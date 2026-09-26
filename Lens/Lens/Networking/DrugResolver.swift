//
//  Bridges the synchronous detection pipeline to the async backend.
//
//  ARSessionManager.resolvePayload is called on the main queue for every frame
//  that reads a barcode or text, and it has to answer immediately. So this
//  answers from cache (or from the local demo catalog on a first sighting) and
//  kicks off the POST /detect that fills the cache for subsequent frames.
//
//  Owned by: AR & detection lane / Networking.
//

import Combine
import Foundation

@MainActor
final class DrugResolver: ObservableObject {
    /// Payload string -> resolved drug, so a bottle held in view resolves once.
    @Published private(set) var resolved: [String: Drug] = [:]
    /// True once any backend call has succeeded, so the UI can say whether
    /// what's on screen came from the backend or from the offline catalog.
    @Published private(set) var isBackendReachable = false

    private var inFlight: Set<String> = []
    private var lastAttempt: [String: Date] = [:]
    private let client: APIClient
    private let retryInterval: TimeInterval = 2

    init() {
        self.client = .shared
    }

    init(client: APIClient) {
        self.client = client
    }

    static func cacheKey(kind: String, value: String) -> String {
        "\(kind):\(value)"
    }

    /// Inverse of `DetectionResult.rawPayload` (`"barcode: …"` / `"text: …"`).
    static func cacheKey(rawPayload: String) -> String? {
        let parts = rawPayload.split(separator: ":", maxSplits: 1)
        guard parts.count == 2 else { return nil }
        let kind = String(parts[0])
        let value = parts[1].trimmingCharacters(in: .whitespaces)
        return cacheKey(kind: kind, value: value)
    }

    /// `kind` is "barcode" or "text", matching POST /detect's two fields.
    func resolve(kind: String, value: String) -> Drug {
        let key = Self.cacheKey(kind: kind, value: value)
        if let drug = resolved[key] {
            return drug
        }
        fetch(kind: kind, value: value, key: key)
        return DemoDrugCatalog.resolve(payload: value).drug
    }

    func cachedDrug(forRawPayload payload: String) -> Drug? {
        guard let key = Self.cacheKey(rawPayload: payload) else { return nil }
        return resolved[key]
    }

    private func fetch(kind: String, value: String, key: String) {
        guard client.baseURL != nil, !inFlight.contains(key) else { return }
        if let last = lastAttempt[key], Date().timeIntervalSince(last) < retryInterval {
            return
        }
        lastAttempt[key] = Date()
        inFlight.insert(key)
        Task { [weak self] in
            guard let self else { return }
            defer { self.inFlight.remove(key) }
            do {
                let drug = try await client.detectDrug(
                    barcode: kind == "barcode" ? value : nil,
                    ocrText: kind == "text" ? value : nil
                )
                self.resolved[key] = drug
                self.isBackendReachable = true
            } catch APIError.notFound {
                // The backend is up but doesn't know this package. Keep the
                // local guess rather than retrying every frame.
                self.resolved[key] = DemoDrugCatalog.resolve(payload: value).drug
                self.isBackendReachable = true
            } catch {
                // Backend down: leave uncached so a later frame retries.
            }
        }
    }
}

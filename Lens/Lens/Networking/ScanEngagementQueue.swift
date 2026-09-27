import Combine
import Foundation

/// Keep the next summary read behind any unfinished engagement write for the
/// same account/drug. Tracking updates must not create parallel writes.
@MainActor
final class ScanEngagementQueue: ObservableObject {
    private struct Key: Hashable {
        let hcpId: String
        let drugId: String
    }
    private var pending: [Key: Task<Int, Error>] = [:]
    /// The bottle currently in view. Cleared when tracking drops, so the next
    /// confirmed sighting logs another touch. Frames inside one sighting do not.
    private var sighting: Key?
    @Published private(set) var isRecording = false

    /// True once per confirmed sighting. Repeat calls while the same bottle
    /// stays in view return false. After `noteTrackingLost()`, the next call
    /// is a new scan.
    func startsNewScan(hcpId: String, drugId: String) -> Bool {
        let key = Key(hcpId: hcpId, drugId: drugId)
        guard sighting != key else { return false }
        sighting = key
        return true
    }

    /// The detected object left the frame (or the session dropped it).
    func noteTrackingLost() {
        sighting = nil
    }

    /// Detection returned while this drug's summary request was still in
    /// flight. Keep that request as the open sighting so it is not logged twice.
    func keepCurrentSighting(hcpId: String, drugId: String) {
        sighting = Key(hcpId: hcpId, drugId: drugId)
    }

    func wait(hcpId: String, drugId: String) async {
        let key = Key(hcpId: hcpId, drugId: drugId)
        _ = try? await pending[key]?.value
    }

    func record(hcpId: String, drugId: String, operation: @escaping () async throws -> Int) async throws -> Int {
        let key = Key(hcpId: hcpId, drugId: drugId)
        if let task = pending[key] { return try await task.value }
        let task = Task { try await operation() }
        pending[key] = task
        isRecording = true
        defer {
            pending[key] = nil
            isRecording = !pending.isEmpty
        }
        return try await task.value
    }
}

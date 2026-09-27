//
//  App-wide observable state.
//
//  Single source of truth for "who is the demo user right now, what
//  drug are they looking at, and how familiar are they with it." Views
//  read/write this instead of passing data through init parameters.
//
//  Owned by: whole team — this is the shared contract between lanes.
//

import Foundation
import Combine

@MainActor
final class AppState: ObservableObject {
    @Published var selectedHCP: HCP? {
        didSet {
            if let selectedHCP {
                defaults.set(selectedHCP.id, forKey: Self.profileCacheKey)
                if let data = try? Self.encoder.encode(selectedHCP) {
                    defaults.set(data, forKey: Self.profileRecordKey)
                }
            } else {
                defaults.removeObject(forKey: Self.profileCacheKey)
                defaults.removeObject(forKey: Self.profileRecordKey)
            }
            if oldValue?.id != selectedHCP?.id {
                currentDrug = nil
                familiarityTier = nil
                selectedPatient = nil
                scanSessionPatient = nil
                openScanTab = false
                reloadHistory()
            }
        }
    }
    @Published var sessionToken: String? {
        didSet {
            if let sessionToken, !sessionToken.isEmpty {
                defaults.set(sessionToken, forKey: Self.sessionCacheKey)
            } else {
                defaults.removeObject(forKey: Self.sessionCacheKey)
            }
        }
    }
    @Published var currentDrug: Drug?
    @Published var selectedPatient: Patient?
    /// Stays set for this camera visit so the HUD can check the chart
    /// after `selectedPatient` is cleared.
    @Published var scanSessionPatient: Patient?
    @Published var openScanTab = false
    @Published var familiarityTier: String?
    @Published private(set) var scanHistory: [ScanLogEntry] = []
    @Published var pendingRecoveryCode: String?

    var isSignedIn: Bool {
        selectedHCP != nil && !(sessionToken ?? "").isEmpty
    }

    static let profileCacheKey = "lens.selectedHCPID"
    static let profileRecordKey = "lens.selectedHCPRecord"
    static let sessionCacheKey = "lens.sessionToken"
    static let historyCacheKey = "lens.scanHistory"

    private let defaults: UserDefaults
    private let now: () -> Date

    init(defaults: UserDefaults = .standard, now: @escaping () -> Date = Date.init) {
        self.defaults = defaults
        self.now = now
        let token = defaults.string(forKey: Self.sessionCacheKey)
        if let data = defaults.data(forKey: Self.profileRecordKey),
           let stored = try? Self.decoder.decode(HCP.self, from: data) {
            selectedHCP = stored
        } else {
            selectedHCP = nil
        }
        if selectedHCP == nil {
            defaults.removeObject(forKey: Self.profileCacheKey)
            defaults.removeObject(forKey: Self.profileRecordKey)
        }
        sessionToken = token
        reloadHistory()
    }

    func applySession(profile: HCP, token: String, recoveryCode: String?, openScan: Bool = true) {
        pendingRecoveryCode = recoveryCode
        sessionToken = token
        selectedHCP = profile
        if openScan {
            openScanTab = true
        }
    }

    func logOut() {
        sessionToken = nil
        pendingRecoveryCode = nil
        selectedHCP = nil
        currentDrug = nil
        familiarityTier = nil
        endScanSession()
    }

    func useForScan(_ patient: Patient) {
        selectedPatient = patient
        scanSessionPatient = patient
        openScanTab = true
    }

    func finishScanSelection() {
        selectedPatient = nil
    }

    func endScanSession() {
        selectedPatient = nil
        scanSessionPatient = nil
        openScanTab = false
    }

    func recordChat(question: String, answer: String) {
        recordChat(question: question, answer: answer, drug: currentDrug, hcpId: selectedHCP?.id)
    }

    /// Use the question's original context, including a genuinely drug-free
    /// question, rather than whatever the camera sees when its answer arrives.
    func recordChat(question: String, answer: String, drug: Drug?, hcpId: String?) {
        let question = question.trimmingCharacters(in: .whitespacesAndNewlines)
        let answer = answer.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !question.isEmpty, !answer.isEmpty, let hcpId,
              selectedHCP?.id == hcpId else { return }

        let turn = ChatTurn(askedAt: now(), question: question, answer: answer)
        var entries = entries(for: hcpId)

        if let last = entries.indices.last, entries[last].drugId == drug?.id {
            entries[last].chats.append(turn)
        } else {
            entries.append(
                ScanLogEntry(
                    hcpId: hcpId,
                    drugId: drug?.id,
                    drugName: drug?.name ?? "Voice chat",
                    scannedAt: turn.askedAt,
                    chats: [turn]
                )
            )
        }

        save(entries, for: hcpId)
    }

    /// Pulls this HCP's chat history from MongoDB (the source of truth) and
    /// overwrites the local cache. Called from `HistoryView`'s pull-to-refresh.
    func syncHistory() async {
        guard let hcpId = selectedHCP?.id else { return }
        guard let conversations = try? await APIClient.shared.getChats(hcpId: hcpId) else { return }

        let entries = conversations.map { conversation -> ScanLogEntry in
            var turns: [ChatTurn] = []
            var index = 0
            while index + 1 < conversation.messages.count {
                let userMessage = conversation.messages[index]
                let assistantMessage = conversation.messages[index + 1]
                let askedAt = ServerDate.parse(userMessage.askedAt)
                    ?? ServerDate.parse(conversation.askedAt)
                    ?? now()
                turns.append(ChatTurn(askedAt: askedAt, question: userMessage.text, answer: assistantMessage.text))
                index += 2
            }
            return ScanLogEntry(
                id: UUID(uuidString: conversation.conversationId) ?? UUID(),
                hcpId: hcpId,
                drugId: conversation.drugId,
                drugName: conversation.drugName,
                scannedAt: ServerDate.parse(conversation.askedAt) ?? now(),
                chats: turns
            )
        }

        save(entries, for: hcpId)
    }

    private func reloadHistory() {
        guard let hcpId = selectedHCP?.id else {
            scanHistory = []
            return
        }
        scanHistory = entries(for: hcpId)
    }

    private func entries(for hcpId: String) -> [ScanLogEntry] {
        (loadAll()[hcpId] ?? []).filter { !$0.chats.isEmpty }
    }

    private func save(_ entries: [ScanLogEntry], for hcpId: String) {
        var all = loadAll()
        all[hcpId] = entries
        if let data = try? Self.encoder.encode(all) {
            defaults.set(data, forKey: Self.historyCacheKey)
        }
        if selectedHCP?.id == hcpId {
            scanHistory = entries
        }
    }

    private func loadAll() -> [String: [ScanLogEntry]] {
        guard let data = defaults.data(forKey: Self.historyCacheKey) else { return [:] }
        return (try? Self.decoder.decode([String: [ScanLogEntry]].self, from: data)) ?? [:]
    }

    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .secondsSince1970
        return encoder
    }()

    private static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .secondsSince1970
        return decoder
    }()
}

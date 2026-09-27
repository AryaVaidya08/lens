// Compile with production VoiceAssistantSession.swift and Models/Drug.swift.
// These doubles isolate question context and cancellation from Apple audio APIs.
import Combine
import Foundation

@MainActor
final class SpeechRecognizer: ObservableObject {
    enum State { case idle, requestingPermission, listening, finishing }
    @Published var state: State = .idle
    var transcript = ""
    var errorMessage: String?
    var completion: ((String) -> Void)?
    func startListening(_ completion: @escaping (String) -> Void) {
        self.completion = completion
        state = .listening
    }
    func stopListening() {
        state = .idle
        completion?("What does the reference say?")
    }
    func cancel() { state = .idle; completion = nil }
}

@MainActor
final class SpeechSynthesizer: ObservableObject {
    @Published var isSpeaking = false
    var errorMessage: String?
    var spoken: [String] = []
    func stop() { isSpeaking = false }
    func speak(_ text: String) { spoken.append(text); isSpeaking = true }
}

enum PlaceholderAssistant {
    static func reply(to question: String, drug: Drug?) -> String { "Demo" }
}

@MainActor
final class APIClient {
    static let shared = APIClient()
    func askQuestion(drugId: String, hcpId: String, query: String, patientId: String?) async throws -> String {
        fatalError("Tests must inject an answer provider; network calls are forbidden")
    }
}

@main
struct VoiceSessionChecks {
    @MainActor static func main() async {
        let session = VoiceAssistantSession()
        var drug: Drug? = Drug(id: "first", name: "First bottle")
        var patient: String? = "first-patient"
        var hcp: String? = "first-hcp"
        var records = 0
        var recordedDrug: Drug?
        var recordedHCP: String?
        var received: (String?, String?, String?)?
        session.answerProvider = { _, drug, hcp, patient in
            received = (drug?.id, hcp, patient)
            return "Reference answer"
        }
        func tap() {
            session.microphoneTapped(currentDrug: { drug }, hcpId: { hcp }, patientId: { patient }) { _, _, contextDrug, contextHCP in
                records += 1
                recordedDrug = contextDrug
                recordedHCP = contextHCP
            }
        }
        tap()
        drug = Drug(id: "second", name: "Second bottle")
        patient = "second-patient"
        tap()
        for _ in 0..<100 where records == 0 { await Task.yield() }
        precondition(received?.0 == "first", "Detection changes must not retarget a recorded question")
        precondition(received?.1 == "first-hcp" && received?.2 == "first-patient", "Question must retain its original chart context")
        precondition(records == 1 && session.speaker.spoken == ["Reference answer"])
        precondition(recordedDrug?.id == "first" && recordedHCP == "first-hcp", "History must use the same snapshot as the answer request")

        session.stopAudio()
        var pending: CheckedContinuation<String, Never>?
        session.answerProvider = { _, _, _, _ in
            await withCheckedContinuation { pending = $0 }
        }
        tap()
        tap()
        for _ in 0..<100 where pending == nil { await Task.yield() }
        precondition(pending != nil, "Request should reach the injected provider")
        session.leaveScanTab()
        pending?.resume(returning: "Late answer")
        for _ in 0..<100 { await Task.yield() }
        precondition(records == 1 && session.speaker.spoken == ["Reference answer"], "Leaving Scan must suppress late history writes and speech")

        pending = nil
        tap()
        tap()
        for _ in 0..<100 where pending == nil { await Task.yield() }
        precondition(pending != nil)
        hcp = "second-hcp"
        pending?.resume(returning: "Previous account's answer")
        for _ in 0..<100 { await Task.yield() }
        precondition(records == 1 && session.speaker.spoken == ["Reference answer"], "Account changes must not leak old replies into another history")

        session.stopAudio()
        session.answerProvider = { _, _, _, _ in "General answer" }
        drug = nil
        tap()
        drug = Drug(id: "later", name: "Later bottle")
        tap()
        for _ in 0..<100 where records == 1 { await Task.yield() }
        precondition(records == 2 && recordedDrug == nil, "A drug-free question must remain drug-free in history")
        print("PASS: voice question context, exactly-once completion, and cancellation")
    }
}

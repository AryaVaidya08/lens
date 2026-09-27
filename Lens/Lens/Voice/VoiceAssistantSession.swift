import Combine
import Foundation

@MainActor
final class VoiceAssistantSession: ObservableObject {
    let recognizer: SpeechRecognizer
    let speaker: SpeechSynthesizer
    @Published var reply = ""
    @Published var isExpanded = false

    /// Question + current drug + HCP + selected patient -> spoken answer.
    /// Defaults to POST /drug/{id}/ask, falling back to the local demo reply
    /// when the backend isn't reachable. Injectable so tests don't need a
    /// network.
    var answerProvider: (String, Drug?, String?, String?) async -> String = backendAnswer

    private var answerGeneration = 0
    private var cancellables = Set<AnyCancellable>()

    init(recognizer: SpeechRecognizer? = nil, speaker: SpeechSynthesizer? = nil) {
        let recognizer = recognizer ?? SpeechRecognizer()
        let speaker = speaker ?? SpeechSynthesizer()
        self.recognizer = recognizer
        self.speaker = speaker
        recognizer.objectWillChange
            .sink { [weak self] _ in self?.objectWillChange.send() }
            .store(in: &cancellables)
        speaker.objectWillChange
            .sink { [weak self] _ in self?.objectWillChange.send() }
            .store(in: &cancellables)
    }

    var isActive: Bool { recognizer.state != .idle || speaker.isSpeaking }

    var microphoneSymbol: String {
        if speaker.isSpeaking || recognizer.state == .listening { return "stop.fill" }
        if recognizer.state == .requestingPermission { return "xmark" }
        if recognizer.state == .finishing { return "ellipsis" }
        return "mic.fill"
    }

    var buttonTitle: String {
        switch recognizer.state {
        case .idle: "Tap to speak"
        case .requestingPermission: "Requesting access…"
        case .listening: "Finish"
        case .finishing: "Finishing…"
        }
    }

    var microphoneAccessibilityLabel: String {
        if recognizer.state == .requestingPermission { return "Cancel microphone request" }
        if speaker.isSpeaking { return "Stop speaking" }
        return buttonTitle
    }

    var hasContent: Bool {
        !recognizer.transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
        !reply.isEmpty || recognizer.errorMessage != nil || speaker.errorMessage != nil
    }

    /// The answer half of the loop. `hcpId` is whichever persona is selected —
    /// the backend trusts it (see CLAUDE.md: no real auth for the demo).
    /// `patientId` is whichever patient is currently selected for this scan,
    /// if any — passed through so the answer can be grounded in that
    /// patient's chart alongside the drug dossier.
    static func backendAnswer(question: String, drug: Drug?, hcpId: String?, patientId: String?) async -> String {
        guard let drug, let hcpId else {
            return PlaceholderAssistant.reply(to: question, drug: drug)
        }
        do {
            return try await APIClient.shared.askQuestion(
                drugId: drug.id, hcpId: hcpId, query: question, patientId: patientId
            )
        } catch {
            return PlaceholderAssistant.reply(to: question, drug: drug)
        }
    }

    func microphoneTapped(
        currentDrug: @escaping () -> Drug?,
        hcpId: @escaping () -> String?,
        patientId: @escaping () -> String? = { nil },
        recordChat: @escaping (String, String) -> Void
    ) {
        isExpanded = true
        if recognizer.state == .requestingPermission {
            stopAudio()
            isExpanded = false
            return
        }
        if speaker.isSpeaking {
            speaker.stop()
            return
        }
        if recognizer.state == .listening {
            recognizer.stopListening()
        } else if recognizer.state == .idle {
            speaker.stop()
            reply = ""
            answerGeneration += 1
            let generation = answerGeneration
            recognizer.startListening { [weak self] text in
                guard let self else { return }
                let drug = currentDrug()
                let hcpId = hcpId()
                let patientId = patientId()
                self.reply = "Thinking…"
                Task { [weak self] in
                    guard let self else { return }
                    let answer = await self.answerProvider(text, drug, hcpId, patientId)
                    guard self.answerGeneration == generation else { return }
                    self.reply = answer
                    recordChat(text, answer)
                    self.speaker.speak(answer)
                }
            }
        }
    }

    func leaveScanTab() {
        stopAudio()
        isExpanded = false
    }

    func stopAudio() {
        answerGeneration += 1
        recognizer.cancel()
        speaker.stop()
    }
}

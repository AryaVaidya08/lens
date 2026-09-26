import Combine
import Foundation

@MainActor
final class VoiceAssistantSession: ObservableObject {
    let recognizer: SpeechRecognizer
    let speaker: SpeechSynthesizer
    @Published var reply = ""
    @Published var isExpanded = false

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

    func microphoneTapped(
        currentDrug: @escaping () -> Drug?,
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
            recognizer.startListening { [weak self] text in
                guard let self else { return }
                self.reply = PlaceholderAssistant.reply(to: text, drug: currentDrug())
                recordChat(text, self.reply)
                self.speaker.speak(self.reply)
            }
        }
    }

    func leaveScanTab() {
        stopAudio()
        isExpanded = false
    }

    func stopAudio() {
        recognizer.cancel()
        speaker.stop()
    }
}

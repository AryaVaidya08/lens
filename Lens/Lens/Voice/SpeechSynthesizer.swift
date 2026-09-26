import AVFoundation
import Combine

@MainActor
final class SpeechSynthesizer: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {
    @Published private(set) var isSpeaking = false
    @Published private(set) var errorMessage: String?

    private let synthesizer = AVSpeechSynthesizer()
    private var currentUtterance: AVSpeechUtterance?
    private var ownsAudioSession = false

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    func speak(_ text: String) {
        stop()
        errorMessage = nil
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .spokenAudio, options: .duckOthers)
            try session.setActive(true)
            ownsAudioSession = true
            let utterance = AVSpeechUtterance(string: text)
            utterance.voice = InstalledSpeechVoices.selectedVoice()
            utterance.rate = AVSpeechUtteranceDefaultSpeechRate
            currentUtterance = utterance
            isSpeaking = true
            synthesizer.speak(utterance)
        } catch {
            errorMessage = "Couldn't play the reply. You can still read it below."
            releaseAudioSession()
        }
    }

    func stop() {
        currentUtterance = nil
        synthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
        releaseAudioSession()
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                                      didFinish utterance: AVSpeechUtterance) {
        let utteranceID = ObjectIdentifier(utterance)
        Task { @MainActor [weak self] in self?.finished(utteranceID) }
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                                      didCancel utterance: AVSpeechUtterance) {
        let utteranceID = ObjectIdentifier(utterance)
        Task { @MainActor [weak self] in self?.finished(utteranceID) }
    }

    private func finished(_ utteranceID: ObjectIdentifier) {
        guard let currentUtterance, ObjectIdentifier(currentUtterance) == utteranceID else { return }
        self.currentUtterance = nil
        isSpeaking = false
        releaseAudioSession()
    }

    private func releaseAudioSession() {
        guard ownsAudioSession else { return }
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        ownsAudioSession = false
    }
}

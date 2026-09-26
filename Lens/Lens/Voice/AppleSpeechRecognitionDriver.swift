import AVFoundation
import Speech

@MainActor
final class AppleSpeechRecognitionDriver: SpeechRecognitionDriving {
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var hasInputTap = false
    private var ownsAudioSession = false

    enum RecordingError: LocalizedError {
        case unavailable, noInput

        var errorDescription: String? {
            switch self {
            case .unavailable: "Speech recognition is unavailable. Check your connection and try again."
            case .noInput: "No microphone input is available. Check your audio device and try again."
            }
        }
    }

    func requestSpeechPermission() async -> SpeechPermission {
        let status = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { @Sendable status in
                continuation.resume(returning: status)
            }
        }
        switch status {
        case .authorized: return .authorized
        case .restricted: return .restricted
        default: return .denied
        }
    }

    func requestMicrophonePermission() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioApplication.requestRecordPermission { @Sendable granted in
                continuation.resume(returning: granted)
            }
        }
    }

    func start(onUpdate: @escaping @MainActor (SpeechUpdate) -> Void) throws {
        guard let recognizer, recognizer.isAvailable else { throw RecordingError.unavailable }
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
        try audioSession.setActive(true)
        ownsAudioSession = true

        let request = SFSpeechAudioBufferRecognitionRequest()
        request.shouldReportPartialResults = true
        if recognizer.supportsOnDeviceRecognition { request.requiresOnDeviceRecognition = true }
        self.request = request
        let input = audioEngine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0, format.channelCount > 0 else { throw RecordingError.noInput }
        input.installTap(onBus: 0, bufferSize: 1024, format: format,
                         block: Self.audioTap(for: request))
        hasInputTap = true
        recognitionTask = recognizer.recognitionTask(with: request) { @Sendable result, error in
            let update = SpeechUpdate(text: result?.bestTranscription.formattedString,
                                      isFinal: result?.isFinal ?? false, failed: error != nil)
            Task { @MainActor in onUpdate(update) }
        }
        audioEngine.prepare()
        try audioEngine.start()
    }

    func finishAudio() {
        stopAudioInput()
        request?.endAudio()
    }

    func cancel() {
        finishAudio()
        recognitionTask?.cancel()
        recognitionTask = nil
        request = nil
        if ownsAudioSession {
            try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
            ownsAudioSession = false
        }
    }

    nonisolated private static func audioTap(
        for request: SFSpeechAudioBufferRecognitionRequest
    ) -> AVAudioNodeTapBlock {
        { buffer, _ in request.append(buffer) }
    }

    private func stopAudioInput() {
        audioEngine.stop()
        if hasInputTap {
            audioEngine.inputNode.removeTap(onBus: 0)
            hasInputTap = false
        }
    }
}

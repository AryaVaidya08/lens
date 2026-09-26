import Combine
import Foundation

/// Microphone → live transcript → one completed question. No backend calls.
@MainActor
final class SpeechRecognizer: ObservableObject {
    enum State {
        case idle, requestingPermission, listening, finishing
    }

    @Published private(set) var state: State = .idle
    @Published private(set) var transcript = ""
    @Published private(set) var errorMessage: String?
    @Published private(set) var needsSettings = false

    private let driver: any SpeechRecognitionDriving
    private let sleep: @MainActor (Duration) async throws -> Void
    private var timeoutTask: Task<Void, Never>?
    private var sessionID: UUID?
    private var completion: ((String) -> Void)?

    init(driver: any SpeechRecognitionDriving,
         sleep: @escaping @MainActor (Duration) async throws -> Void = { try await Task.sleep(for: $0) }) {
        self.driver = driver
        self.sleep = sleep
    }

    #if os(iOS)
    convenience init() {
        self.init(driver: AppleSpeechRecognitionDriver())
    }
    #endif

    func startListening(completion: @escaping (String) -> Void) {
        cancel()
        transcript = ""
        errorMessage = nil
        needsSettings = false
        state = .requestingPermission
        let id = UUID()
        sessionID = id
        self.completion = completion

        Task { [weak self] in
            guard let self, self.sessionID == id else { return }
            let authorization = await self.driver.requestSpeechPermission()
            guard self.sessionID == id else { return }
            guard authorization == .authorized else {
                self.needsSettings = authorization == .denied
                self.fail(authorization == .restricted
                    ? "Speech recognition is restricted on this device."
                    : "Allow speech recognition in Settings to use the assistant.")
                return
            }
            let allowed = await self.driver.requestMicrophonePermission()
            guard self.sessionID == id else { return }
            guard allowed else {
                self.needsSettings = true
                self.fail("Allow microphone access in Settings to use the assistant.")
                return
            }
            self.beginRecording(id: id)
        }
    }

    /// End input and allow the recognizer to finalize the last words.
    func stopListening() {
        guard state == .listening, let id = sessionID else { return }
        state = .finishing
        driver.finishAudio()
        // A driver can deliver a final result synchronously while ending audio.
        guard sessionID == id else { return }
        scheduleTimeout(after: .seconds(3), id: id) { $0.finish() }
    }

    /// Invalidate callbacks before cancelling; late results must not speak.
    func cancel() {
        sessionID = nil
        completion = nil
        timeoutTask?.cancel()
        timeoutTask = nil
        driver.cancel()
        state = .idle
    }

    private func beginRecording(id: UUID) {
        do {
            state = .listening
            try driver.start { [weak self] update in
                guard let self, self.sessionID == id else { return }
                // Empty end-of-audio updates must not erase captured words.
                if let text = update.text,
                   !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    self.transcript = text
                }
                if update.isFinal {
                    self.finish()
                } else if update.failed {
                    if self.state == .finishing {
                        // Match the timeout path after Finish: submit captured
                        // words once, or report silence if there weren't any.
                        self.finish()
                    } else {
                        self.fail("Couldn't finish recognizing your speech. Please try again.")
                    }
                }
            }
            guard sessionID == id else { return }
            scheduleTimeout(after: .seconds(45), id: id) { $0.stopListening() }
        } catch {
            let message = (error as? LocalizedError)?.errorDescription
            fail(message ?? "Couldn't start the microphone. Check your audio device and try again.")
        }
    }

    private func scheduleTimeout(after duration: Duration, id: UUID,
                                 action: @escaping @MainActor (SpeechRecognizer) -> Void) {
        timeoutTask?.cancel()
        let sleep = self.sleep
        timeoutTask = Task { [weak self] in
            do { try await sleep(duration) } catch { return }
            guard !Task.isCancelled, let self, self.sessionID == id else { return }
            action(self)
        }
    }

    private func finish() {
        let text = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        let callback = completion
        cancel()
        guard !text.isEmpty else {
            errorMessage = "I didn't hear anything. Tap the microphone and try again."
            return
        }
        callback?(text)
    }

    private func fail(_ message: String) {
        cancel()
        errorMessage = message
    }
}

import Foundation

/// Boundary between the voice conversation and Apple's permission/audio APIs.
/// Tests supply a fake driver; the app uses AppleSpeechRecognitionDriver.
enum SpeechPermission {
    case authorized, denied, restricted
}

struct SpeechUpdate: Sendable {
    let text: String?
    let isFinal: Bool
    let failed: Bool
}

@MainActor
protocol SpeechRecognitionDriving: AnyObject {
    func requestSpeechPermission() async -> SpeechPermission
    func requestMicrophonePermission() async -> Bool
    func start(onUpdate: @escaping @MainActor (SpeechUpdate) -> Void) throws
    func finishAudio()
    func cancel()
}

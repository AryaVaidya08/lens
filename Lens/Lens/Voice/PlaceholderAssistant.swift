import Foundation

/// Replace this reply with APIClient.askQuestion once backend integration is ready.
/// The demo deliberately echoes the recognized question without clinical advice.
enum PlaceholderAssistant {
    static func reply(to question: String) -> String {
        "I heard you say: \(question). I'm using a demo reply for now. Drug answers will be available when the assistant is connected."
    }
}

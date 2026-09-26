import Foundation

struct SpeechVoiceOption: Equatable {
    enum Quality: Int {
        case standard, enhanced, premium
    }

    let id: String
    let name: String
    let language: String
    let quality: Quality
}

enum SpeechVoiceSelection {
    /// One assistant persona: Ava, US English. Quality variants keep the same voice.
    /// Voice names may include a quality suffix such as "Ava (Premium)".
    static func selected(from voices: [SpeechVoiceOption]) -> SpeechVoiceOption? {
        voices.filter {
            $0.language == "en-US" && ($0.name == "Ava" || $0.name.hasPrefix("Ava ("))
        }.sorted {
            if $0.quality != $1.quality { return $0.quality.rawValue > $1.quality.rawValue }
            return $0.id < $1.id
        }.first
    }
}

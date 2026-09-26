import AVFoundation

@MainActor
enum InstalledSpeechVoices {
    static func selectedVoice() -> AVSpeechSynthesisVoice? {
        let voices = AVSpeechSynthesisVoice.speechVoices().filter {
            !$0.voiceTraits.contains(.isNoveltyVoice) && !$0.voiceTraits.contains(.isPersonalVoice)
        }
        let options = voices.map { voice in
            let quality: SpeechVoiceOption.Quality
            switch voice.quality {
            case .premium: quality = .premium
            case .enhanced: quality = .enhanced
            default: quality = .standard
            }
            return SpeechVoiceOption(id: voice.identifier, name: voice.name,
                                     language: voice.language, quality: quality)
        }
        if let selected = SpeechVoiceSelection.selected(from: options),
           let voice = AVSpeechSynthesisVoice(identifier: selected.id) {
            return voice
        }
        // Keep speech usable if Ava has not been downloaded on this device yet.
        return AVSpeechSynthesisVoice(language: "en-US")
    }
}

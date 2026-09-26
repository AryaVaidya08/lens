import Foundation

@main
struct VoiceSelectionChecks {
    static func main() {
        let basic = SpeechVoiceOption(id: "ava-basic", name: "Ava", language: "en-US", quality: .standard)
        let enhanced = SpeechVoiceOption(id: "ava-enhanced", name: "Ava (Enhanced)", language: "en-US", quality: .enhanced)
        let premium = SpeechVoiceOption(id: "ava-premium", name: "Ava (Premium)", language: "en-US", quality: .premium)
        let other = SpeechVoiceOption(id: "other", name: "Other", language: "en-US", quality: .premium)
        let french = SpeechVoiceOption(id: "french", name: "Ava", language: "fr-FR", quality: .premium)
        let similarName = SpeechVoiceOption(id: "similar", name: "Avalon", language: "en-US", quality: .premium)
        let all = [french, basic, other, enhanced, premium, similarName]
        precondition(SpeechVoiceSelection.selected(from: all) == premium)
        precondition(SpeechVoiceSelection.selected(from: [basic, enhanced, other]) == enhanced)
        precondition(SpeechVoiceSelection.selected(from: [basic, other]) == basic)
        precondition(SpeechVoiceSelection.selected(from: []) == nil)
        precondition(SpeechVoiceSelection.selected(from: [french, other, similarName]) == nil)
        precondition(SpeechVoiceSelection.selected(from: all) == SpeechVoiceSelection.selected(from: all.reversed()))
        let unsuffixedPremium = SpeechVoiceOption(id: "premium", name: "Ava", language: "en-US", quality: .premium)
        precondition(SpeechVoiceSelection.selected(from: [basic, unsuffixedPremium]) == unsuffixedPremium)
        print("PASS: 7 fixed voice checks (Ava quality variants, locale, missing voice, stable selection)")
    }
}

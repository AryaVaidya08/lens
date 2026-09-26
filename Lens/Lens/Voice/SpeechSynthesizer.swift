//
//  Text-to-speech for spoken answers.
//
//  Wraps AVSpeechSynthesizer. Takes the `answer_text` returned by
//  APIClient.askQuestion and speaks it aloud.
//
//  Owned by: Voice & LLM lane.
//

import AVFoundation

final class SpeechSynthesizer {
    /// Speaks `text` aloud.
    ///
    /// TODO: implement — wrap an AVSpeechSynthesizer + AVSpeechUtterance,
    /// picking a voice/rate that stays intelligible for spoken medical
    /// terminology.
    func speak(_ text: String) {
        // TODO: implement
    }
}

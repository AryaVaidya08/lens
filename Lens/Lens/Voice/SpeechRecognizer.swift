//
//  Speech-to-text for follow-up questions.
//
//  Wraps SFSpeechRecognizer. The physician taps to ask, speaks, and
//  this hands the transcribed text to APIClient.askQuestion.
//
//  Owned by: Voice & LLM lane.
//

import Speech

final class SpeechRecognizer {
    /// Starts listening on the mic and calls `completion` with the
    /// transcribed text once recognition finishes.
    ///
    /// TODO: implement — request SFSpeechRecognizer + microphone
    /// authorization, run an SFSpeechAudioBufferRecognitionRequest over
    /// an AVAudioEngine tap, and call `completion` with the final
    /// transcription.
    func startListening(completion: @escaping (String) -> Void) {
        // TODO: implement
    }
}

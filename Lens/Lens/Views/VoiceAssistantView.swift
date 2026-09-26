import AVFoundation
import Combine
import SwiftUI
import UIKit

struct VoiceAssistantView: View {
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.openURL) private var openURL
    @StateObject private var recognizer = SpeechRecognizer()
    @StateObject private var speaker = SpeechSynthesizer()
    @State private var reply = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    VStack(alignment: .leading, spacing: 8) {
                        Label("Voice assistant", systemImage: "waveform.circle.fill")
                            .font(.title2.bold())
                        Text("Try saying something, then tap Finish. I'll repeat what I heard. Drug answers aren't connected yet.")
                            .foregroundStyle(.secondary)
                    }

                    VStack(spacing: 12) {
                        Button(action: microphoneTapped) {
                            Label(buttonTitle, systemImage: recognizer.state == .listening ? "stop.fill" : "mic.fill")
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(recognizer.state == .requestingPermission || recognizer.state == .finishing)
                        .accessibilityIdentifier("assistant.microphone")

                        if recognizer.state != .idle {
                            Button("Cancel", role: .cancel) { recognizer.cancel() }
                        }
                        if speaker.isSpeaking {
                            Button("Stop speaking") { speaker.stop() }
                        }
                        Text(statusText)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }

                    if !recognizer.transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        transcriptCard(title: "You said", text: recognizer.transcript)
                    }

                    if !reply.isEmpty {
                        transcriptCard(title: "Assistant · Demo reply", text: reply)
                        Button {
                            speaker.speak(reply)
                        } label: {
                            Label("Replay reply", systemImage: "speaker.wave.2.fill")
                        }
                        .disabled(recognizer.state != .idle || speaker.isSpeaking)
                    }

                    if let error = recognizer.errorMessage ?? speaker.errorMessage {
                        Label(error, systemImage: "exclamationmark.circle")
                            .foregroundStyle(.red)
                            .accessibilityIdentifier("assistant.error")
                    }
                    if recognizer.needsSettings {
                        Button("Open app settings") {
                            if let url = URL(string: UIApplication.openSettingsURLString) {
                                openURL(url)
                            }
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Assistant")
        }
        .onDisappear(perform: stopAudio)
        .onChange(of: scenePhase) { _, phase in
            if phase == .background { stopAudio() }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)
            .receive(on: RunLoop.main)) { notification in
            guard let type = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                  type == AVAudioSession.InterruptionType.began.rawValue else { return }
            stopAudio()
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)
            .receive(on: RunLoop.main)) { notification in
            guard let reason = notification.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
                  reason == AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue else { return }
            stopAudio()
        }
    }

    private var buttonTitle: String {
        switch recognizer.state {
        case .idle: "Tap to speak"
        case .requestingPermission: "Requesting access…"
        case .listening: "Finish"
        case .finishing: "Finishing…"
        }
    }

    private var statusText: String {
        if speaker.isSpeaking { return "Speaking reply…" }
        switch recognizer.state {
        case .idle: return "Ready when you are."
        case .requestingPermission: return "Microphone and speech recognition access are needed."
        case .listening: return "Listening… Recording ends after 45 seconds."
        case .finishing: return "Finishing your transcript…"
        }
    }

    private func transcriptCard(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.headline)
            Text(text).textSelection(.enabled)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.quaternary, in: RoundedRectangle(cornerRadius: 16))
    }

    private func microphoneTapped() {
        if recognizer.state == .listening {
            recognizer.stopListening()
        } else if recognizer.state == .idle {
            speaker.stop()
            reply = ""
            recognizer.startListening { text in
                // Future integration: APIClient.shared.askQuestion(drugId:hcpId:query:).
                // Keep the local demo functional until that endpoint is ready.
                reply = PlaceholderAssistant.reply(to: text)
                speaker.speak(reply)
            }
        }
    }

    private func stopAudio() {
        recognizer.cancel()
        speaker.stop()
    }
}

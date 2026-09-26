import AVFoundation
import Combine
import SwiftUI
import UIKit

struct VoiceAssistantView: View {
    @ObservedObject var assistant: VoiceAssistantSession
    @Binding var selectedTab: MainTab
    var isLandscape = false
    var availableHeight: CGFloat = 800
    @State private var contentHeight: CGFloat = 0
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.openURL) private var openURL

    var body: some View {
        VStack(alignment: .center, spacing: 12) {
            if assistant.isExpanded && selectedTab == .scan && assistant.hasContent {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Assistant").font(.headline)
                        Spacer()
                        Button {
                            assistant.stopAudio()
                            assistant.isExpanded = false
                        } label: {
                            Image(systemName: "xmark")
                                .frame(width: 44, height: 44)
                        }
                        .accessibilityLabel("Close assistant")
                    }

                    ScrollView {
                        VStack(alignment: .leading, spacing: 12) {
                            Text(statusText)
                                .font(.footnote)
                                .foregroundStyle(.secondary)

                            if assistant.recognizer.state != .idle {
                                Button("Cancel", role: .cancel) { assistant.recognizer.cancel() }
                            }
                            if assistant.speaker.isSpeaking {
                                Button("Stop speaking") { assistant.speaker.stop() }
                            }
                            if !assistant.recognizer.transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                                transcriptCard(title: "You said", text: assistant.recognizer.transcript)
                            }
                            if !assistant.reply.isEmpty {
                                transcriptCard(title: "Assistant · Demo reply", text: assistant.reply)
                                Button {
                                    assistant.speaker.speak(assistant.reply)
                                } label: {
                                    Label("Replay reply", systemImage: "speaker.wave.2.fill")
                                }
                                .disabled(assistant.recognizer.state != .idle || assistant.speaker.isSpeaking)
                            }
                            if let error = assistant.recognizer.errorMessage ?? assistant.speaker.errorMessage {
                                Label(error, systemImage: "exclamationmark.circle")
                                    .foregroundStyle(.red)
                                    .accessibilityIdentifier("assistant.error")
                            }
                            if assistant.recognizer.needsSettings {
                                Button("Open app settings") {
                                    if let url = URL(string: UIApplication.openSettingsURLString) {
                                        openURL(url)
                                    }
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .onGeometryChange(for: CGFloat.self) { $0.size.height } action: { contentHeight = $0 }
                    }
                    .frame(height: min(max(contentHeight, 44), panelHeightLimit))
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 16)
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
                .frame(maxWidth: 360)
                .padding(.horizontal, 8)
            }

            if assistant.isExpanded && selectedTab == .scan && !assistant.hasContent && assistant.recognizer.state != .idle {
                HStack {
                    Text(assistant.buttonTitle == "Finish" ? "Listening…" : assistant.buttonTitle)
                        .font(.footnote)
                    Button("Cancel") {
                        assistant.stopAudio()
                        assistant.isExpanded = false
                    }
                }
                .padding(10)
                .background(.regularMaterial, in: Capsule())
            }
        }
        .frame(maxWidth: .infinity)
        .onChange(of: scenePhase) { _, phase in
            if phase == .background { assistant.stopAudio() }
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)
            .receive(on: RunLoop.main)) { notification in
            guard let type = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                  type == AVAudioSession.InterruptionType.began.rawValue else { return }
            assistant.stopAudio()
        }
        .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)
            .receive(on: RunLoop.main)) { notification in
            guard let reason = notification.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
                  reason == AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue else { return }
            assistant.stopAudio()
        }
    }

    private var microphoneScale: CGFloat { isLandscape ? 0.8 : 1 }

    private var panelHeightLimit: CGFloat {
        min(180, max(44, availableHeight - 64 * microphoneScale - 100))
    }

    private var statusText: String {
        if assistant.speaker.isSpeaking { return "Speaking reply…" }
        switch assistant.recognizer.state {
        case .idle: return "Ready when you are."
        case .requestingPermission: return "Microphone and speech recognition access are needed."
        case .listening: return "Listening… Tap the stop button to finish. Recording ends after 45 seconds."
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
}

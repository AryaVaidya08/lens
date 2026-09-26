import AVFoundation
import Combine
import SwiftUI
import UIKit

struct VoiceAssistantView: View {
    @Binding var selectedTab: MainTab
    var isLandscape = false
    var availableHeight: CGFloat = 800
    @ScaledMetric(relativeTo: .title3) private var microphoneIconSize = 20
    @State private var contentHeight: CGFloat = 0
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.openURL) private var openURL
    @StateObject private var recognizer = SpeechRecognizer()
    @StateObject private var speaker = SpeechSynthesizer()
    @State private var reply = ""
    @State private var isExpanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if isExpanded && selectedTab == .scan && hasContent {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Assistant").font(.headline)
                        Spacer()
                        Button {
                            stopAudio()
                            isExpanded = false
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

                            if recognizer.state != .idle {
                                Button("Cancel", role: .cancel) { recognizer.cancel() }
                            }
                            if speaker.isSpeaking {
                                Button("Stop speaking") { speaker.stop() }
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

            if isExpanded && selectedTab == .scan && !hasContent && recognizer.state != .idle {
                HStack {
                    Text(buttonTitle == "Finish" ? "Listening…" : buttonTitle)
                        .font(.footnote)
                    Button("Cancel") { stopAudio(); isExpanded = false }
                }
                .padding(10)
                .background(.regularMaterial, in: Capsule())
                .padding(.leading, 8)
            }

            HStack(spacing: 0) {
                Button(action: microphoneTapped) {
                    Image(systemName: microphoneSymbol)
                        .font(.system(size: microphoneIconSize * microphoneScale, weight: .bold))
                        .foregroundStyle(isActive ? Color.white : Color.primary)
                        .frame(width: 55 * microphoneScale, height: 55 * microphoneScale)
                        .background {
                            if isActive {
                                Circle().fill(.black)
                            } else {
                                Circle()
                                    .fill(.clear)
                                    .glassEffect(.regular, in: .circle)
                            }
                        }
                        .overlay {
                            if isActive {
                                Circle().strokeBorder(Color.blue, lineWidth: 3 * microphoneScale)
                            }
                        }
                        .shadow(color: isActive ? .blue.opacity(0.45) : .clear, radius: 5 * microphoneScale)
                        .contentShape(Circle())
                }
                .buttonStyle(.plain)
                .disabled(recognizer.state == .finishing)
                .accessibilityLabel(recognizer.state == .requestingPermission ? "Cancel microphone request" : speaker.isSpeaking ? "Stop speaking" : buttonTitle)
                .accessibilityIdentifier("assistant.microphone")

            }
            .padding(.horizontal, 8 * microphoneScale)
            .frame(height: 64 * microphoneScale)
            .offset(x: 10 * microphoneScale, y: 14 * microphoneScale - (isLandscape ? 8 : 0))
        }
        .onChange(of: selectedTab) { _, tab in
            if tab != .scan {
                stopAudio()
                isExpanded = false
            }
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

    private var isActive: Bool { recognizer.state != .idle || speaker.isSpeaking }

    // Preserve portrait geometry; scale the entire control together for the
    // shorter landscape tab row, keeping a minimum 44-point touch target.
    private var microphoneScale: CGFloat { isLandscape ? 0.8 : 1 }

    private var panelHeightLimit: CGFloat {
        min(180, max(44, availableHeight - 64 * microphoneScale - 100))
    }

    private var microphoneSymbol: String {
        if speaker.isSpeaking || recognizer.state == .listening { return "stop.fill" }
        if recognizer.state == .requestingPermission { return "xmark" }
        if recognizer.state == .finishing { return "ellipsis" }
        return "mic.fill"
    }

    private var hasContent: Bool {
        !recognizer.transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
        !reply.isEmpty || recognizer.errorMessage != nil || speaker.errorMessage != nil
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

    private func microphoneTapped() {
        selectedTab = .scan
        isExpanded = true
        if recognizer.state == .requestingPermission {
            stopAudio()
            isExpanded = false
            return
        }
        if speaker.isSpeaking {
            speaker.stop()
            return
        }
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

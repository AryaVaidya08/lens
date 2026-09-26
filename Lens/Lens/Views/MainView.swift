import SwiftUI

/// Navigation for Anthony's profile, voice, and settings work.
/// CameraView remains the AR lane's integration point.
struct MainView: View {
    var body: some View {
        TabView {
            NavigationStack {
                CameraView()
                    .navigationTitle("Scan")
            }
            .tabItem { Label("Scan", systemImage: "viewfinder") }

            VoiceAssistantView()
                .tabItem { Label("Assistant", systemImage: "waveform") }

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
    }
}

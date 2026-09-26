import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        NavigationStack {
            Form {
                if let profile = appState.selectedHCP {
                    Section("Current profile") {
                        LabeledContent("Name", value: profile.name)
                        LabeledContent("Specialty", value: profile.specialty)
                    }
                }

                Section {
                    Button("Log out", role: .destructive) {
                        appState.logOut()
                    }
                    .accessibilityIdentifier("settings.logout")
                } footer: {
                    Text("Logging out clears your saved profile from this device. You'll choose a profile the next time you open Lens.")
                }
            }
            .navigationTitle("Settings")
        }
    }
}

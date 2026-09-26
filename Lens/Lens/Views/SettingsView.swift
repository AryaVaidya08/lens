import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var profileToEdit: HCP?

    var body: some View {
        NavigationStack {
            Form {
                if let profile = appState.selectedHCP {
                    Section("Current profile") {
                        LabeledContent("Name", value: profile.name)
                        LabeledContent("Specialty", value: profile.specialty)
                        Button {
                            profileToEdit = profile
                        } label: {
                            Label {
                                Text("Edit profile")
                            } icon: {
                                Image(systemName: "pencil")
                                    .fontWeight(.bold)
                            }
                        }
                        .accessibilityIdentifier("settings.editProfile")
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
            .contentMargins(.top, 8, for: .scrollContent)
            .tabHeader("Settings")
        }
        .sheet(item: $profileToEdit) { profile in
            EditProfileView(profile: profile)
        }
    }
}

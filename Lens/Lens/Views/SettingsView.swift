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
                        if let email = profile.email, !email.isEmpty {
                            LabeledContent("Email", value: email)
                        }
                        if let organization = profile.organization, !organization.isEmpty {
                            LabeledContent("Organization", value: organization)
                        }
                        LabeledContent("Patients", value: "\(profile.patientIds?.count ?? 0)")
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
                        Task {
                            try? await APIClient.shared.logout()
                            APIClient.shared.clearSession()
                            appState.logOut()
                        }
                    }
                    .accessibilityIdentifier("settings.logout")
                } footer: {
                    Text("Logging out clears this account from the phone. Patient charts stay in the clinic database and are only viewed here.")
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

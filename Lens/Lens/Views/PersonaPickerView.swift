//
//  Demo login stand-in.
//
//  A list of preset HCP personas to tap — this *is* the auth for the
//  demo (see docs/architecture.md: "Auth" row). Sets
//  AppState.selectedHCP; the app root switches to the signed-in screens.
//
//  Owned by: Anthony (profile selection and persistence).
//

import SwiftUI

struct PersonaPickerView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text("Choose your demo profile to get started. We'll remember your choice on this device.")
                        .foregroundStyle(.secondary)
                }

                Section("HCP profiles") {
                    ForEach(HCP.demoProfiles) { profile in
                        Button {
                            appState.selectedHCP = profile
                        } label: {
                            HStack(spacing: 14) {
                                Image(systemName: "person.crop.circle.fill")
                                    .font(.largeTitle)
                                    .foregroundStyle(.tint)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(profile.name).font(.headline)
                                    Text(profile.specialty)
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 8)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("profile.\(profile.id)")
                    }
                }
            }
            .navigationTitle("Welcome to Lens")
        }
    }
}

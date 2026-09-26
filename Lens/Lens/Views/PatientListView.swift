import SwiftUI

struct PatientListView: View {
    @EnvironmentObject private var appState: AppState
    @State private var patients: [Patient] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && patients.isEmpty {
                    ProgressView("Loading clinic records")
                } else if let errorMessage, patients.isEmpty {
                    ContentUnavailableView(
                        "Couldn't load patients",
                        systemImage: "folder.badge.questionmark",
                        description: Text(errorMessage)
                    )
                } else if patients.isEmpty {
                    ContentUnavailableView(
                        "No patients yet",
                        systemImage: "folder",
                        description: Text("Patients are added from the Lens web dashboard. They can't be created here.")
                    )
                } else {
                    List {
                        ForEach(patients) { patient in
                            NavigationLink {
                                PatientDetailView(patient: patient)
                            } label: {
                                PatientFolderRow(patient: patient)
                            }
                            .accessibilityIdentifier("patient.\(patient.id)")
                        }
                    }
                    .accessibilityIdentifier("patients.list")
                }
            }
            .contentMargins(.top, 8, for: .scrollContent)
            .tabIslandBottomClearance()
            .tabHeader("Patients")
        }
        .task { await load() }
        .refreshable { await load() }
    }

    @MainActor
    private func load() async {
        guard let hcpId = appState.selectedHCP?.id else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            patients = try await APIClient.shared.listPatients(hcpId: hcpId)
            errorMessage = nil
            if var profile = appState.selectedHCP {
                profile.patientIds = patients.map(\.id)
                appState.selectedHCP = profile
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

private struct PatientFolderRow: View {
    let patient: Patient

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "folder.fill")
                .font(.title2)
                .foregroundStyle(.tint)
            VStack(alignment: .leading, spacing: 4) {
                Text(patient.displayName).font(.headline)
                Text(subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }

    private var subtitle: String {
        var parts: [String] = []
        if let age = patient.age { parts.append("Age \(age)") }
        if let weight = patient.weightKg {
            parts.append(String(format: "%.1f kg", weight))
        }
        if !patient.medicalHistory.isEmpty { parts.append(patient.medicalHistory) }
        return parts.isEmpty ? "Imported from clinic" : parts.joined(separator: " · ")
    }
}

import SwiftUI

struct PatientDetailView: View {
    let patient: Patient

    var body: some View {
        List {
            Section {
                NavigationLink {
                    MedicationReviewsView(patient: patient)
                } label: {
                    Label("Medication Review", systemImage: "pills")
                }
                .accessibilityIdentifier("patient.medicationReviews")
                NavigationLink {
                    MedicationAccessView(patient: patient)
                } label: {
                    Label("Medication Access", systemImage: "doc.text.magnifyingglass")
                }
                .accessibilityIdentifier("patient.medicationAccess")
            }
            Section("Chart") {
                LabeledContent("Name", value: patient.displayName)
                LabeledContent("Age", value: patient.age.map(String.init) ?? "—")
                LabeledContent("Weight", value: patient.weightKg.map { String(format: "%.1f kg", $0) } ?? "—")
                LabeledContent("Sex", value: patient.sex.isEmpty ? "—" : patient.sex)
                if !patient.recordId.isEmpty {
                    LabeledContent("Record ID", value: patient.recordId)
                }
                if !patient.sourceLabel.isEmpty {
                    LabeledContent("Source", value: patient.sourceLabel)
                }
            }
            Section("Medical history") {
                Text(patient.medicalHistory.isEmpty ? "None recorded" : patient.medicalHistory)
            }
            Section("Allergies") {
                Text(patient.allergies.isEmpty ? "None recorded" : patient.allergies)
            }
            Section("Current medications") {
                Text(patient.currentMedications.isEmpty ? "None recorded" : patient.currentMedications)
            }
            Section("Notes") {
                Text(patient.notes.isEmpty ? "No notes" : patient.notes)
            }
        }
        .navigationTitle(patient.displayName)
        .safeAreaInset(edge: .bottom) {
            Text("Chart is read-only. Medication reviews and access cases are saved separately.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .background(.background)
        }
        .tabIslandBottomClearance()
    }
}

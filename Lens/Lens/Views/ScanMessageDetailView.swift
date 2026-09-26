import SwiftUI

/// Snapshot the tapped result so camera updates cannot change the message being read.
struct ScanMessageDetails: Identifiable {
    let id = UUID()
    let summary: DrugSummary
    var patient: Patient? = nil
    var error: String? = nil
    var isOffline = false
}

struct ScanMessageDetailView: View {
    let message: ScanMessageDetails
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let patient = message.patient {
                        Label(patient.displayName, systemImage: "person.crop.circle")
                            .font(.title2.bold())
                        if let check = message.summary.chartCheck(for: patient.id), check.hasConcerns {
                            Text("Possible interactions and allergy concerns").font(.headline)
                            Text(check.headline).foregroundStyle(.orange)
                            ForEach(Array(check.displayFlags.enumerated()), id: \.offset) { _, flag in
                                Text("• " + flag)
                            }
                            Text(check.disclaimer).font(.footnote).foregroundStyle(.secondary)
                        } else if message.error != nil {
                            unavailable
                        }
                        Text("Recorded allergies").font(.headline)
                        Text(chartText(patient.allergies))
                        Text("Current medications").font(.headline)
                        Text(chartText(patient.currentMedications))
                    } else {
                        if message.isOffline {
                            Label("Offline information", systemImage: "wifi.slash")
                                .foregroundStyle(.secondary)
                        }
                        Text(message.summary.headline)
                            .font(.title2.bold())
                            .fixedSize(horizontal: false, vertical: true)
                        ForEach(Array(message.summary.expandedBullets.enumerated()), id: \.offset) { _, text in
                            Text(text)
                                .font(.body)
                                .multilineTextAlignment(.leading)
                                .lineLimit(nil)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(20)
                .textSelection(.enabled)
            }
            .navigationTitle(message.summary.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: {
                        Image(systemName: "xmark").frame(width: 44, height: 44)
                    }
                    .accessibilityLabel("Close full message")
                }
            }
        }
    }

    private var unavailable: some View {
        Text(message.error ?? "Patient check unavailable. Interactions and allergy risks have not been assessed.")
            .foregroundStyle(.secondary)
    }

    private func chartText(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "Not recorded" : value
    }
}

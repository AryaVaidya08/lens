//
//  AR-anchored info bubble.
//
//  The SwiftUI view CameraView positions at a detection's on-screen
//  location. Same content model as HUDView (the non-AR fallback) — keep
//  them in sync so personalization changes show up in both.
//
//  Owned by: AR & detection lane.
//


import SwiftUI

struct HUDOverlayView: View {
    let summary: DrugSummary

    var patient: Patient? = nil
    var isLoading = false
    var checkError: String? = nil
    var retry: (() -> Void)? = nil
    var isOffline = false
    var onExpand: (() -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 4) {
                Text(summary.name).font(.subheadline.bold())
                if let patient, !isLoading, let check = summary.chartCheck(for: patient.id), check.hasNoMatches {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                        .accessibilityLabel("No allergy or medication conflicts found")
                }
            }
            if let patient {
                patientContent(patient)
            } else if isLoading {
                loadingStatus("Loading details…")
            } else {
                if isOffline {
                    Label("Offline information", systemImage: "wifi.slash")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                Text(summary.headline)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                if summary.summarySource == "reference" {
                    Text("Reference excerpts · AI summary unavailable")
                        .font(.caption2).foregroundStyle(.secondary)
                }
                ForEach(Array(cardPreview.enumerated()), id: \.offset) { _, bullet in
                    Text("• " + bullet)
                        .font(.caption2)
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                }
                if isOffline, let retry {
                    Button("Retry live details", action: retry).font(.caption2)
                }
            }
            if !isLoading, patient == nil, onExpand != nil {
                HStack {
                    Spacer()
                    Image(systemName: "arrow.up.left.and.arrow.down.right")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .accessibilityHidden(true)
                }
            }
        }
        .contentShape(Rectangle())
        .onTapGesture { if !isLoading { onExpand?() } }
        .padding(8)
        .frame(maxWidth: patient == nil ? 280 : 300, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .shadow(radius: 6)
    }

    /// About a quarter of the rewrite stays on the bubble. The opened chat lists the rest.
    private var cardPreview: [String] {
        let all = summary.previewBullets
        guard !all.isEmpty else { return [] }
        let visible = max(1, (all.count + 3) / 4)
        return Array(all.prefix(visible))
    }

    private func patientContent(_ patient: Patient) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            if let check = summary.chartCheck(for: patient.id), check.hasConcerns {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Possible interactions and allergy concerns")
                        .font(.caption.weight(.semibold))
                    Text(check.headline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.orange)
                    ForEach(Array(check.displayFlags.prefix(2).enumerated()), id: \.offset) { _, flag in
                        Text("• " + flag)
                            .lineLimit(2)
                    }
                    Text("Chart name match · Tap to read details")
                        .foregroundStyle(.secondary)
                }
            } else if isLoading {
                loadingStatus("Checking patient chart…")
            } else if checkError != nil {
                unavailableCheck
            }
            chartField("Recorded allergies", value: patient.allergies)
            chartField("Current medications", value: patient.currentMedications)
        }
        .font(.caption2)
        .foregroundStyle(.primary)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func loadingStatus(_ title: String) -> some View {
        VStack(spacing: 6) {
            ProgressView()
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 4)
    }

    private var unavailableCheck: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(checkError ?? "Patient check unavailable. Interactions and allergy risks have not been assessed.")
                .foregroundStyle(.secondary)
            if let retry { Button("Retry patient check", action: retry) }
        }
    }

    private func chartField(_ title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title).fontWeight(.semibold)
            Text(value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "Not recorded" : value)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

#Preview {
    HUDOverlayView(
        summary: DrugSummary(
            drugId: "preview-drug",
            name: "Sample Drug",
            tier: "new",
            headline: "Fast-acting oral tablet",
            bullets: ["Standard adult dose: 10mg once daily", "Common use: hypertension"]
        )
    )
}

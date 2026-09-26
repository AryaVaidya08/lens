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
    /// Raw decoded barcode string — debug-only, for verifying Vision is
    /// reading the right symbol. Pass `nil` to hide it (e.g. once a real
    /// backend lookup replaces the fake resolver and this stops being
    /// interesting to show live).
    var debugRawPayload: String? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(summary.name)
                .font(.headline)

            Text(summary.headline)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            VStack(alignment: .leading, spacing: 3) {
                ForEach(summary.bullets, id: \.self) { bullet in
                    HStack(alignment: .top, spacing: 4) {
                        Text("•")
                        Text(bullet)
                    }
                    .font(.caption)
                }
            }

            if let debugRawPayload {
                Divider()
                Text("raw: \(debugRawPayload)")
                    .font(.caption2.monospaced())
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
        }
        .padding(12)
        .frame(maxWidth: 240, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .shadow(radius: 6)
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
        ),
        debugRawPayload: "036000291452"
    )
}

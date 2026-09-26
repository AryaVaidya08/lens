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

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(summary.name)
                .font(.subheadline.bold())

            Text(summary.headline)
                .font(.caption)
                .foregroundStyle(.secondary)

            VStack(alignment: .leading, spacing: 2) {
                ForEach(summary.bullets, id: \.self) { bullet in
                    HStack(alignment: .top, spacing: 3) {
                        Text("•")
                        Text(bullet)
                    }
                    .font(.caption2)
                }
            }
        }
        .padding(8)
        .frame(maxWidth: 150, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
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
        )
    )
}

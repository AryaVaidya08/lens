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

            if let check = summary.patientCheck {
                Divider().padding(.vertical, 2)
                Label(check.headline, systemImage: check.isFlag ? "exclamationmark.triangle.fill" : "checkmark.circle")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(check.isFlag ? Color.orange : Color.green)
                    .fixedSize(horizontal: false, vertical: true)
                ForEach(check.flags, id: \.self) { flag in
                    Text(flag)
                        .font(.caption2)
                }
                Text(check.disclaimer)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(8)
        .frame(maxWidth: summary.patientCheck == nil ? 150 : 240, alignment: .leading)
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

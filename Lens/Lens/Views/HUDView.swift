//
//  Non-AR fallback HUD.
//
//  Same content model as HUDOverlayView, rendered as a plain on-screen
//  card instead of an AR-anchored one — useful if ARKit anchoring is
//  flaky during the demo, or on the simulator where ARKit doesn't run.
//
//  Owned by: AR & detection lane.
//

import SwiftUI

struct HUDView: View {
    let summary: DrugSummary

    var body: some View {
        // TODO: implement — render summary.headline and summary.bullets
        // as a plain SwiftUI card.
        Text("TODO: implement")
    }
}

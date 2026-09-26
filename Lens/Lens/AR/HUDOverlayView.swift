//
//  AR-anchored info card.
//
//  The SwiftUI view rendered at the ARSessionManager's placed anchor.
//  Same content model as HUDView (the non-AR fallback) — keep them in
//  sync so personalization changes show up in both.
//
//  Owned by: AR & detection lane.
//

import SwiftUI

struct HUDOverlayView: View {
    let summary: DrugSummary

    var body: some View {
        // TODO: implement — render summary.headline and summary.bullets
        // in a compact card styled for an AR overlay (semi-transparent
        // background, readable at arm's length).
        Text("TODO: implement")
    }
}

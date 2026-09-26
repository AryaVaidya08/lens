//
//  ARKit session lifecycle + anchor placement.
//
//  Owns the ARSession/ARSCNView, and turns a detection result into a
//  spatially anchored HUD. This is what makes the info feel "placed on
//  the object" rather than a flat overlay.
//
//  Owned by: AR & detection lane.
//

import ARKit
import SceneKit

/// Result of a successful on-device detection, handed to the AR layer
/// so it knows what to anchor and where.
struct DetectionResult {
    let drugId: String
    let name: String
    // TODO: implement — add screen-space or world-space hit-test info
    // needed to place the anchor (e.g. the CGPoint tapped/detected at).
}

final class ARSessionManager: NSObject, ObservableObject {
    // TODO: implement — hold the ARSCNView/ARSession and configuration
    // (ARWorldTrackingConfiguration).

    /// Places a spatial anchor at the location implied by `result`, so
    /// HUDOverlayView can be positioned there.
    ///
    /// TODO: implement — run a hit-test / raycast from the detection
    /// point, create an ARAnchor, and attach a SceneKit node that hosts
    /// the SwiftUI HUD content.
    func placeAnchor(for result: DetectionResult) {
        // TODO: implement
    }
}

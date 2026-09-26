//
//  Camera + AR host view.
//
//  Hosts the live camera feed via ARSessionManager, runs
//  BarcodeScanner/TextRecognizer against incoming frames, and shows
//  HUDOverlayView once a drug is detected and its summary fetched.
//
//  Owned by: AR & detection lane.
//

import SwiftUI

struct CameraView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        // TODO: implement — wrap ARSessionManager in a UIViewRepresentable
        // (or use RealityKit's ARView equivalent), run detection on
        // frames, call APIClient.detectDrug + getSummary on a hit, then
        // show HUDOverlayView anchored via ARSessionManager.placeAnchor.
        Text("TODO: implement")
    }
}

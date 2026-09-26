//
//  Demo login stand-in.
//
//  A list of preset HCP personas to tap — this *is* the auth for the
//  demo (see docs/architecture.md: "Auth" row). Sets
//  AppState.selectedHCP and pushes into CameraView.
//
//  Owned by: AR & detection lane.
//

import SwiftUI

struct PersonaPickerView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        // TODO: implement — list a few preset HCP personas (name +
        // specialty), fetched via APIClient.getProfile or hardcoded for
        // the demo, and set appState.selectedHCP on tap before
        // navigating to CameraView.
        Text("TODO: implement")
    }
}

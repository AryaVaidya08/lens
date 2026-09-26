//
//  App entry point.
//
//  Launches straight into PersonaPickerView — there's no auth, so the
//  persona pick *is* the login step. Owns the single AppState instance
//  shared down through the view hierarchy.
//
//  Owned by: AR & detection lane (shell) / whole team (shared state).
//

import SwiftUI

@main
struct HCPCopilotApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            // TODO: implement — inject appState as an environmentObject
            // and show PersonaPickerView first.
            PersonaPickerView()
                .environmentObject(appState)
        }
    }
}

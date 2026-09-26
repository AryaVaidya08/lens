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
            // DEV SHORTCUT: launching straight into CameraView so the
            // detection/HUD work is testable before PersonaPickerView
            // (Anthony's task) is implemented. Revert to PersonaPickerView
            // once that's done — see git history for the real entry point.
            CameraView()
                .environmentObject(appState)
        }
    }
}

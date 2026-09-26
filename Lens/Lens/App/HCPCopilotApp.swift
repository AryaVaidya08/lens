//
//  App entry point.
//
//  Restores the saved demo profile or presents the persona picker.
//  Owns the single AppState instance shared through the view hierarchy.
//
//  Owned by: AR & detection lane (shell) / whole team (shared state).
//

import SwiftUI

@main
struct HCPCopilotApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            Group {
                if let profile = appState.selectedHCP {
                    MainView()
                        .id(profile.id)
                } else {
                    PersonaPickerView()
                }
            }
            .environmentObject(appState)
        }
    }
}

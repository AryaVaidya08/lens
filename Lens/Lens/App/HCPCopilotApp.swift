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
    @State private var isShowingSplash = true

    var body: some Scene {
        WindowGroup {
            ZStack {
                Group {
                    if let profile = appState.selectedHCP {
                        MainView()
                            .id(profile.id)
                    } else {
                        PersonaPickerView()
                    }
                }

                if isShowingSplash {
                    LaunchSplashView()
                        .allowsHitTesting(false)
                        .transition(.opacity)
                        .zIndex(1)
                }
            }
            .environmentObject(appState)
            .task {
                try? await Task.sleep(for: .seconds(1.2))
                withAnimation(.easeOut(duration: 0.4)) {
                    isShowingSplash = false
                }
            }
        }
    }
}

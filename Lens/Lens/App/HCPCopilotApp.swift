//
//  App entry point.
//
//  Restores the saved demo profile or presents the persona picker.
//  Owns the single AppState instance shared through the view hierarchy.
//
//  Owned by: AR & detection lane (shell) / whole team (shared state).
//

import Combine
import SwiftUI

@main
struct HCPCopilotApp: App {
    @StateObject private var appState = AppState()
    @State private var isShowingSplash = true

    var body: some Scene {
        WindowGroup {
            ZStack {
                Group {
                    if appState.isSignedIn, let profile = appState.selectedHCP {
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
            .onAppear {
                APIClient.shared.sessionToken = appState.sessionToken
            }
            .onChange(of: appState.sessionToken) { _, token in
                APIClient.shared.sessionToken = token
            }
            .alert("Save your recovery code", isPresented: Binding(
                get: { appState.pendingRecoveryCode != nil },
                set: { if !$0 { appState.pendingRecoveryCode = nil } }
            )) {
                Button("I saved it") { appState.pendingRecoveryCode = nil }
            } message: {
                Text("This is the only time Lens will show it. Use it to reset your password.\n\n\(appState.pendingRecoveryCode ?? "")")
            }
            .task {
                try? await Task.sleep(for: .seconds(1.2))
                withAnimation(.easeOut(duration: 0.4)) {
                    isShowingSplash = false
                }
            }
        }
    }
}

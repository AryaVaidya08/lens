import SwiftUI
import UIKit

enum MainTab: Hashable {
    case scan, history, patients, settings
}

struct MainView: View {
    @EnvironmentObject private var appState: AppState
    @State private var selectedTab: MainTab = .scan
    @State private var isLandscape = false
    @StateObject private var assistant = VoiceAssistantSession()

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack {
                CameraView()
                    .toolbar(.hidden, for: .navigationBar)
            }
            .tag(MainTab.scan)
            .toolbar(.hidden, for: .tabBar)
            .toolbarVisibility(.hidden, for: .tabBar)

            HistoryView()
                .tag(MainTab.history)
                .toolbar(.hidden, for: .tabBar)
                .toolbarVisibility(.hidden, for: .tabBar)

            PatientListView()
                .tag(MainTab.patients)
                .toolbar(.hidden, for: .tabBar)
                .toolbarVisibility(.hidden, for: .tabBar)

            SettingsView()
                .tag(MainTab.settings)
                .toolbar(.hidden, for: .tabBar)
                .toolbarVisibility(.hidden, for: .tabBar)
        }
        .toolbar(.hidden, for: .tabBar)
        .toolbarVisibility(.hidden, for: .tabBar)
        .background {
            SuppressSystemTabBar()
            GeometryReader { proxy in
                Color.clear.preference(key: MainViewSizeKey.self, value: proxy.size)
            }
        }
        .onPreferenceChange(MainViewSizeKey.self) { size in
            isLandscape = size.width > size.height
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            VStack(spacing: 8) {
                if selectedTab == .scan {
                    VoiceAssistantView(
                        assistant: assistant,
                        selectedTab: $selectedTab,
                        isLandscape: isLandscape,
                        availableHeight: isLandscape ? 400 : 800
                    )
                    .fixedSize(horizontal: false, vertical: true)
                }

                MainTabIsland(
                    selectedTab: $selectedTab,
                    assistant: assistant,
                    isLandscape: isLandscape,
                    onMicrophoneTap: {
                        assistant.microphoneTapped(
                            currentDrug: { appState.currentDrug },
                            hcpId: { appState.selectedHCP?.id },
                            recordChat: { question, answer in
                                appState.recordChat(question: question, answer: answer)
                            }
                        )
                    }
                )
            }
            .frame(maxWidth: .infinity)
            .padding(.bottom, 6)
        }
        .task {
            APIClient.shared.sessionToken = appState.sessionToken
            guard let id = appState.selectedHCP?.id else { return }
            do {
                let profile = try await APIClient.shared.getProfile(hcpId: id)
                if appState.selectedHCP?.id == profile.id {
                    appState.selectedHCP = profile
                }
            } catch let error as APIError where error.requiresReauthentication {
                APIClient.shared.clearSession()
                appState.logOut()
            } catch {
                // Keep the cached profile if the refresh fails for a transient reason.
            }
        }
        .onAppear {
            if appState.openScanTab {
                selectedTab = .scan
                appState.openScanTab = false
            }
        }
        .onChange(of: appState.openScanTab) { _, open in
            guard open else { return }
            selectedTab = .scan
            appState.openScanTab = false
        }
        .onChange(of: selectedTab) { _, tab in
            if tab != .scan {
                assistant.leaveScanTab()
                appState.endScanSession()
            }
        }
    }
}

private struct MainViewSizeKey: PreferenceKey {
    static var defaultValue: CGSize = .zero
    static func reduce(value: inout CGSize, nextValue: () -> CGSize) {
        value = nextValue()
    }
}

/// TabView still owns the screens so the camera can stay retained, but
/// the system tab island is replaced by `MainTabIsland`.
private struct SuppressSystemTabBar: UIViewRepresentable {
    func makeUIView(context: Context) -> UIView {
        let view = UIView()
        view.isUserInteractionEnabled = false
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        DispatchQueue.main.async {
            var current: UIView? = uiView
            while let view = current {
                if let tabBar = view as? UITabBar {
                    tabBar.isHidden = true
                    return
                }
                if let controller = view.next as? UITabBarController {
                    controller.tabBar.isHidden = true
                    return
                }
                current = view.superview
            }
        }
    }
}

import SwiftUI

enum MainTab: Hashable {
    case scan, settings
}

struct MainView: View {
    @State private var selectedTab: MainTab = .scan

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            TabView(selection: $selectedTab) {
                NavigationStack {
                    CameraView()
                        .toolbar(.hidden, for: .navigationBar)
                }
                .tag(MainTab.scan)
                .tabItem { Label("Scan", systemImage: "viewfinder") }

                SettingsView()
                    .tag(MainTab.settings)
                    .tabItem { Label("Settings", systemImage: "gearshape") }
            }

            if selectedTab == .scan {
                GeometryReader { geometry in
                    VoiceAssistantView(
                        selectedTab: $selectedTab,
                        isLandscape: geometry.size.width > geometry.size.height,
                        availableHeight: geometry.size.height
                    )
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomLeading)
                }
            }
        }
    }
}

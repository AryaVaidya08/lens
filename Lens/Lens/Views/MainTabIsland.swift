import SwiftUI

struct MainTabIsland: View {
    @Binding var selectedTab: MainTab
    @ObservedObject var assistant: VoiceAssistantSession
    var isLandscape = false
    var onMicrophoneTap: () -> Void

    var body: some View {
        HStack(spacing: 0) {
            sideButton(
                tab: .patients,
                title: "Patients",
                systemImage: "folder",
                identifier: "tab.patients"
            )
            sideButton(
                tab: .history,
                title: "History",
                systemImage: "clock.arrow.circlepath",
                identifier: "tab.history"
            )

            centerButton

            sideButton(
                tab: .settings,
                title: "Settings",
                systemImage: "gearshape",
                identifier: "tab.settings"
            )
        }
        .padding(.horizontal, 6 * scale)
        .padding(.vertical, 4 * scale)
        .frame(width: 340 * scale)
        .glassEffect(.regular, in: .capsule)
        .accessibilityElement(children: .contain)
        .accessibilityAddTraits(.isTabBar)
        .accessibilityIdentifier("main.tabBar")
    }

    private var scale: CGFloat { isLandscape ? 0.8 : 1 }

    private var isOnScan: Bool { selectedTab == .scan }

    private var centerButton: some View {
        Button(action: centerTapped) {
            islandLabel(
                title: isOnScan ? "Mic" : "Scan",
                systemImage: centerSymbol,
                isSelected: isOnScan,
                isActiveMic: isOnScan && assistant.isActive
            )
        }
        .buttonStyle(.plain)
        .disabled(isOnScan && assistant.recognizer.state == .finishing)
        .accessibilityLabel(isOnScan ? assistant.microphoneAccessibilityLabel : "Scan")
        .accessibilityIdentifier(isOnScan ? "assistant.microphone" : "tab.scan")
        .modifier(SelectedTabTrait(isSelected: isOnScan))
    }

    private func sideButton(tab: MainTab, title: String, systemImage: String, identifier: String) -> some View {
        Button {
            selectedTab = tab
        } label: {
            islandLabel(
                title: title,
                systemImage: systemImage,
                isSelected: selectedTab == tab,
                isActiveMic: false
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(title)
        .accessibilityIdentifier(identifier)
        .modifier(SelectedTabTrait(isSelected: selectedTab == tab))
    }

    private func islandLabel(title: String, systemImage: String, isSelected: Bool, isActiveMic: Bool) -> some View {
        VStack(spacing: 2 * scale) {
            Image(systemName: systemImage)
                .font(.system(size: 17 * scale, weight: .semibold))
                .frame(height: 22 * scale)
            Text(title)
                .font(.system(size: 10 * scale, weight: .medium))
        }
        .foregroundStyle(isActiveMic ? Color.white : (isSelected ? Color.accentColor : Color.primary.opacity(0.7)))
        .frame(maxWidth: .infinity)
        .frame(height: 48 * scale)
        .background {
            if isActiveMic {
                Capsule().fill(.black)
            }
        }
        .overlay {
            if isActiveMic {
                Capsule().strokeBorder(Color.blue, lineWidth: 2 * scale)
            }
        }

        .contentShape(Rectangle())
    }

    private var centerSymbol: String {
        isOnScan ? assistant.microphoneSymbol : "viewfinder"
    }

    private func centerTapped() {
        if isOnScan {
            onMicrophoneTap()
        } else {
            selectedTab = .scan
        }
    }
}

extension View {
    func tabIslandBottomClearance() -> some View {
        safeAreaPadding(.bottom, 72)
    }
}

private struct SelectedTabTrait: ViewModifier {
    let isSelected: Bool

    func body(content: Content) -> some View {
        if isSelected {
            content.accessibilityAddTraits(.isSelected)
        } else {
            content
        }
    }
}

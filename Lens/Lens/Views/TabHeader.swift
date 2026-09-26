import SwiftUI

private struct TabHeader: ViewModifier {
    let title: String

    func body(content: Content) -> some View {
        content
            .navigationTitle(title)
            .toolbar(.hidden, for: .navigationBar)
            .safeAreaInset(edge: .top, spacing: 0) {
                Text(title)
                    .font(.largeTitle.bold())
                    .accessibilityAddTraits(.isHeader)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(.background)
            }
    }
}

extension View {
    /// A left-aligned title without the navigation bar's empty toolbar row.
    func tabHeader(_ title: String) -> some View {
        modifier(TabHeader(title: title))
    }
}

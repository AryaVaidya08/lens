import SwiftUI

/// Matches the system launch screen (LaunchLogo on LaunchBackground) so the
/// hand-off into the app is seamless while the camera session warms up.
struct LaunchSplashView: View {
    @State private var isPulsing = false

    var body: some View {
        ZStack {
            Color("LaunchBackground")
                .ignoresSafeArea()
            Image("LaunchLogo")
                .resizable()
                .scaledToFit()
                .frame(width: 150, height: 150)
                .opacity(isPulsing ? 0.6 : 1)
                .scaleEffect(isPulsing ? 0.96 : 1)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Lens is loading")
        .onAppear {
            withAnimation(.easeInOut(duration: 0.9).repeatForever(autoreverses: true)) {
                isPulsing = true
            }
        }
    }
}

#Preview {
    LaunchSplashView()
}

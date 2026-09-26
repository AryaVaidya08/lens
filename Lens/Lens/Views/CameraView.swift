//
//  Camera + AR host view.
//
//  Hosts the live camera feed via ARSessionManager, which runs a staged
//  detection pipeline (object detector -> barcode -> OCR text fallback —
//  see ARSessionManager's doc comment). This view draws the object
//  bounding box as soon as something's detected, then shows HUDOverlayView
//  once a barcode or text off of it resolves to a drug — positioned to one
//  side of the bounding box, gliding smoothly as it moves and fading out
//  if the object goes out of view (see ARSessionManager's design note on
//  why this is 2D screen tracking rather than a 3D-anchored node).
//
//  Owned by: AR & detection lane.
//

import SwiftUI
import ARKit

/// An ARSCNView that reports when it first receives real (non-zero) Auto
/// Layout-driven bounds.
///
/// The previous approach here manually assigned `.frame` from `updateUIView`
/// to fight a "camera renders square after a landscape launch" bug — but
/// SwiftUI's `UIViewRepresentable` host already sizes this view via its own
/// Auto Layout constraints, and forcing `.frame` on top of that (with
/// `translatesAutoresizingMaskIntoConstraints` still `true`) generates a
/// second, conflicting set of constraints — the "Unable to simultaneously
/// satisfy constraints" crash log. The actual fix is to never touch
/// `.frame`/constraints ourselves, and instead just make sure the AR
/// session doesn't start rendering until this view has already been given
/// its real, final, orientation-correct size by Auto Layout.
private final class SelfSizingARSCNView: ARSCNView {
    var onFirstLayout: (() -> Void)?
    private var hasReportedLayout = false

    override func layoutSubviews() {
        super.layoutSubviews()
        guard !hasReportedLayout, bounds.width > 0, bounds.height > 0 else { return }
        hasReportedLayout = true
        onFirstLayout?()
    }
}

/// Bridges ARSessionManager's ARSession into an ARSCNView for SwiftUI.
private struct ARCameraRepresentable: UIViewRepresentable {
    let session: ARSession
    /// Unlocks the initial start after layout. CameraView also tracks tab
    /// visibility and scene activity so the retained view can resume later.
    let onReady: () -> Void

    func makeUIView(context: Context) -> SelfSizingARSCNView {
        let view = SelfSizingARSCNView()
        view.session = session
        view.automaticallyUpdatesLighting = true
        view.onFirstLayout = onReady
        return view
    }

    func updateUIView(_ uiView: SelfSizingARSCNView, context: Context) {}
}

/// Reads the HUD bubble's rendered size so it can be positioned without
/// overlapping the barcode or running off the edge of the screen.
private struct SizePreferenceKey: PreferenceKey {
    static var defaultValue: CGSize = .zero
    static func reduce(value: inout CGSize, nextValue: () -> CGSize) {
        value = nextValue()
    }
}

struct CameraView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.scenePhase) private var scenePhase
    @State private var lifecycle = CameraSessionLifecycle()
    @StateObject private var arManager = ARSessionManager()
    @State private var bubbleSize: CGSize = CGSize(width: 220, height: 90)
    @State private var flashOpacity: Double = 1.0

    /// Debug aid so detection accuracy is visible while tuning — flip to
    /// `false` before the real demo.
    private let showDebugBoundingBox = true

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                ARCameraRepresentable(session: arManager.session) {
                    updateSession(.layoutReady)
                }
                .ignoresSafeArea()

                if showDebugBoundingBox, let objectBox = arManager.objectBoundingBox {
                    // Shows as soon as ObjectDetector finds something in
                    // frame — before a barcode/text has necessarily been
                    // read off of it yet, so this doubles as a "yes, I see
                    // your bottle" cue distinct from the info bubble below.
                    Rectangle()
                        .stroke(Color.green, lineWidth: 3)
                        .frame(
                            width: objectBox.width * geometry.size.width,
                            height: objectBox.height * geometry.size.height
                        )
                        .position(
                            x: objectBox.midX * geometry.size.width,
                            y: objectBox.midY * geometry.size.height
                        )
                        .animation(.easeOut(duration: 0.25), value: objectBox)
                }

                if let detection = arManager.activeDetection {
                    let scale = proximityScale(for: detection.screenAnchor)
                    let scaledBubbleSize = CGSize(width: bubbleSize.width * scale, height: bubbleSize.height * scale)

                    HUDOverlayView(summary: fakeSummary(for: detection), debugRawPayload: detection.rawPayload)
                        .background(
                            GeometryReader { bubbleGeometry in
                                Color.clear
                                    .preference(key: SizePreferenceKey.self, value: bubbleGeometry.size)
                            }
                        )
                        .scaleEffect(scale)
                        .opacity(flashOpacity)
                        .position(
                            bubblePosition(
                                for: detection.screenAnchor,
                                in: geometry.size,
                                bubbleSize: scaledBubbleSize
                            )
                        )
                        .animation(.easeOut(duration: 0.25), value: detection.screenAnchor)
                        .transition(.opacity)
                }
            }
        }
        .onPreferenceChange(SizePreferenceKey.self) { bubbleSize = $0 }
        .onAppear {
            arManager.resolvePayload = { kind, value in
                // TODO: implement — replace with a real
                // APIClient.shared.detectDrug(
                //     barcode: kind == "barcode" ? value : nil,
                //     ocrText: kind == "text" ? value : nil
                // ) call once Backend & data's /detect route is live.
                (drugId: "fake-drug-1", name: "Sample Drug")
            }
            arManager.currentInterfaceOrientation = currentInterfaceOrientation()
            UIDevice.current.beginGeneratingDeviceOrientationNotifications()
            updateSession(.active(scenePhase == .active))
            updateSession(.visible(true))
        }
        .onDisappear {
            UIDevice.current.endGeneratingDeviceOrientationNotifications()
            updateSession(.visible(false))
        }
        .onChange(of: scenePhase) { _, phase in
            updateSession(.active(phase == .active))
        }
        .onReceive(NotificationCenter.default.publisher(for: UIDevice.orientationDidChangeNotification)) { _ in
            arManager.currentInterfaceOrientation = currentInterfaceOrientation()
        }
        .onChange(of: arManager.activeDetection?.drugId) { _, newDrugId in
            guard let newDrugId else { return }
            appState.currentDrug = Drug(id: newDrugId, name: arManager.activeDetection?.name ?? "")
        }
        .onChange(of: arManager.isStale) { _, stale in
            if stale {
                withAnimation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true)) {
                    flashOpacity = 0.8
                }
            } else {
                withAnimation(.easeOut(duration: 0.15)) {
                    flashOpacity = 1.0
                }
            }
        }
    }

    private func updateSession(_ event: CameraSessionLifecycle.Event) {
        switch lifecycle.handle(event) {
        case .start: arManager.start()
        case .stop: arManager.stop()
        case nil: break
        }
    }

    private func currentInterfaceOrientation() -> UIInterfaceOrientation {
        UIApplication.shared.connectedScenes
            .compactMap { ($0 as? UIWindowScene)?.effectiveGeometry.interfaceOrientation }
            .first ?? .portrait
    }

    /// Approximates "how close is the phone to the barcode" from how much
    /// of the frame its bounding box fills — there's no real depth data
    /// without a 3D anchor/raycast (see ARSessionManager's design note),
    /// but box width as a fraction of screen width is a solid proxy: a
    /// barcode held close fills much more of the frame than one seen from
    /// across a desk. Returns a multiplier for `.scaleEffect`.
    private func proximityScale(for box: CGRect) -> CGFloat {
        let normalizedWidthWhenFar: CGFloat = 0.08
        let normalizedWidthWhenClose: CGFloat = 0.35
        let minScale: CGFloat = 0.7
        let maxScale: CGFloat = 1.3

        let t = (box.width - normalizedWidthWhenFar) / (normalizedWidthWhenClose - normalizedWidthWhenFar)
        let clampedT = min(max(t, 0), 1)
        return minScale + clampedT * (maxScale - minScale)
    }

    /// Places the bubble beside the barcode — to the right by default,
    /// flipping to the left if there isn't room — vertically centered on
    /// the box, and clamped so it always stays fully on screen.
    private func bubblePosition(for box: CGRect, in containerSize: CGSize, bubbleSize: CGSize) -> CGPoint {
        let margin: CGFloat = 16
        let boxCenter = CGPoint(x: box.midX * containerSize.width, y: box.midY * containerSize.height)
        let boxHalfWidth = (box.width * containerSize.width) / 2
        let bubbleHalfWidth = max(bubbleSize.width, 1) / 2
        let bubbleHalfHeight = max(bubbleSize.height, 1) / 2

        var x = boxCenter.x + boxHalfWidth + margin + bubbleHalfWidth
        if x + bubbleHalfWidth + margin > containerSize.width {
            x = boxCenter.x - boxHalfWidth - margin - bubbleHalfWidth
        }
        x = min(max(x, bubbleHalfWidth + margin), containerSize.width - bubbleHalfWidth - margin)

        let y = min(
            max(boxCenter.y, bubbleHalfHeight + margin),
            containerSize.height - bubbleHalfHeight - margin
        )

        return CGPoint(x: x, y: y)
    }

    /// TODO: implement — remove once getSummary() is live; this exists
    /// only to give the HUD bubble something to show for now.
    private func fakeSummary(for detection: DetectionResult) -> DrugSummary {
        DrugSummary(
            drugId: detection.drugId,
            name: detection.name,
            tier: "new",
            headline: "Fast-acting oral tablet",
            bullets: [
                "Standard adult dose: 10mg once daily",
                "Common use: hypertension",
                "Tap to ask a follow-up question"
            ]
        )
    }
}

#Preview {
    CameraView()
        .environmentObject(AppState())
}

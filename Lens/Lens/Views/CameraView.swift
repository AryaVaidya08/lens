//
//  Camera + AR host view.
//
//  Hosts the live camera feed via ARSessionManager, which runs a staged
//  detection pipeline (object detector -> barcode -> OCR text fallback —
//  see ARSessionManager's doc comment). This view shows HUDOverlayView
//  once a barcode or text off the detected object resolves to a drug —
//  positioned near the top-right of where the object was seen, gliding
//  smoothly as it moves and fading out if the object goes out of view
//  (see ARSessionManager's design note on why this is 2D screen tracking
//  rather than a 3D-anchored node).
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
    @StateObject private var resolver = DrugResolver()
    @State private var bubbleSize: CGSize = CGSize(width: 150, height: 70)
    @State private var flashOpacity: Double = 1.0
    /// Personalized content from GET /drug/{id}/summary. Nil until it arrives
    /// (or if the backend is unreachable), in which case the offline catalog
    /// fills the bubble so the HUD is never blank.
    @State private var summary: DrugSummary?
    @State private var loadingDrugId: String?

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                ARCameraRepresentable(session: arManager.session) {
                    updateSession(.layoutReady)
                }
                .ignoresSafeArea()

                if let detection = arManager.activeDetection {
                    let scale = proximityScale(for: detection.screenAnchor)
                    let scaledBubbleSize = CGSize(width: bubbleSize.width * scale, height: bubbleSize.height * scale)

                    HUDOverlayView(summary: displaySummary(for: detection))
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
                // Answers from cache immediately and fills that cache from
                // POST /detect in the background — see DrugResolver.
                guard let drug = MainActor.assumeIsolated({ resolver.resolve(kind: kind, value: value) }) else {
                    return nil
                }
                return (drugId: drug.id, name: drug.name)
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
            adopt(Drug(id: newDrugId, name: arManager.activeDetection?.name ?? ""))
        }
        .onChange(of: resolver.resolved) { _, _ in
            guard let detection = arManager.activeDetection,
                  let drug = resolver.cachedDrug(forRawPayload: detection.rawPayload) else { return }
            adopt(drug)
        }
        .onChange(of: arManager.isStale) { _, stale in
            if stale {
                withAnimation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true)) {
                    flashOpacity = 0.5
                }
            } else {
                withAnimation(.easeOut(duration: 0.15)) {
                    flashOpacity = 8.0
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
    /// flipping to the left if there isn't room — aligned near the top of
    /// the box rather than vertically centered, and clamped so it always
    /// stays fully on screen. The margin is deliberately generous (and the
    /// bubble deliberately small) so the bubble clears the bounding box
    /// instead of the screen-edge clamp pushing it back over the object
    /// being scanned.
    private func bubblePosition(for box: CGRect, in containerSize: CGSize, bubbleSize: CGSize) -> CGPoint {
        let margin: CGFloat = 24
        let topMargin: CGFloat = 8
        let boxCenterX = box.midX * containerSize.width
        let boxTop = box.minY * containerSize.height
        let boxHalfWidth = (box.width * containerSize.width) / 2
        let bubbleHalfWidth = max(bubbleSize.width, 1) / 2
        let bubbleHalfHeight = max(bubbleSize.height, 1) / 2

        var x = boxCenterX + boxHalfWidth + margin + bubbleHalfWidth
        if x + bubbleHalfWidth + margin > containerSize.width {
            x = boxCenterX - boxHalfWidth - margin - bubbleHalfWidth
        }
        x = min(max(x, bubbleHalfWidth + margin), containerSize.width - bubbleHalfWidth - margin)

        let y = min(
            max(boxTop + topMargin + bubbleHalfHeight, bubbleHalfHeight + margin),
            containerSize.height - bubbleHalfHeight - margin
        )

        return CGPoint(x: x, y: y)
    }

    /// The personalized summary once it arrives, otherwise the offline catalog
    /// so the bubble is populated the instant something is detected.
    private func displaySummary(for detection: DetectionResult) -> DrugSummary {
        if let summary, summary.drugId == appState.currentDrug?.id {
            return summary
        }
        let drugId = appState.currentDrug?.id ?? detection.drugId
        // `detection` only ever exists because resolvePayload matched a
        // known demo drug (see ARSessionManager.handleObjectSeen), so
        // `drugId` is always in the catalog — the empty summary below is
        // just a defensive fallback, never expected to be hit.
        return DemoDrugCatalog.drug(id: drugId)?.summary
            ?? DemoDrugCatalog.resolve(payload: detection.rawPayload)?.summary
            ?? DrugSummary(drugId: detection.drugId, name: detection.name, tier: "new", headline: "", bullets: [])
    }

    private func adopt(_ drug: Drug) {
        if appState.currentDrug != drug {
            appState.currentDrug = drug
            summary = nil
        }
        guard summary?.drugId != drug.id, loadingDrugId != drug.id else { return }
        loadingDrugId = drug.id
        Task { await loadPersonalizedContent(for: drug) }
    }

    /// The read-then-write half of the personalization loop: fetch the tier's
    /// content for this HCP, then log the touch so the next scan is one tier
    /// further along. Logging second is what makes scan 1 "new" and scan 2
    /// "returning" rather than both showing the post-scan tier.
    private func loadPersonalizedContent(for drug: Drug) async {
        guard let hcpId = appState.selectedHCP?.id else { return }
        do {
            let fetched = try await APIClient.shared.getSummary(drugId: drug.id, hcpId: hcpId)
            guard appState.currentDrug?.id == fetched.drugId else { return }
            summary = fetched
            appState.familiarityTier = fetched.tier
            try await APIClient.shared.logEngagement(hcpId: hcpId, drugId: drug.id)
        } catch {
            // Offline: the catalog summary stays on screen and the scan simply
            // isn't logged. Nothing to surface mid-demo.
        }
        if loadingDrugId == drug.id {
            loadingDrugId = nil
        }
    }
}

#Preview {
    CameraView()
        .environmentObject(AppState())
}

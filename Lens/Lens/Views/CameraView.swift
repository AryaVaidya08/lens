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

import ARKit
import Combine
import SwiftUI

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
    @StateObject private var engagementQueue = ScanEngagementQueue()
    @State private var bubbleSize: CGSize = CGSize(width: 150, height: 70)
    @State private var flashOpacity: Double = 1.0
    /// Personalized content; the offline catalog is used only after failure.
    @State private var summary: DrugSummary?
    @State private var loadingDrugId: String?
    @State private var failedSummaryDrugId: String?
    @State private var checkError: String?
    @State private var patientScanDrug: Drug?
    @State private var summaryRequestID = UUID()
    @State private var lastSummaryFailureAt: [String: Date] = [:]
    @State private var expandedMessage: ScanMessageDetails?
    @State private var engagementError: String?
    @State private var pendingTouchDrugId: String?

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                ARCameraRepresentable(session: arManager.session) {
                    updateSession(.layoutReady)
                }
                .ignoresSafeArea()

                VStack {
                    scanPatientChip
                    if let patient = appState.scanSessionPatient, let drug = patientScanDrug {
                        HUDOverlayView(
                            summary: patientSummary(for: drug),
                            patient: patient,
                            isLoading: loadingDrugId == drug.id,
                            checkError: checkError,
                            retry: { Task { await loadPersonalizedContent(for: drug, logTouch: false) } },
                            onExpand: {
                                expandedMessage = ScanMessageDetails(summary: patientSummary(for: drug), patient: patient, error: checkError)
                            }
                        )
                        .padding(.horizontal, 16)
                    }
                    Spacer()

                }
                .padding(.top, 12)

                if appState.scanSessionPatient == nil, let detection = arManager.activeDetection {
                    let drugId = resolver.cachedDrug(forRawPayload: detection.rawPayload)?.id ?? detection.drugId
                    let phase = ScanSummaryPhase.resolve(drugId: drugId, summary: summary, failedDrugId: failedSummaryDrugId)
                    let scale = proximityScale(for: detection.screenAnchor)
                    let scaledBubbleSize = CGSize(width: bubbleSize.width * scale, height: bubbleSize.height * scale)

                    HUDOverlayView(
                        summary: displaySummary(for: detection, phase: phase),
                        patient: appState.scanSessionPatient,
                        isLoading: phase == .loading,
                        checkError: checkError,
                        retry: {
                            guard let drug = appState.currentDrug else { return }
                            Task { await loadPersonalizedContent(for: drug, logTouch: false) }
                        },
                        isOffline: phase == .offline,
                        onExpand: {
                            expandedMessage = ScanMessageDetails(summary: displaySummary(for: detection, phase: phase), isOffline: phase == .offline)
                        }
                    )
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
        .overlay(alignment: .bottomTrailing) {
            if let engagementError, let drug = appState.currentDrug, summary?.drugId == drug.id {
                Text(engagementError)
                    .font(.caption)
                    .frame(maxWidth: 240, alignment: .trailing)
                    .padding(16)
            }
        }
        .fullScreenCover(item: $expandedMessage) { message in
            ScanMessageDetailView(message: message)
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
            APIClient.shared.sessionToken = appState.sessionToken
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
            guard let newDrugId else {
                engagementQueue.noteTrackingLost()
                return
            }
            adopt(Drug(id: newDrugId, name: arManager.activeDetection?.name ?? ""))
        }
        .onChange(of: resolver.resolved) { _, _ in
            guard let detection = arManager.activeDetection,
                  let drug = resolver.cachedDrug(forRawPayload: detection.rawPayload) else { return }
            adopt(drug)
        }
        .onChange(of: appState.scanSessionPatient?.id) { _, patientId in
            summaryRequestID = UUID()
            failedSummaryDrugId = nil
            checkError = nil
            summary = nil
            patientScanDrug = nil
            guard let detection = arManager.activeDetection else {
                loadingDrugId = nil
                return
            }
            let drug = resolver.cachedDrug(forRawPayload: detection.rawPayload)
                ?? Drug(id: detection.drugId, name: detection.name)
            appState.currentDrug = drug
            if patientId != nil {
                loadingDrugId = drug.id
                patientScanDrug = drug
            } else {
                loadingDrugId = nil
            }
            Task { await loadPersonalizedContent(for: drug, logTouch: false) }
        }
        .onChange(of: appState.sessionToken) { _, token in
            guard token != nil else { return }
            let drug = appState.currentDrug ?? patientScanDrug
            guard let drug else { return }
            if summary?.drugId == drug.id { return }
            failedSummaryDrugId = nil
            lastSummaryFailureAt.removeValue(forKey: drug.id)
            Task { await loadPersonalizedContent(for: drug, logTouch: false) }
        }
        .onChange(of: appState.selectedHCP?.specialty) { _, _ in
            guard let drug = appState.currentDrug else { return }
            summaryRequestID = UUID()
            failedSummaryDrugId = nil
            checkError = nil
            summary = nil
            loadingDrugId = drug.id
            Task { await loadPersonalizedContent(for: drug, logTouch: false) }
        }
        .onChange(of: arManager.isStale) { _, stale in
            if stale {
                withAnimation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true)) {
                    flashOpacity = 0.5
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

    private func displaySummary(for detection: DetectionResult, phase: ScanSummaryPhase) -> DrugSummary {
        let drugId = resolver.cachedDrug(forRawPayload: detection.rawPayload)?.id ?? detection.drugId
        if let summary, summary.drugId == drugId {
            return summary
        }
        guard phase == .offline else {
            return DrugSummary(drugId: drugId, name: detection.name, tier: "new", headline: "", bullets: [])
        }
        return DrugSummary(
            drugId: drugId,
            name: detection.name,
            tier: "new",
            headline: "Live summary unavailable",
            bullets: [],
            summarySource: "unavailable"
        )
    }

    private func patientSummary(for drug: Drug) -> DrugSummary {
        let base: DrugSummary
        if let summary, summary.drugId == drug.id {
            base = summary
        } else {
            base = DrugSummary(drugId: drug.id, name: drug.name, tier: "new", headline: "", bullets: [])
        }
        guard let patient = appState.scanSessionPatient else { return base }
        let extra = DemoDrugCatalog.drug(id: drug.id)?.answers.values.joined(separator: " ") ?? ""
        return base.applyingChartCheck(for: patient, extraText: extra)
    }

    private func adopt(_ drug: Drug) {
        if appState.scanSessionPatient != nil { patientScanDrug = drug }
        if appState.currentDrug?.id != drug.id {
            appState.currentDrug = drug
            summary = nil
            failedSummaryDrugId = nil
        }
        let needsPatientCheck = appState.scanSessionPatient.map {
            summary?.chartCheck(for: $0.id) == nil
        } ?? false
        // A summary request already owns this sighting. Coming back before it
        // finishes must not start a second touch.
        if loadingDrugId == drug.id {
            if let hcpId = appState.selectedHCP?.id {
                engagementQueue.keepCurrentSighting(hcpId: hcpId, drugId: drug.id)
            }
            return
        }
        if failedSummaryDrugId == drug.id,
           let last = lastSummaryFailureAt[drug.id],
           Date().timeIntervalSince(last) < 2 {
            return
        }
        let logTouch = appState.selectedHCP.map {
            engagementQueue.startsNewScan(hcpId: $0.id, drugId: drug.id)
        } ?? false
        if summary?.drugId == drug.id && !needsPatientCheck && !logTouch { return }
        if logTouch, summary?.drugId == drug.id {
            summary = nil
            failedSummaryDrugId = nil
            engagementError = nil
        }
        loadingDrugId = drug.id
        Task { await loadPersonalizedContent(for: drug, logTouch: logTouch) }
    }

    /// The read-then-write half of the personalization loop: fetch the tier's
    /// content for this HCP, then log the touch so the next scan is one tier
    /// further along. Logging second is what makes scan 1 "new" and scan 2
    /// "returning" rather than both showing the post-scan tier.
    private var scanPatientChip: some View {
        Group {
            if let patient = appState.scanSessionPatient {
                HStack(spacing: 8) {
                    Image(systemName: "person.crop.circle")
                    Text(patient.displayName)
                        .font(.caption.weight(.semibold))
                    Button {
                        appState.endScanSession()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.caption2.weight(.bold))
                    }
                    .accessibilityLabel("Clear scan patient")
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(.ultraThinMaterial, in: Capsule())
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 16)
    }

    private func loadPersonalizedContent(for drug: Drug, logTouch: Bool) async {
        APIClient.shared.sessionToken = appState.sessionToken
        guard let hcpId = appState.selectedHCP?.id else {
            failedSummaryDrugId = drug.id
            lastSummaryFailureAt[drug.id] = Date()
            loadingDrugId = nil
            return
        }
        failedSummaryDrugId = nil
        let patientId = appState.scanSessionPatient?.id
        let requestID = UUID()
        summaryRequestID = requestID
        if logTouch { pendingTouchDrugId = drug.id }
        loadingDrugId = drug.id
        checkError = nil
        engagementError = nil
        defer {
            if summaryRequestID == requestID { loadingDrugId = nil }
        }

        func apply(_ fetched: DrugSummary) -> Bool {
            let stillThisDrug = fetched.drugId == drug.id
                || appState.currentDrug?.id == fetched.drugId
                || patientScanDrug?.id == fetched.drugId
            guard summaryRequestID == requestID,
                  appState.selectedHCP?.id == hcpId,
                  appState.scanSessionPatient?.id == patientId,
                  stillThisDrug else { return false }
            if let patient = appState.scanSessionPatient {
                let extra = DemoDrugCatalog.drug(id: fetched.drugId)?.answers.values.joined(separator: " ") ?? ""
                summary = fetched.applyingChartCheck(for: patient, extraText: extra)
            } else {
                summary = fetched
            }
            appState.familiarityTier = fetched.tier
            lastSummaryFailureAt.removeValue(forKey: drug.id)
            return true
        }

        do {
            await engagementQueue.wait(hcpId: hcpId, drugId: drug.id)
            guard summaryRequestID == requestID else { return }
            let fetched: DrugSummary
            do {
                fetched = try await APIClient.shared.getSummary(
                    drugId: drug.id, hcpId: hcpId, patientId: patientId
                )
            } catch let error as APIError where error.requiresReauthentication {
                guard let token = appState.sessionToken, !token.isEmpty,
                      summaryRequestID == requestID else { throw error }
                APIClient.shared.sessionToken = token
                fetched = try await APIClient.shared.getSummary(
                    drugId: drug.id, hcpId: hcpId, patientId: patientId
                )
            }
            if !apply(fetched) { return }
            if pendingTouchDrugId == drug.id {
                pendingTouchDrugId = nil
                do {
                    _ = try await engagementQueue.record(hcpId: hcpId, drugId: drug.id) {
                        try await APIClient.shared.logEngagement(
                            hcpId: hcpId, drugId: drug.id, patientId: patientId
                        )
                    }
                } catch {
                    // Keep the successful reference response. A failed or
                    // ambiguous write must not be retried as a second touch.
                    if summaryRequestID == requestID {
                        engagementError = "Couldn't confirm this scan was saved. Familiarity may not advance."
                    }
                    return
                }
                if summaryRequestID == requestID,
                   appState.scanSessionPatient?.id == patientId {
                    appState.finishScanSelection()
                }
            }
        } catch {
            guard summaryRequestID == requestID else { return }
            if let patient = appState.scanSessionPatient {
                summary = patientSummary(for: drug)
                checkError = nil
            } else if summary?.drugId != drug.id {
                failedSummaryDrugId = drug.id
                lastSummaryFailureAt[drug.id] = Date()
            }
        }
    }
}

#Preview {
    CameraView()
        .environmentObject(AppState())
}

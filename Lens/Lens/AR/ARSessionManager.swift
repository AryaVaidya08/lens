//
//  ARKit session lifecycle + detection-to-HUD plumbing.
//
//  Owns the ARSession and runs the detection pipeline per frame:
//    1. ObjectDetector finds "is there something here" and where (no
//       model, no training — see its own doc comment).
//    2. BarcodeScanner tries to read a barcode restricted to that region.
//    3. TextRecognizer (OCR) is the fallback if no barcode decodes.
//  Whichever succeeds publishes state that CameraView renders a bounding
//  box + HUD bubble from.
//
//  Design note: ARKit is used here purely for a stable camera passthrough
//  (consistent with the app's "AR" framing) — the HUD bubble itself is
//  positioned in 2D screen space at the detected object's on-screen
//  location rather than as a true 3D-anchored SceneKit node. Flat product
//  packaging rarely has enough surface texture for reliable ARKit
//  plane/feature-point hit-testing, so 2D screen tracking is the more
//  demo-reliable choice. True world anchoring (raycast + ARAnchor) is a
//  reasonable stretch goal once detection is solid — see the TODO on
//  `placeAnchor` below.
//
//  Owned by: AR & detection lane.
//

import ARKit
import Combine
import SceneKit
import Foundation
import UIKit
import SwiftUI

/// A detected drug ready to display: its resolved identity plus where the
/// object was seen on screen, so the HUD bubble can appear near it.
struct DetectionResult: Identifiable, Equatable {
    let id = UUID()
    let drugId: String
    let name: String
    /// The raw identifier that resolved this detection, before any
    /// backend lookup — tagged with how it was read ("barcode: ..." or
    /// "text: ...") and surfaced in the HUD for testing, so it's visible
    /// which path actually worked.
    let rawPayload: String
    /// Normalized (0...1, top-left origin) location of the detected
    /// object at the moment of detection, used to position the HUD
    /// bubble and the debug bounding box.
    let screenAnchor: CGRect
}

extension UIInterfaceOrientation {
    /// Maps the current interface orientation to the `CGImagePropertyOrientation`
    /// Vision needs to interpret a back-camera `ARFrame.capturedImage` buffer
    /// correctly. `capturedImage` is always delivered in the sensor's native
    /// landscape orientation regardless of how the device is actually held —
    /// without this mapping, bounding boxes drift out of sync with what's on
    /// screen as soon as the phone is rotated.
    var cgImageOrientation: CGImagePropertyOrientation {
        switch self {
        case .landscapeRight: return .up
        case .landscapeLeft: return .down
        case .portraitUpsideDown: return .left
        default: return .right // .portrait and anything unrecognized
        }
    }
}

final class ARSessionManager: NSObject, ObservableObject, ARSessionDelegate {
    let session = ARSession()
    private let objectDetector = ObjectDetector()
    private let barcodeScanner = BarcodeScanner()
    private let textRecognizer = TextRecognizer()

    /// Turns a decoded identifier (a barcode payload or OCR text) into a
    /// drug identity. CameraView sets this. `kind` is `"barcode"` or
    /// `"text"`, so the real implementation knows which field of the
    /// backend's /detect request to populate.
    ///
    /// TODO: implement — CameraView should replace the default fake
    /// resolver with a real call into
    /// `APIClient.shared.detectDrug(barcode:ocrText:)` once Backend &
    /// data's `/detect` route is live — pass `value` as `barcode` when
    /// `kind == "barcode"`, or as `ocrText` when `kind == "text"`.
    var resolvePayload: (_ kind: String, _ value: String) -> (drugId: String, name: String) = { _, _ in
        (drugId: "fake-drug-1", name: "Sample Drug")
    }

    /// The most recent detected object's bounding box — shown as soon as
    /// `ObjectDetector` finds *something* in frame, regardless of whether
    /// a barcode or text off of it has been read successfully yet. This is
    /// what draws the bounding box the moment a bottle-shaped object comes
    /// into view.
    @Published var objectBoundingBox: CGRect?

    /// The currently displayed, fully resolved detection (identity +
    /// summary-ready info). `screenAnchor` updates on every frame the
    /// object is seen (so the HUD glides smoothly to follow it);
    /// `drugId`/`name` only change once a different barcode/text is read.
    /// Goes back to `nil` — with an animated fade, since CameraView
    /// applies `withAnimation` around every write — after `staleTimeout`
    /// seconds with no object in view at all.
    @Published var activeDetection: DetectionResult?

    /// True from the moment a frame fails to find the object at all until
    /// either it's seen again (back to `false`) or `staleTimeout` elapses
    /// and `activeDetection`/`objectBoundingBox` are cleared. CameraView
    /// uses this window to flash the bubble as a "still holding on, about
    /// to let go" cue.
    @Published var isStale = false

    /// Updated by CameraView whenever the device rotates, so detection
    /// stays aligned with what's on screen at any orientation.
    var currentInterfaceOrientation: UIInterfaceOrientation = .portrait

    private var lastSeenAt: Date?
    private let staleTimeout: TimeInterval = 1.5
    private var staleCheckTimer: Timer?

    private var frameCounter = 0
    /// Only run Vision every Nth frame — this pipeline runs three Vision
    /// requests per attempt (object, barcode, OCR), and ARKit delivers
    /// frames at up to 60fps.
    private let detectionInterval = 5

    /// Vision runs here, off ARKit's delivery thread — running it
    /// synchronously inside `session(_:didUpdate:)` blocks that thread
    /// long enough that ARKit logs "the delegate is retaining ARFrames"
    /// and eventually stops delivering frames. `isScanning` drops frames
    /// that arrive while a scan is still in flight instead of queueing
    /// them up, so this queue never backs up either.
    private let visionQueue = DispatchQueue(label: "hcpcopilot.vision-scan", qos: .userInitiated)
    private var isScanning = false

    private var isRunning = false
    private var generation = UUID()

    func start() {
        guard !isRunning, ARWorldTrackingConfiguration.isSupported else { return }
        isRunning = true
        generation = UUID()
        let configuration = ARWorldTrackingConfiguration()
        // The assistant owns microphone capture; scanning only needs video.
        configuration.providesAudioData = false
        // Lifecycle, scan gating, and published results share the main queue.
        // Only the expensive Vision requests execute on visionQueue.
        session.delegateQueue = .main
        session.delegate = self
        session.run(configuration)

        staleCheckTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            self?.clearIfStale()
        }
    }

    func stop() {
        guard isRunning else { return }
        isRunning = false
        // Vision may still be processing a frame from before this pause.
        generation = UUID()
        session.pause()
        staleCheckTimer?.invalidate()
        staleCheckTimer = nil
        lastSeenAt = nil
        objectBoundingBox = nil
        activeDetection = nil
        isStale = false
    }

    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        guard isRunning else { return }
        frameCounter += 1
        guard frameCounter % detectionInterval == 0 else { return }
        guard !isScanning else { return }
        isScanning = true

        // Grab just the pixel buffer (a cheap, refcounted handle) and the
        // orientation now, synchronously — never hold on to `frame`
        // itself past this callback.
        let scanGeneration = generation
        let pixelBuffer = frame.capturedImage
        let orientation = currentInterfaceOrientation.cgImageOrientation

        visionQueue.async { [weak self] in
            guard let self else { return }

            guard let objectBox = self.objectDetector.detectObject(pixelBuffer: pixelBuffer, orientation: orientation) else {
                DispatchQueue.main.async {
                    self.isScanning = false
                    guard self.isRunning, self.generation == scanGeneration else { return }
                    self.objectBoundingBox = nil
                    self.markMissedIfNeeded()
                }
                return
            }

            var identifier: (kind: String, value: String)?
            if let barcode = self.barcodeScanner.scan(pixelBuffer: pixelBuffer, orientation: orientation, regionOfInterest: objectBox) {
                identifier = ("barcode", barcode.payload)
            } else if let text = self.textRecognizer.scan(pixelBuffer: pixelBuffer, orientation: orientation, regionOfInterest: objectBox) {
                identifier = ("text", text)
            }

            DispatchQueue.main.async {
                self.isScanning = false
                guard self.isRunning, self.generation == scanGeneration else { return }
                self.handleObjectSeen(objectBox: objectBox, identifier: identifier)
            }
        }
    }

    /// The object detector found something this frame — always records
    /// that (for the bounding box) and clears the stale flag, since
    /// there's clearly still something in view even if this particular
    /// frame's barcode/OCR attempt came up empty.
    private func handleObjectSeen(objectBox: CGRect, identifier: (kind: String, value: String)?) {
        objectBoundingBox = objectBox
        lastSeenAt = Date()
        isStale = false

        guard let identifier else { return } // object visible, nothing legible off it yet

        let identity = resolvePayload(identifier.kind, identifier.value)
        let result = DetectionResult(
            drugId: identity.drugId,
            name: identity.name,
            rawPayload: "\(identifier.kind): \(identifier.value)",
            screenAnchor: objectBox
        )

        withAnimation(.easeOut(duration: 0.25)) {
            activeDetection = result
        }
    }

    /// A scan attempt this frame found no object at all — start the
    /// "about to go stale" flash immediately, well before the full
    /// `staleTimeout` clears everything, but only if there's something on
    /// screen to flash.
    private func markMissedIfNeeded() {
        guard activeDetection != nil else { return }
        isStale = true
    }

    private func clearIfStale() {
        guard let lastSeenAt, Date().timeIntervalSince(lastSeenAt) > staleTimeout else { return }
        self.lastSeenAt = nil
        isStale = false
        objectBoundingBox = nil
        withAnimation(.easeOut(duration: 0.6)) {
            activeDetection = nil
        }
    }

    /// Records a fully resolved detection so the HUD can render it.
    ///
    /// TODO: implement true 3D anchor placement here as a stretch goal —
    /// raycast from `result.screenAnchor`'s center via
    /// `session.raycastQuery(from:allowing:alignment:)`, add an
    /// `ARAnchor` at the hit position, and attach a SceneKit node hosting
    /// the HUD instead of the current 2D screen-space overlay in
    /// CameraView.
    func placeAnchor(for result: DetectionResult) {
        activeDetection = result
    }
}

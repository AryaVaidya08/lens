# Lane context: AR & detection

Read `CLAUDE.md` at the repo root first — this doc only covers what's specific to your lane. This doc has been refreshed against the current codebase (unlike some of the other lane docs, which may still describe the original scaffold — cross-check anything that looks stale).

## What you own

The physical act of pointing the phone at a drug and seeing something appear in space, plus the scan flow for medication-list reconciliation.

- `Lens/Lens/Detection/ObjectDetector.swift` — Stage 1: runs the trained Core ML model (`BottleDetection.mlmodel` / `PillBottleDetectorv1`, see `PillBottleDetector.mlproj/` and `training/`) via `VNCoreMLRequest` to find the bottle and its bounding box, before any barcode/OCR read is attempted.
- `Lens/Lens/Detection/BarcodeScanner.swift` — Vision `VNDetectBarcodesRequest`, restricted to the region `ObjectDetector` found. First-choice identification path.
- `Lens/Lens/Detection/TextRecognizer.swift` — Vision `VNRecognizeTextRequest` OCR, the fallback when no barcode decodes.
- `Lens/Lens/Detection/MedicationDocumentScanner.swift`, `MedicationLabelOCR.swift` — `VNDocumentCameraViewController`-based scanning for medication reviews (scanning a reference med list and/or confirmed bottles, feeding `MedicationReviewsView`).
- `Lens/Lens/AR/ARSessionManager.swift` — ARKit session lifecycle, runs the three-stage detection pipeline above per frame, publishes state for the HUD, and handles `sessionWasInterrupted`/`sessionInterruptionEnded`/`didFailWithError` recovery. Read its header comment: the HUD bubble is deliberately 2D screen-tracked, not a true 3D-anchored SceneKit node — flat packaging doesn't give ARKit enough texture for reliable plane/feature-point tracking.
- `Lens/Lens/AR/CameraSessionLifecycle.swift` — small state machine gating camera start/stop on layout-ready + visible + active, so the session doesn't start before first layout or keep running when another tab is open.
- `Lens/Lens/AR/HUDOverlayView.swift` — the info card that follows the detected object.
- `Lens/Lens/Views/CameraView.swift` — hosts the camera feed + AR overlay, wires detection → backend call → HUD.
- `Lens/Lens/Views/PersonaPickerView.swift` — despite the leftover scaffold name, this is now the **real sign-in screen** (email/password, "Create an account", "Forgot password"), not a demo persona picker.
- `Lens/Lens/Views/HUDView.swift` — non-AR fallback (useful on the simulator, where ARKit doesn't run).
- `Lens/Lens/App/HCPCopilotApp.swift` — app entry point / root navigation (shell only, don't need to touch often).

## What you depend on (don't break, coordinate before changing)

- `Lens/Lens/Networking/APIClient.swift` / `Endpoints.swift` — call `detectDrug`, `getSummary`, `logEngagement`, `medicationReviews`/`saveMedicationReview` from here. Owned jointly with Backend & data; if a response shape changes, your calls need to match.
- `Lens/Lens/Models/Drug.swift`, `DrugSummary.swift`, `MedicationReview.swift` — what the backend returns; `HUDOverlayView`/`HUDView`/`MedicationReviewsView` render these.
- `backend/app/routes/detect.py` (Backend & data lane) — you send it a barcode string or OCR text; it returns `{drug_id, name}` via `app/detection/catalog.py`'s fuzzy match.
- `backend/app/routes/medication_reviews.py` (Backend & data lane) — the comparison logic your scanned entries feed into.

## Current state

All of the above is implemented, not stub code. What's still worth attention:

- The Core ML detector (`PillBottleDetectorv1`) is trained on the specific demo bottles in `training/` — if the actual demo drugs change, retrain it (`training/README.md`) rather than relying on barcode/OCR alone for new packaging.
- `ARSessionManager`'s interruption/failure recovery (`sessionWasInterrupted`, `sessionInterruptionEnded`, `didFailWithError`) was added after real demo runs hit ARKit tracking loss — if you touch this file, re-test by backgrounding the app mid-scan and by covering the camera, not just the happy path.
- `MedicationDocumentScanner`/`MedicationLabelOCR` accuracy on a real printed med list is the main remaining reliability risk in this lane, the same way barcode/OCR accuracy was for the original scan flow.

## Pitfalls specific to this lane

- **Simulator has no camera and no ARKit.** You need a physical device to test any of this. `HUDView` (non-AR) remains the simulator-testable fallback.
- **Camera/mic permissions:** this Xcode project uses `GENERATE_INFOPLIST_FILE = YES` (no checked-in `Info.plist`), so privacy strings (`NSCameraUsageDescription`, `NSMicrophoneUsageDescription`, `NSSpeechRecognitionUsageDescription`) are `INFOPLIST_KEY_*` build settings in Xcode's target "Info" tab, not a plist file. A missing usage-description string crashes the app on first permission prompt instead of showing a dialog.
- **Vision requests should run off the main thread** — don't block the ARKit render loop running detection on every frame; the pipeline already throttles this, so if you're adding new per-frame work, follow the same pattern rather than running on every frame.
- Detection quality on real pharma packaging is still unpredictable — a manual override (pick a drug from a list) remains the demo safety net if live detection flakes.

## Definition of done for the hackathon

Point the phone at a real (or printed mock) drug package, see a HUD appear with that drug's personalized summary within a couple seconds, reliably enough to demo live twice in a row, survive an ARSession interruption without crashing, and complete a medication-review scan against a printed reference list.

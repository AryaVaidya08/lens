# Lane context: AR & detection

Read `CLAUDE.md` at the repo root first — this doc only covers what's specific to your lane.

## What you own

The physical act of pointing the phone at a drug and seeing something appear in space.

- `Lens/Lens/Detection/BarcodeScanner.swift` — Vision `VNDetectBarcodesRequest` wrapper
- `Lens/Lens/Detection/TextRecognizer.swift` — Vision `VNRecognizeTextRequest` OCR fallback
- `Lens/Lens/AR/ARSessionManager.swift` — ARKit session, anchor placement
- `Lens/Lens/AR/HUDOverlayView.swift` — the AR-anchored info card
- `Lens/Lens/Views/CameraView.swift` — hosts the camera feed + AR overlay, wires detection → backend call → HUD
- `Lens/Lens/Views/PersonaPickerView.swift` — the demo "login" screen
- `Lens/Lens/Views/HUDView.swift` — non-AR fallback (useful on the simulator, where ARKit doesn't run)
- `Lens/Lens/App/HCPCopilotApp.swift` — app entry point (shell only, don't need to touch often)

## What you depend on (don't break, coordinate before changing)

- `Lens/Lens/Networking/APIClient.swift` / `Endpoints.swift` — call `detectDrug`, `getSummary`, `logEngagement` from here. These are owned jointly; if the backend lane changes a response shape, your calls need to match.
- `Lens/Lens/Models/Drug.swift`, `DrugSummary.swift` — what `getSummary` returns; `HUDOverlayView`/`HUDView` render these.
- `backend/app/routes/detect.py` (Backend & data lane) — you send it a barcode string or OCR text; it returns `{drug_id, name}`.

## Suggested build order

1. Get `CameraView` showing a live camera feed at all (no detection yet) — proves the AR/camera plumbing works before adding Vision.
2. Wire `BarcodeScanner` against sample frames; log detected payloads to console.
3. Call `APIClient.detectDrug` with a detected barcode, confirm you get a `Drug` back from a running backend (coordinate with Backend & data lane — they should have `/detect` stubbed to return something fixed early).
4. Add `ARSessionManager.placeAnchor` + `HUDOverlayView` once detection is reliable enough to anchor against.
5. `TextRecognizer` OCR fallback last — it's the backup path, not the primary demo path.

## Pitfalls specific to this lane

- **Simulator has no camera and no ARKit.** You need a physical device to test any of this. Build `HUDView` (non-AR) early as your simulator-testable fallback.
- **Camera/mic permissions:** this Xcode project uses `GENERATE_INFOPLIST_FILE = YES` (no checked-in `Info.plist`), so privacy strings (`NSCameraUsageDescription`, `NSMicrophoneUsageDescription`, `NSSpeechRecognitionUsageDescription`) need to be added as `INFOPLIST_KEY_*` build settings in Xcode's target "Info" tab, not in a plist file. Do this early — a missing usage-description string crashes the app on first permission prompt instead of showing a dialog.
- **Vision requests are synchronous-feeling but should run off the main thread** — don't block the ARKit render loop running detection on every frame; throttle (e.g. every N frames) or run detection only when the user taps.
- Detection quality on real pharma packaging is unpredictable — have a manual override (tap a drug from a list) as a demo safety net if live detection flakes during the pitch.

## Definition of done for the hackathon

Point the phone at a real (or printed mock) drug package, see a HUD appear with that drug's personalized summary within a couple seconds, reliably enough to demo live twice in a row.

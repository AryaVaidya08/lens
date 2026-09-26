# Training your own pill/bottle recognition model

Right now, `ObjectDetector` (`Lens/Lens/Detection/ObjectDetector.swift`) finds "something's in frame" using Vision's built-in objectness saliency request — zero setup, but it has no idea *what* it's looking at. Identity currently comes from whatever `BarcodeScanner`/`TextRecognizer` can read off that region.

Once you've settled on the actual drug samples you're using for the demo, you can do much better: train a small image classifier on photos of *your specific bottles*, so the app recognizes "this is the Ibuprofen bottle" directly — no legible barcode or readable label text required. This matters because demo bottles get held at angles, under bad lighting, with reflective packaging — OCR/barcode reliability degrades fast, but a classifier trained on your exact bottles from many angles is much more robust.

This doc covers two paths:
1. **Create ML** (recommended) — no Python, no GPU setup, built into Xcode, works well for "classify a handful of known objects" with a few dozen photos per class. Do this first.
2. **YOLOv8 + Core ML export** (stretch goal) — real per-class bounding-box detection instead of classify-a-crop, if there's time and you want to drop the generic objectness detector entirely.

---

## Path 1: Create ML image classifier (do this)

### 1. Collect photos, one folder per drug

Inside `training/data/`, create one folder per drug, named to match the `drug_id` you're using in `backend/app/db/seed.py` — keeping these in sync means the classifier's output label can be used directly as a `drug_id` with no separate mapping table to maintain.

```
training/data/
  ibuprofen-200mg/
  amoxicillin-500mg/
  lisinopril-10mg/
  background/          <- see note below, not a drug
```

For each drug folder: **30-50+ photos minimum**, more if you have time. Create ML uses transfer learning (a pretrained feature extractor under the hood), so it needs far fewer photos than training from scratch — but variety matters more than volume:

- Multiple angles (front label, tilted, held at an angle like someone actually holding it up to a phone)
- Multiple distances (close-up filling the frame, and farther away like a real scan)
- Multiple lighting conditions — critically, include lighting similar to wherever you'll actually demo (venue lighting, not just your dorm room)
- Different hands/backgrounds if multiple teammates are collecting photos — a model trained on one person's desk/hand will overfit to that background
- A few photos with the bottle partially occluded (fingers covering part of the label) since that's realistic for a held object

**Add a `background` folder** with photos of *not-drugs* — hands, tables, other random objects, empty rooms. Without this, the model will always confidently guess one of your drug classes even when shown nothing relevant, since it's never seen a "none of the above" example. This is the single most common mistake with small demo classifiers — don't skip it.

Fastest way to collect photos: use the iPhone(s) you're demoing with, `AirDrop`/`Files` them to a Mac, and sort into these folders. A shared folder (iCloud Drive/Google Drive) that multiple teammates drop photos into works well under time pressure.

### 2. Train in Create ML

Create ML ships with Xcode — open it via **Xcode → Open Developer Tool → Create ML**, or run `xcrun createml` from Terminal.

1. **File → New Project → Image Classification.**
2. Drag the `training/data/` folder (with your per-class subfolders) into the **Training Data** well. Create ML uses the folder names as the class labels automatically.
3. Leave **Validation Data** on "Auto" (it holds out a slice of your training data automatically) unless you've collected a separate, deliberately different-looking test set — better practice, but auto-split is fine under time pressure.
4. Hit **Train**. On an M-series Mac this typically takes a few minutes, not hours — it's fine-tuning a small head on top of a frozen pretrained backbone, not training a network from scratch.
5. Check the **Evaluation** tab: per-class precision/recall, and a confusion matrix showing which drugs get mixed up with which. If two drugs are confused often, they usually look similar from certain angles — go add more varied photos for those two specific classes and retrain (retraining is fast, iterate freely).
6. Use the **Preview** tab to live-test with your Mac's camera before writing any app code — hold a bottle up to your laptop's webcam and watch the live confidence scores. This is the fastest way to sanity-check the model actually works before integrating it.

### 3. Export and add to the Xcode project

1. In the **Output** tab, click **Get** to export a `.mlmodel` file (or `.mlpackage`, Create ML's newer default format — either works).
2. Drag that file into `Lens/Lens/` in Xcode (or straight into the `Lens/Lens/` folder on disk — remember this project uses Xcode 16's file-system-synchronized groups, so it's picked up automatically).
3. Xcode auto-generates a Swift class matching the model's name (e.g. a model named `PillClassifier.mlmodel` gets you a generated `PillClassifier` Swift class with a ready-made `prediction(...)` API) — you don't write any Core ML boilerplate by hand.

### 4. Wire it into the detection pipeline

Add a new file, `Lens/Lens/Detection/PillClassifier.swift`, shaped like `BarcodeScanner`/`TextRecognizer` so it slots into the same pipeline:

```swift
import Vision
import CoreVideo
import CoreGraphics

final class PillClassifier {
    private let request: VNCoreMLRequest

    init() {
        // Replace `PillClassifier` with your generated model class's name.
        let model = try! VNCoreMLModel(for: PillClassifier(configuration: MLModelConfiguration()).model)
        request = VNCoreMLRequest(model: model)
    }

    /// Returns the predicted drug label and confidence, restricted to the
    /// region ObjectDetector found — same regionOfInterest convention as
    /// BarcodeScanner/TextRecognizer (top-left origin).
    func classify(
        pixelBuffer: CVPixelBuffer,
        orientation: CGImagePropertyOrientation = .right,
        regionOfInterest: CGRect
    ) -> (label: String, confidence: Float)? {
        request.regionOfInterest = regionOfInterest.flippedVerticalOrigin

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: orientation, options: [:])
        do {
            try handler.perform([request])
        } catch {
            return nil
        }

        guard let top = (request.results as? [VNClassificationObservation])?.first else {
            return nil
        }

        // Reject low-confidence guesses and anything classified as your
        // "background" (not-a-drug) class.
        guard top.confidence > 0.7, top.identifier != "background" else {
            return nil
        }

        return (label: top.identifier, confidence: top.confidence)
    }
}
```

Then in `ARSessionManager.swift`, add it as a third resolution path alongside barcode/OCR (inside the `visionQueue.async` block, after the existing barcode/text attempts):

```swift
if let barcode = self.barcodeScanner.scan(pixelBuffer: pixelBuffer, orientation: orientation, regionOfInterest: objectBox) {
    identifier = ("barcode", barcode.payload)
} else if let text = self.textRecognizer.scan(pixelBuffer: pixelBuffer, orientation: orientation, regionOfInterest: objectBox) {
    identifier = ("text", text)
} else if let pill = self.pillClassifier.classify(pixelBuffer: pixelBuffer, orientation: orientation, regionOfInterest: objectBox) {
    identifier = ("class", pill.label)
}
```

Since class labels are the folder names from step 1 (which you kept matching `drug_id`), `resolvePayload`'s real implementation can treat `kind == "class"` as an already-resolved `drug_id` — no barcode/OCR lookup needed, straight to `/drug/{id}/summary`. This is worth trying *first* in the `if`/`else if` chain once the model is trained and evaluated well, since it's the most robust of the three signals for a held, at-an-angle demo object — barcode/OCR can stay as fallbacks for drugs you haven't gotten around to training yet.

---

## Path 2: YOLOv8 + Core ML (stretch goal)

Only worth doing if Path 1's accuracy isn't good enough and you have real time left. This gives you a real trained object detector (bounding box + class in one shot) instead of classifying a crop found by the generic objectness detector — meaning you could drop `ObjectDetector.swift` entirely and get both "where" and "what" from one model.

Rough sequence (needs Python, not just Xcode):

```bash
pip install ultralytics coremltools

# Label your photos with bounding boxes first — Roboflow
# (roboflow.com) has a free tier with a fast web-based labeling UI and
# exports directly in YOLO format, which is far less painful than
# hand-writing annotation files.

# Fine-tune a pretrained nano model (fast, small, good for on-device):
yolo detect train model=yolov8n.pt data=your_dataset.yaml epochs=100 imgsz=640

# Export to Core ML:
yolo export model=runs/detect/train/weights/best.pt format=coreml
```

That produces a `.mlpackage` you drag into Xcode the same way as the Create ML export, and run via `VNCoreMLRequest` the same way — but its output is a full set of bounding boxes with class labels per detection, so it replaces both `ObjectDetector` and the classification step in one request.

This path needs real setup time (labeling, a training environment, testing the export) — don't start it unless Path 1 is trained, evaluated, and integrated first, and there's still runway left before the demo.

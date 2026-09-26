//
//  Pill bottle detector.
//
//  Stage 1 of the detection pipeline: before trying to read a barcode or
//  OCR text off anything, we need to know where to look. This runs
//  PillBottleDetectorv1 (a Create ML object detector trained on our demo
//  bottles, see training/README.md) via VNCoreMLRequest, which gives a
//  real "bottle" bounding box instead of Vision's generic objectness
//  saliency guess. If multiple bottles are in frame, only the largest
//  bounding box is surfaced — the app only ever displays one detection at
//  a time. BarcodeScanner/TextRecognizer are run next, restricted to the
//  region this returns.
//
//  Owned by: AR & detection lane.
//

import Vision
import CoreML
import CoreVideo
import CoreGraphics

extension CGRect {
    /// Flips a normalized (0...1) rect between Vision's bottom-left-origin
    /// convention and the top-left-origin convention used everywhere else
    /// in this app (SwiftUI, UIKit). This flip is its own inverse — the
    /// same property converts in either direction — so both BarcodeScanner
    /// (converting a `boundingBox` result out of Vision) and callers
    /// building a `regionOfInterest` to feed back into Vision use it.
    var flippedVerticalOrigin: CGRect {
        CGRect(x: minX, y: 1 - minY - height, width: width, height: height)
    }
}

final class ObjectDetector {
    private let request: VNCoreMLRequest

    init() {
        guard let model = try? VNCoreMLModel(for: PillBottleDetectorv1(configuration: MLModelConfiguration()).model) else {
            fatalError("Failed to load PillBottleDetectorv1.mlmodel")
        }
        let request = VNCoreMLRequest(model: model)
        // The model's bounding-box coordinates are relative to the full
        // input image — scaleFill maps the whole camera frame into the
        // model's square input (distorting aspect ratio slightly) so
        // those coordinates stay aligned with the original frame, instead
        // of centerCrop silently cropping bottle out of a wide frame.
        request.imageCropAndScaleOption = .scaleFill
        self.request = request
    }

    /// Returns the bounding box of the largest detected pill bottle in the
    /// frame, normalized to a 0...1 unit square with the origin at
    /// top-left, or `nil` if none was detected above the model's
    /// confidence threshold.
    func detectObject(pixelBuffer: CVPixelBuffer, orientation: CGImagePropertyOrientation = .right) -> CGRect? {
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: orientation, options: [:])

        do {
            try handler.perform([request])
        } catch {
            return nil
        }

        guard let observations = request.results as? [VNRecognizedObjectObservation], !observations.isEmpty else {
            return nil
        }

        // Only one detection is ever shown at a time — if more than one
        // bottle is in frame, prefer whichever fills more of the screen
        // (almost certainly the one actually being held up to the camera).
        let largest = observations.max { lhs, rhs in
            let lhsArea = lhs.boundingBox.width * lhs.boundingBox.height
            let rhsArea = rhs.boundingBox.width * rhs.boundingBox.height
            return lhsArea < rhsArea
        }

        return largest?.boundingBox.flippedVerticalOrigin
    }
}

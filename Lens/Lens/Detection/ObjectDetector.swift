//
//  Lightweight "is there something here" detector.
//
//  Stage 1 of the detection pipeline: before trying to read a barcode or
//  OCR text off anything, we need to know where to look. Rather than
//  bundling/training a custom object-detection model (real option, but
//  real setup cost — see the note below), this uses Vision's built-in
//  objectness-based saliency request: it ships in the OS, needs no model
//  file, and reliably finds "the most prominent thing in frame," which in
//  a hand-held, point-the-phone-at-one-object framing is almost always
//  the drug bottle/package being held up to the camera. It doesn't know
//  *what* the object is — that's what BarcodeScanner/TextRecognizer are
//  for, run next, restricted to the region this returns.
//
//  Upgrade path, if there's time: a real trained detector (e.g. YOLOv8n
//  exported to Core ML, run via VNCoreMLRequest) trained on COCO or Open
//  Images V7 would give an actual "bottle" class label instead of a
//  generic "something's here" region, at the cost of bundling and testing
//  a multi-MB model file. Not worth the risk to add blind right now.
//
//  Owned by: AR & detection lane.
//

import Vision
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
    /// Returns the bounding box of the most prominent object in the frame,
    /// normalized to a 0...1 unit square with the origin at top-left, or
    /// `nil` if nothing stands out.
    func detectObject(pixelBuffer: CVPixelBuffer, orientation: CGImagePropertyOrientation = .right) -> CGRect? {
        let request = VNGenerateObjectnessBasedSaliencyImageRequest()
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: orientation, options: [:])

        do {
            try handler.perform([request])
        } catch {
            return nil
        }

        guard let observation = request.results?.first,
              let topObject = observation.salientObjects?.max(by: { $0.confidence < $1.confidence }) else {
            return nil
        }

        return topObject.boundingBox.flippedVerticalOrigin
    }
}

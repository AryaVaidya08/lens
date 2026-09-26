//
//  Barcode detection.
//
//  Wraps Vision's VNDetectBarcodesRequest to pull a barcode payload out
//  of a live camera frame. First-choice detection path — TextRecognizer
//  is the OCR fallback when there's no scannable barcode.
//
//  Owned by: AR & detection lane.
//

import Vision
import CoreVideo
import CoreGraphics

/// One scan result: the decoded payload plus where it was found in the
/// frame. `boundingBox` is normalized to a 0...1 unit square with the
/// origin at top-left (UIKit/SwiftUI convention) — Vision itself reports
/// bottom-left, so `scan` flips it here to save every caller from having
/// to remember that.
struct BarcodeDetection: Equatable {
    let payload: String
    let boundingBox: CGRect
}

final class BarcodeScanner {
    /// Scans a single pixel buffer for a barcode and returns its decoded
    /// payload plus normalized bounding box, if any.
    ///
    /// `orientation` should match how the buffer is actually rotated —
    /// ARKit's `ARFrame.capturedImage` comes in landscape sensor
    /// orientation regardless of device orientation, so callers reading
    /// frames from an AR session in portrait should pass `.right`
    /// (the default here).
    ///
    /// `regionOfInterest` restricts the scan to a sub-region of the frame
    /// (top-left origin, same convention as `boundingBox` below) — pass
    /// the object bounding box from `ObjectDetector` so this only reads
    /// barcodes off the object actually in frame, not background clutter.
    func scan(
        pixelBuffer: CVPixelBuffer,
        orientation: CGImagePropertyOrientation = .right,
        regionOfInterest: CGRect? = nil
    ) -> BarcodeDetection? {
        let request = VNDetectBarcodesRequest()
        if let regionOfInterest {
            request.regionOfInterest = regionOfInterest.flippedVerticalOrigin
        }
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: orientation, options: [:])

        do {
            try handler.perform([request])
        } catch {
            return nil
        }

        guard let result = request.results?.first,
              let payload = result.payloadStringValue else {
            return nil
        }

        return BarcodeDetection(payload: payload, boundingBox: result.boundingBox.flippedVerticalOrigin)
    }
}

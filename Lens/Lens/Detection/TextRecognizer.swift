//
//  OCR fallback detection.
//
//  Wraps Vision's VNRecognizeTextRequest for packages without a
//  scannable barcode. Same input/output shape as BarcodeScanner so the
//  pipeline in ARSessionManager can try one then the other without
//  branching logic — both are restricted to the region ObjectDetector
//  found, so this only reads text off the object in frame.
//
//  Owned by: AR & detection lane.
//

import Vision
import CoreVideo
import CoreGraphics

final class TextRecognizer {
    /// Scans a single pixel buffer for recognizable text and returns the
    /// best candidate string, if any — joins every recognized line, since
    /// a drug's name is often split across multiple short lines on the
    /// label rather than sitting on one.
    ///
    /// `orientation` and `regionOfInterest` behave exactly as they do on
    /// `BarcodeScanner.scan`.
    func scan(
        pixelBuffer: CVPixelBuffer,
        orientation: CGImagePropertyOrientation = .right,
        regionOfInterest: CGRect? = nil
    ) -> String? {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        if let regionOfInterest {
            request.regionOfInterest = regionOfInterest.flippedVerticalOrigin
        }

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: orientation, options: [:])
        do {
            try handler.perform([request])
        } catch {
            return nil
        }

        guard let observations = request.results, !observations.isEmpty else {
            return nil
        }

        let lines = observations.compactMap { $0.topCandidates(1).first?.string }
        guard !lines.isEmpty else { return nil }

        return lines.joined(separator: " ")
    }
}

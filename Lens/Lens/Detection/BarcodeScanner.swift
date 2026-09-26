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

final class BarcodeScanner {
    /// Scans a single pixel buffer for a barcode and returns its decoded
    /// payload string, if any.
    ///
    /// TODO: implement — build a VNDetectBarcodesRequest, run it via
    /// VNImageRequestHandler on `pixelBuffer`, and return the first
    /// result's `payloadStringValue`.
    func scan(pixelBuffer: CVPixelBuffer) -> String? {
        // TODO: implement
        return nil
    }
}

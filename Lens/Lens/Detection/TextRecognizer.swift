//
//  OCR fallback detection.
//
//  Wraps Vision's VNRecognizeTextRequest for packages without a
//  scannable barcode. Same input/output shape as BarcodeScanner so
//  CameraView can try one then the other without branching logic.
//
//  Owned by: AR & detection lane.
//

import Vision
import CoreVideo

final class TextRecognizer {
    /// Scans a single pixel buffer for recognizable text and returns
    /// the best candidate string, if any.
    ///
    /// TODO: implement — build a VNRecognizeTextRequest, run it via
    /// VNImageRequestHandler on `pixelBuffer`, and join the top
    /// candidate strings from each observation.
    func scan(pixelBuffer: CVPixelBuffer) -> String? {
        // TODO: implement
        return nil
    }
}

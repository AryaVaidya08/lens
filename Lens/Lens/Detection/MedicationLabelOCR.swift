import Foundation
import Vision

enum MedicationLabelOCR {
    /// Called off the main actor. Preserve lines for confirmation and parsing.
    nonisolated static func recognize(data: Data) throws -> String {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = false
        try VNImageRequestHandler(data: data, options: [:]).perform([request])
        return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
    }
}

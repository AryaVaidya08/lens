import SwiftUI
import VisionKit
import UIKit

/// One source image per medication entry; OCR stays on device.
struct MedicationDocumentScanner: UIViewControllerRepresentable {
    var onResult: (Result<UIImage, Error>) -> Void
    var onCancel: () -> Void

    static var isSupported: Bool { VNDocumentCameraViewController.isSupported }

    func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let controller = VNDocumentCameraViewController()
        controller.delegate = context.coordinator
        return controller
    }
    func updateUIViewController(_ controller: VNDocumentCameraViewController, context: Context) {}
    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    final class Coordinator: NSObject, VNDocumentCameraViewControllerDelegate {
        let parent: MedicationDocumentScanner
        init(parent: MedicationDocumentScanner) { self.parent = parent }
        func documentCameraViewControllerDidCancel(_ controller: VNDocumentCameraViewController) { parent.onCancel() }
        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFailWithError error: Error) { parent.onResult(.failure(error)) }
        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFinishWith scan: VNDocumentCameraScan) {
            guard scan.pageCount == 1 else {
                parent.onResult(.failure(NSError(domain: "MedicationScan", code: 1, userInfo: [NSLocalizedDescriptionKey: "Capture one label per entry. Retake the scan with one page."])))
                return
            }
            parent.onResult(.success(scan.imageOfPage(at: 0)))
        }
    }

    static func recognize(_ image: UIImage) async throws -> String {
        // Encode orientation before moving the work off the main actor.
        guard let data = image.jpegData(compressionQuality: 0.9) else {
            throw NSError(domain: "MedicationScan", code: 2)
        }
        return try await Task.detached(priority: .userInitiated) {
            try MedicationLabelOCR.recognize(data: data)
        }.value
    }
}

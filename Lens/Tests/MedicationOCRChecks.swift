import AppKit
import Foundation

@main
struct MedicationOCRChecks {
    static func main() throws {
        let image = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1000, pixelsHigh: 600,
                                     bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                                     isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: image)
        NSColor.white.setFill()
        NSRect(x: 0, y: 0, width: 1000, height: 600).fill()
        let lines = ["Examplemed 10 mg", "extended-release tablets", "Take one tablet daily"]
        for (index, line) in lines.enumerated() {
            (line as NSString).draw(at: NSPoint(x: 60, y: 440 - index * 100), withAttributes: [
                .font: NSFont.systemFont(ofSize: 42), .foregroundColor: NSColor.black
            ])
        }
        NSGraphicsContext.restoreGraphicsState()
        let text = try MedicationLabelOCR.recognize(data: image.representation(using: .png, properties: [:])!)
        let entry = MedicationLabelSuggestions.entry(from: text)
        precondition(entry.name == "Examplemed", "OCR missed medication name: \(text)")
        precondition(entry.strength == "10 mg", "OCR missed strength: \(text)")
        precondition(entry.formulation == "extended-release tablets")
        precondition(entry.directions == "Take one tablet daily")
        do {
            _ = try MedicationLabelOCR.recognize(data: Data("not an image".utf8))
            preconditionFailure("Invalid image should throw")
        } catch { }
        print("PASS: image → Vision OCR → medication suggestions; invalid images fail explicitly")
    }
}

import Foundation

/// Replace this reply with APIClient.askQuestion once backend integration is ready.
/// Answers come from DemoDrugCatalog and are labeled as demo data.
enum PlaceholderAssistant {
    static func reply(to question: String, drug: Drug?) -> String {
        let heard = question.trimmingCharacters(in: .whitespacesAndNewlines)
        if let drug {
            return "I heard you say: \(heard). I need the live backend so Grok can answer from \(drug.name)'s reference material."
        }
        return "I heard you say: \(heard). This is a demo reply. Point the camera at a drug first."
    }
}

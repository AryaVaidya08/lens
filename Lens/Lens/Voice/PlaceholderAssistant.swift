import Foundation

/// Replace this reply with APIClient.askQuestion once backend integration is ready.
/// Answers come from DemoDrugCatalog and are labeled as demo data.
enum PlaceholderAssistant {
    static func reply(to question: String, drug: Drug?) -> String {
        guard let drug, let demo = DemoDrugCatalog.drug(id: drug.id) else {
            let names = DemoDrugCatalog.all.map(\.name).joined(separator: ", ")
            return "I heard you say: \(question). This is a demo reply. Point the camera at a drug first. Demo drugs are \(names)."
        }
        let answer = topic(for: question).flatMap { demo.answers[$0] }
            ?? "\(demo.name): \(demo.headline). " + demo.bullets.joined(separator: ". ") + "."
        return "Demo data for \(demo.name). \(answer)"
    }

    private static func topic(for question: String) -> DemoDrug.Topic? {
        let text = question.lowercased()
        let keywords: [(DemoDrug.Topic, [String])] = [
            (.sideEffects, ["side effect", "adverse", "side"]),
            (.interactions, ["interact", "combine", "alcohol", "together", "mix"]),
            (.warnings, ["warning", "risk", "safe", "contraindicat", "boxed", "caution"]),
            (.dosing, ["dose", "dosing", "dosage", "how much", "how often", "milligram", "mg", "take"]),
            (.indications, ["used for", "use", "indicat", "treat", "what is"])
        ]
        return keywords.first { _, words in words.contains { text.contains($0) } }?.0
    }
}

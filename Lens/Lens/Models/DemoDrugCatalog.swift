//
//  Fake drug data for detection, the HUD, and the voice assistant.
//
//  Stands in for /detect, /drug/{id}/summary, and /drug/{id}/ask until the
//  classifier is trained and the backend is live. Keep the IDs aligned with
//  the training folder names so swapping in real results changes nothing
//  downstream.
//

import Foundation

struct DemoDrug {
    enum Topic: CaseIterable {
        case dosing, sideEffects, interactions, warnings, indications
    }

    let id: String
    let name: String
    let headline: String
    let bullets: [String]
    let answers: [Topic: String]

    var drug: Drug { Drug(id: id, name: name) }

    var summary: DrugSummary {
        DrugSummary(drugId: id, name: name, tier: "new", headline: headline, bullets: bullets)
    }
}

enum DemoDrugCatalog {
    static let all: [DemoDrug] = [adderall, biofreeze, lorazepam]

    static func drug(id: String) -> DemoDrug? {
        all.first { $0.id == id }
    }

    /// Matches OCR/barcode text containing a drug name; anything else maps
    /// to a stable pick so the same object keeps resolving to the same drug.
    static func resolve(payload: String) -> DemoDrug {
        let text = payload.lowercased()
        if let match = all.first(where: { text.contains($0.id) }) {
            return match
        }
        let checksum = payload.unicodeScalars.reduce(0) { $0 &+ Int($1.value) }
        return all[checksum % all.count]
    }

    static let adderall = DemoDrug(
        id: "adderall",
        name: "Adderall",
        headline: "CNS stimulant · Schedule II",
        bullets: [
            "Indicated for ADHD and narcolepsy",
            "Boxed warning: abuse, misuse, and addiction",
            "Monitor blood pressure, heart rate, and appetite"
        ],
        answers: [
            .dosing: "Immediate-release tablets usually start at 5 milligrams once or twice daily and are titrated weekly to response. The extended-release capsule is taken once each morning.",
            .sideEffects: "Common side effects include decreased appetite, insomnia, dry mouth, headache, weight loss, and increased heart rate.",
            .interactions: "Avoid use within 14 days of an MAO inhibitor. Use caution with other serotonergic drugs, and note that urinary acidifying or alkalinizing agents change amphetamine levels.",
            .warnings: "It carries a boxed warning for abuse, misuse, and addiction. Assess cardiovascular risk before starting and reassess the need for treatment periodically.",
            .indications: "Adderall is mixed amphetamine salts, indicated for attention deficit hyperactivity disorder and narcolepsy."
        ]
    )

    static let biofreeze = DemoDrug(
        id: "biofreeze",
        name: "Biofreeze",
        headline: "Topical menthol analgesic · OTC",
        bullets: [
            "Temporary relief of minor muscle and joint pain",
            "External use only; avoid broken or irritated skin",
            "Don't use with heating pads or tight bandages"
        ],
        answers: [
            .dosing: "Adults and children 12 and older can apply it to the affected area no more than 4 times daily.",
            .sideEffects: "Side effects are mostly local: redness, irritation, or a burning sensation. Stop use if the skin blisters or irritation is severe.",
            .interactions: "There are no meaningful systemic interactions. Avoid layering it with other topical analgesics or applying heat over it.",
            .warnings: "It's for external use only. Keep it away from the eyes and mucous membranes, and see a clinician if pain lasts more than 7 days or worsens.",
            .indications: "Biofreeze is an over-the-counter menthol gel for temporary relief of minor aches and pains of muscles and joints."
        ]
    )

    static let lorazepam = DemoDrug(
        id: "lorazepam",
        name: "Lorazepam",
        headline: "Benzodiazepine · Schedule IV",
        bullets: [
            "Anxiety disorders and short-term relief of anxiety",
            "Boxed warning: risks with opioids; abuse and dependence",
            "Taper to stop; abrupt discontinuation can cause withdrawal"
        ],
        answers: [
            .dosing: "For anxiety, the usual range is 2 to 3 milligrams per day in divided doses, individualized to the patient. Start lower in elderly or debilitated patients.",
            .sideEffects: "The most common side effects are sedation, dizziness, weakness, and unsteadiness.",
            .interactions: "Combining it with opioids, alcohol, or other CNS depressants can cause profound sedation and respiratory depression. Valproate and probenecid raise lorazepam levels.",
            .warnings: "It carries a boxed warning for concomitant opioid use, abuse and misuse, and dependence with withdrawal reactions. Taper gradually when stopping.",
            .indications: "Lorazepam is a benzodiazepine used to manage anxiety disorders and for short-term relief of anxiety symptoms."
        ]
    )
}

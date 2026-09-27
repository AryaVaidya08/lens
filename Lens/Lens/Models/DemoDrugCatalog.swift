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
    /// The exact barcode payload printed on our physical demo bottle for
    /// this drug (UPC-A/EAN-13/EAN-8 as decoded by Vision's
    /// VNDetectBarcodesRequest — no formatting, no checksum stripped).
    let barcode: String
    let headline: String
    let bullets: [String]
    let answers: [Topic: String]

    var drug: Drug { Drug(id: id, name: name) }

    var summary: DrugSummary {
        DrugSummary(
            drugId: id,
            name: name,
            tier: "new",
            headline: headline,
            bullets: bullets,
            summarySource: "unavailable"
        )
    }
}

enum DemoDrugCatalog {
    static let all: [DemoDrug] = [adderall, biofreeze, lorazepam, xyzal, claritin]

    static func drug(id: String) -> DemoDrug? {
        all.first { $0.id == id }
    }

    /// Matches a scanned barcode payload exactly against one of our demo
    /// bottles' known barcodes, or (for the OCR fallback) matches text
    /// that contains the drug's name. Returns `nil` — rather than guessing
    /// — if the payload doesn't match any of our known demo drugs, so an
    /// unrecognized scan simply doesn't display anything instead of
    /// showing the wrong drug.
    static func resolve(payload: String) -> DemoDrug? {
        let trimmed = payload.trimmingCharacters(in: .whitespacesAndNewlines)
        if let byBarcode = all.first(where: { $0.barcode == trimmed }) {
            return byBarcode
        }
        let lowercased = trimmed.lowercased()
        return all.first { lowercased.contains($0.name.lowercased()) }
    }

    static let adderall = DemoDrug(
        id: "adderall",
        name: "Adderall",
        barcode: "0357844110014",
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
        barcode: "0731124100009",
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
        barcode: "0362135861018",
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

    static let xyzal = DemoDrug(
        id: "xyzal",
        name: "Xyzal",
        barcode: "824247",
        headline: "Second-generation antihistamine · OTC",
        bullets: [
            "Relief of indoor/outdoor allergy symptoms and chronic hives",
            "Once-daily dosing, taken in the evening",
            "Less sedating than first-generation antihistamines"
        ],
        answers: [
            .dosing: "The usual adult dose is 5 milligrams once daily in the evening. Reduce to every other day in moderate renal impairment.",
            .sideEffects: "Somnolence, fatigue, and dry mouth are the most commonly reported side effects.",
            .interactions: "Avoid combining with alcohol or other CNS depressants, which can add to drowsiness.",
            .warnings: "Use caution when driving or operating machinery until the individual response is known, especially at higher-than-recommended doses.",
            .indications: "Xyzal (levocetirizine) treats symptoms of seasonal and perennial allergic rhinitis and chronic idiopathic urticaria."
        ]
    )

    static let claritin = DemoDrug(
        id: "claritin",
        name: "Claritin",
        barcode: "31001563",
        headline: "Second-generation antihistamine · OTC",
        bullets: [
            "Relief of sneezing, runny nose, and itchy/watery eyes",
            "Once-daily, non-drowsy dosing",
            "Also indicated for chronic idiopathic urticaria"
        ],
        answers: [
            .dosing: "The usual adult and child (6+) dose is 10 milligrams once daily. Reduce to every other day in significant hepatic or renal impairment.",
            .sideEffects: "Headache, drowsiness, dry mouth, and fatigue are the most commonly reported side effects, though it's marketed as non-drowsy.",
            .interactions: "Ketoconazole, erythromycin, and cimetidine can raise loratadine plasma levels, though this hasn't been shown to increase side effects in studies.",
            .warnings: "Generally well tolerated; discontinue if hypersensitivity to the drug occurs.",
            .indications: "Claritin (loratadine) relieves symptoms of seasonal allergic rhinitis and treats chronic idiopathic urticaria."
        ]
    )
}

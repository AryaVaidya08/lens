//
//  DrugSummary model.
//
//  Matches backend GET /drug/{drug_id}/summary response shape. This is
//  what both HUDView and HUDOverlayView render.
//

import Foundation

enum ScanSummaryPhase {
    case loading, loaded, offline

    static func resolve(drugId: String, summary: DrugSummary?, failedDrugId: String?) -> Self {
        if summary?.drugId == drugId { return .loaded }
        if failedDrugId == drugId { return .offline }
        return .loading
    }
}

struct PatientChartCheck: Codable, Equatable {
    let status: String
    let patientId: String
    let patientName: String
    let headline: String
    let flags: [String]
    let disclaimer: String

    var isFlag: Bool { status == "flag" }

    var displayFlags: [String] {
        flags.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    var hasConcerns: Bool { !displayFlags.isEmpty }
    var hasNoMatches: Bool { status == "clear" && !hasConcerns }

    /// Name-token overlap against the imported chart. Same idea as
    /// `backend/app/personalization/patient_check.py` — not a clinical check.
    static func evaluate(patient: Patient, drugId: String, drugName: String, extraText: String = "") -> PatientChartCheck {
        var drugTerms = tokens(drugName)
        drugTerms.formUnion(tokens(drugId.replacingOccurrences(of: "_", with: " ")))
        drugTerms.formUnion(tokens(extraText))

        var flags: [String] = []
        for allergy in items(patient.allergies) {
            let lower = allergy.lowercased()
            if ["none known", "no known allergies", "nka", "nkda"].contains(lower) { continue }
            if !overlap(tokens(allergy), drugTerms).isEmpty {
                flags.append("Allergy list mentions \(allergy).")
            }
        }
        let blob = extraText.lowercased()
        for med in items(patient.currentMedications) {
            let lower = med.lowercased()
            if ["none", "none known"].contains(lower) { continue }
            let medTerms = tokens(med)
            if !overlap(medTerms, drugTerms).isEmpty {
                flags.append("Already on the chart: \(med).")
                continue
            }
            if medTerms.contains(where: { token in
                token.count >= 4 && blob.range(of: "\\b\(NSRegularExpression.escapedPattern(for: token))\\b", options: .regularExpression) != nil
            }) {
                flags.append("Dossier interaction text mentions \(med).")
            }
        }

        let name = patient.displayName
        let first = name.split(separator: " ").first.map(String.init) ?? "this patient"
        flags = Array(flags.prefix(4))
        if flags.isEmpty {
            return PatientChartCheck(
                status: "clear",
                patientId: patient.id,
                patientName: name,
                headline: "No name match on \(first)'s allergy or med list",
                flags: [],
                disclaimer: "Name match against the imported chart and dossier. Not a clinical decision."
            )
        }
        return PatientChartCheck(
            status: "flag",
            patientId: patient.id,
            patientName: name,
            headline: "Chart flag for \(name.isEmpty ? "this patient" : name)",
            flags: flags,
            disclaimer: "Name match against the imported chart and dossier. Not a clinical decision."
        )
    }

    private static let stopWords: Set<String> = [
        "none", "known", "nka", "nkda", "no", "not", "the", "and", "with", "for",
        "from", "daily", "once", "twice", "tablet", "tablets", "capsule", "oral",
        "mg", "ml", "bid", "tid", "qid", "prn", "use"
    ]

    private static func items(_ text: String) -> [String] {
        text.replacingOccurrences(of: " and ", with: ",", options: .caseInsensitive)
            .components(separatedBy: CharacterSet(charactersIn: ",;/\n"))
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty && !["none", "n/a", "na"].contains($0.lowercased()) }
    }

    private static func tokens(_ text: String) -> Set<String> {
        Set(
            text.lowercased()
                .split { !$0.isLetter && !$0.isNumber }
                .map(String.init)
                .filter { $0.count >= 4 && !stopWords.contains($0) }
        )
    }

    private static func overlap(_ left: Set<String>, _ right: Set<String>) -> Set<String> {
        var hits = Set<String>()
        for a in left {
            for b in right {
                if a == b || (a.count >= 5 && b.count >= 5 && (a.contains(b) || b.contains(a))) {
                    hits.insert(a.count >= b.count ? a : b)
                }
            }
        }
        return hits
    }

    enum CodingKeys: String, CodingKey {
        case status, headline, flags, disclaimer
        case patientId = "patient_id"
        case patientName = "patient_name"
    }
}

struct DrugSummary: Codable {
    let drugId: String
    let name: String
    let tier: String
    let headline: String
    let bullets: [String]
    var patientCheck: PatientChartCheck? = nil
    var fullBullets: [String]? = nil

    var expandedBullets: [String] {
        let full = (fullBullets ?? []).filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        return full.isEmpty ? bullets : full
    }

    /// Short lines for the HUD bubble only. The complete text stays in `expandedBullets`.
    var previewBullets: [String] {
        let source = bullets.isEmpty ? expandedBullets : bullets
        return source.map { Self.previewLine($0) }
    }

    static func previewLine(_ text: String, maxChars: Int = 90) -> String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count > maxChars else { return trimmed }
        var cut = String(trimmed.prefix(maxChars))
        if let space = cut.lastIndex(of: " "),
           cut.distance(from: cut.startIndex, to: space) > (maxChars * 6) / 10 {
            cut = String(cut[..<space])
        }
        return cut.trimmingCharacters(in: CharacterSet(charactersIn: ".,; ")) + "..."
    }

    func chartCheck(for patientId: String) -> PatientChartCheck? {
        let wanted = patientId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let check = patientCheck else { return nil }
        let got = check.patientId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard got == wanted else { return nil }
        return check
    }

    func applyingChartCheck(for patient: Patient, extraText: String = "") -> DrugSummary {
        if chartCheck(for: patient.id) != nil { return self }
        var copy = self
        copy.patientCheck = .evaluate(patient: patient, drugId: drugId, drugName: name, extraText: extraText)
        return copy
    }

    enum CodingKeys: String, CodingKey {
        case drugId = "drug_id"
        case name, tier, headline, bullets
        case patientCheck = "patient_check"
        case fullBullets = "full_bullets"
    }

    init(drugId: String, name: String, tier: String, headline: String, bullets: [String], patientCheck: PatientChartCheck? = nil, fullBullets: [String]? = nil) {
        self.drugId = drugId
        self.name = name
        self.tier = tier
        self.headline = headline
        self.bullets = bullets
        self.patientCheck = patientCheck
        self.fullBullets = fullBullets
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        drugId = try container.decode(String.self, forKey: .drugId)
        name = try container.decode(String.self, forKey: .name)
        tier = try container.decode(String.self, forKey: .tier)
        headline = try container.decode(String.self, forKey: .headline)
        bullets = try container.decode([String].self, forKey: .bullets)
        fullBullets = try container.decodeIfPresent([String].self, forKey: .fullBullets)
        patientCheck = try? container.decodeIfPresent(PatientChartCheck.self, forKey: .patientCheck)
    }
}

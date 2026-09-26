import Foundation

struct MedicationEntry: Codable, Identifiable, Equatable {
    var id = UUID().uuidString
    var name = ""
    var strength = ""
    var formulation = ""
    var directions = ""
    var sourceText = ""
    var reportedUse = "not_asked"
    var notes = ""
    var referenceId: String?

    var isValid: Bool { !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    var detail: String {
        [strength, formulation, directions].filter { !$0.isEmpty }.joined(separator: " · ")
    }
    enum CodingKeys: String, CodingKey {
        case id, name, strength, formulation, directions, notes
        case sourceText = "source_text", reportedUse = "reported_use", referenceId = "reference_id"
    }
}

struct MedicationReviewDraft: Codable, Equatable {
    var revision = 0
    var referenceSource = ""
    var referenceText = ""
    var referenceVerified = false
    var collectionComplete = false
    var reference: [MedicationEntry] = []
    var observed: [MedicationEntry] = []
    var notes = ""
    var reviewed = false

    var canCompare: Bool {
        !referenceSource.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && referenceVerified && collectionComplete
    }
    enum CodingKeys: String, CodingKey {
        case revision, reference, observed, notes, reviewed
        case referenceSource = "reference_source", referenceText = "reference_text"
        case referenceVerified = "reference_verified", collectionComplete = "collection_complete"
    }
}

struct MedicationFinding: Decodable {
    let kind: String
    let title: String
    let detail: String
}

struct SavedMedicationReview: Decodable, Identifiable {
    let id: String
    let updatedAt: String
    let draft: MedicationReviewDraft
    let findings: [MedicationFinding]
    let report: String

    enum CodingKeys: String, CodingKey {
        case id = "review_id", updatedAt = "updated_at", findings, report
    }
    init(from decoder: Decoder) throws {
        draft = try MedicationReviewDraft(from: decoder)
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decode(String.self, forKey: .id)
        updatedAt = try values.decode(String.self, forKey: .updatedAt)
        findings = try values.decode([MedicationFinding].self, forKey: .findings)
        report = try values.decode(String.self, forKey: .report)
    }
    var dateLabel: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: updatedAt)?.formatted(date: .abbreviated, time: .shortened) ?? updatedAt
    }
}

struct MedicationReviewList: Decodable {
    let reviews: [SavedMedicationReview]
}

/// Suggestions only: users inspect the label and confirm each entry. No drug
/// catalog guesses, dose conversions, or interpretation of patient instructions.
enum MedicationLabelSuggestions {
    static func entry(from text: String) -> MedicationEntry {
        var entry = MedicationEntry()
        entry.sourceText = text
        let lines = text.components(separatedBy: .newlines).map { $0.trimmingCharacters(in: .whitespaces) }
        let pattern = #"(?i)^([a-z][a-z /()-]{1,80}?)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%)(?=\s|/|$)(?:\s*/\s*\d*\s*(?:ml|g))?)"#
        if let regex = try? NSRegularExpression(pattern: pattern) {
            for line in lines {
                let range = NSRange(line.startIndex..., in: line)
                guard let match = regex.firstMatch(in: line, range: range),
                      let name = Range(match.range(at: 1), in: line),
                      let strength = Range(match.range(at: 2), in: line) else { continue }
                entry.name = String(line[name])
                entry.strength = String(line[strength])
                break
            }
        }
        // Preserve the label's actual wording, including release modifiers.
        if let line = lines.first(where: { $0.range(of: #"(?i)\b(tablets?|capsules?|solution|cream|ointment|gel|patch)\b"#, options: .regularExpression) != nil }) {
            if let range = line.range(of: #"(?i)\b(?:(?:extended[- ]release|delayed[- ]release|immediate[- ]release)\s+)?(?:tablets?|capsules?|solution|cream|ointment|gel|patch)\b"#, options: .regularExpression) {
                entry.formulation = String(line[range])
            }
        }
        entry.directions = lines.first(where: { $0.range(of: #"(?i)^(take|apply|inject|inhale|instill|place|use)\b"#, options: .regularExpression) != nil }) ?? ""
        return entry
    }
}

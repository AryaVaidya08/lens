import Foundation

@main
struct MedicationReviewChecks {
    static func main() throws {
        let text = "Examplepharm\nExamplemed 10 mg\nextended-release tablets\nTake one tablet daily"
        let entry = MedicationLabelSuggestions.entry(from: text)
        precondition(entry.name == "Examplemed")
        precondition(entry.strength == "10 mg")
        precondition(entry.formulation == "extended-release tablets")
        precondition(entry.directions == "Take one tablet daily")
        precondition(entry.sourceText == text && entry.reportedUse == "not_asked")
        let missing = MedicationLabelSuggestions.entry(from: "Unreadable label\nLOT 12345")
        precondition(missing.name.isEmpty && missing.strength.isEmpty && missing.directions.isEmpty)
        let liquid = MedicationLabelSuggestions.entry(from: "Examplemed 10 mg / 5 ml\noral solution")
        precondition(liquid.strength == "10 mg / 5 ml")
        let topical = MedicationLabelSuggestions.entry(from: "Examplegel 4%\nApply to affected area")
        precondition(topical.name == "Examplegel" && topical.strength == "4%")
        let compact = MedicationLabelSuggestions.entry(from: "Examplemed 10mg/ml")
        precondition(compact.strength == "10mg/ml")
        var draft = MedicationReviewDraft()
        precondition(!draft.canCompare)
        draft.referenceSource = "Discharge list 27 Sep"
        draft.referenceVerified = true
        precondition(!draft.canCompare)
        draft.collectionComplete = true
        precondition(draft.canCompare)
        draft.reference = [entry]
        draft.observed = [entry]
        let data = try JSONEncoder().encode(draft)
        let object = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        precondition(object["reference_source"] as? String == draft.referenceSource)
        let observed = (object["observed"] as! [[String: Any]])[0]
        precondition(observed["reported_use"] as? String == "not_asked")
        precondition(observed["source_text"] as? String == text)
        var response = object
        response["review_id"] = "review-1"
        response["updated_at"] = "2026-09-27T12:00:00.123456+00:00"
        response["findings"] = [["kind": "difference", "title": "Strength text differs", "detail": "Review source details"]]
        response["report"] = "Report"
        let saved = try JSONDecoder().decode(SavedMedicationReview.self, from: JSONSerialization.data(withJSONObject: response))
        precondition(saved.draft == draft && saved.findings.count == 1 && saved.report == "Report")
        print("PASS: medication OCR suggestions, review validation, JSON encoding/decoding")
    }
}

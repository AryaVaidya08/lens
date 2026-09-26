import Foundation

/// Uses only the isolated mock backend on :8001 documented in medication-review.md.
@main
struct MedicationReviewLiveChecks {
    @MainActor
    static func main() async throws {
        let client = APIClient(baseURL: URL(string: "http://127.0.0.1:8001")!)
        let session = try await client.login(email: "maya.patel@lens.demo", password: "demo")
        client.sessionToken = session.sessionToken
        let id = UUID().uuidString
        var draft = MedicationReviewDraft()
        draft.referenceSource = "QA discharge list"
        var ref = MedicationEntry()
        ref.name = "Examplemed"
        ref.strength = "5 mg"
        ref.formulation = "tablet"
        ref.directions = "Take one daily"
        draft.reference = [ref]
        var bottle = ref
        bottle.id = UUID().uuidString
        bottle.strength = "10 mg"
        bottle.reportedUse = "taking"
        draft.observed = [bottle]
        let savedDraft = try await client.saveMedicationReview(patientId: "pat_001", reviewId: id, draft: draft)
        precondition(savedDraft.draft.revision == 1 && savedDraft.report.isEmpty)
        draft = savedDraft.draft
        draft.referenceVerified = true
        draft.collectionComplete = true
        draft.reviewed = true
        let compared = try await client.saveMedicationReview(patientId: "pat_001", reviewId: id, draft: draft)
        precondition(compared.draft.revision == 2)
        precondition(compared.findings.count == 1 && compared.findings[0].title == "Strength text differs")
        precondition(compared.report.contains("reference: 5 mg; bottle: 10 mg"))
        let reopened = try await client.medicationReviews(patientId: "pat_001")
        precondition(reopened.first(where: { $0.id == compared.id })?.report == compared.report)
        do {
            _ = try await client.saveMedicationReview(patientId: "pat_001", reviewId: id, draft: draft)
            preconditionFailure("Stale save was accepted")
        } catch APIError.serverMessage(let message) {
            precondition(message.contains("newer version"))
        }
        let other = try await client.login(email: "james.chen@lens.demo", password: "demo")
        client.sessionToken = other.sessionToken
        do {
            _ = try await client.medicationReviews(patientId: "pat_001")
            preconditionFailure("Another clinician read the review")
        } catch APIError.serverMessage(let message) {
            precondition(message.contains("not found"))
        }
        print("PASS: Swift URLSession → FastAPI draft, compare, reopen, conflict, and patient isolation")
    }
}

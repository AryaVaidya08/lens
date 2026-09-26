import Foundation

/// Run only against the isolated mongomock backend on :8001.
@main
struct MedicationAccessLiveChecks {
    @MainActor
    static func main() async throws {
        let client = APIClient(baseURL: URL(string: "http://127.0.0.1:8001")!)
        let login = try await client.login(email: "maya.patel@lens.demo", password: "demo")
        client.sessionToken = login.sessionToken
        let policies = try await client.accessPolicies()
        precondition(policies.count == 1)
        let policy = policies[0]
        var d = MedicationAccessDraft()
        d.policyId = policy.id
        d.selectPolicy(policy)
        d.medication = policy.medication; d.strength = policy.strengths[0]; d.formulation = policy.formulation
        d.payer = policy.payer; d.plan = "QA plan"; d.memberId = "QA-MEMBER"; d.patientDob = "2000-01-01"
        d.directions = "Directions from QA prescription"; d.quantity = "30 tablets / 30 days"
        d.indication = "QA indication"; d.prescriber = "QA prescriber / NPI"; d.prescriberContact = "QA contact"
        d.rationale = "Patient-specific rationale for testing only"
        d.policyConfirmed = true
        let id = UUID().uuidString
        let incomplete = try await client.saveMedicationAccess(patientId: "pat_001", caseId: id, draft: d)
        precondition(incomplete.missing.count == 1 && !incomplete.draft.letter.isEmpty)
        precondition(!incomplete.draft.reviewed)
        d = incomplete.draft
        d.evidence[0].text = "Confirmed patient-specific reason"
        d.evidence[0].source = "QA note dated 2026-09-26"
        d.evidence[0].confirmed = true
        // Backend must regenerate even if the caller accidentally retains the old letter.
        let complete = try await client.saveMedicationAccess(patientId: "pat_001", caseId: id, draft: d)
        precondition(complete.missing.isEmpty && complete.draft.letter.contains("Confirmed patient-specific reason"))
        d = complete.draft
        d.reviewed = true; d.status = .ready
        let ready = try await client.saveMedicationAccess(patientId: "pat_001", caseId: id, draft: d)
        d = ready.draft; d.status = .submitted; d.statusNote = "Portal receipt QA-001"
        let submitted = try await client.saveMedicationAccess(patientId: "pat_001", caseId: id, draft: d)
        precondition(submitted.history.last?.packet == complete.draft.letter)
        precondition(submitted.exportText.contains("SUBMISSION CHECKLIST"))
        do {
            _ = try await client.saveMedicationAccess(patientId: "pat_001", caseId: id, draft: d)
            preconditionFailure("Stale revision accepted")
        } catch APIError.serverMessage(let message) { precondition(message.contains("newer version")) }
        d = submitted.draft; d.status = .approved; d.statusNote = "Payer decision QA-002"
        let approved = try await client.saveMedicationAccess(patientId: "pat_001", caseId: id, draft: d)
        d = approved.draft; d.status = .obtained; d.statusNote = "Patient confirmed receipt"
        let obtained = try await client.saveMedicationAccess(patientId: "pat_001", caseId: id, draft: d)
        let reopened = try await client.medicationAccess(patientId: "pat_001")
        precondition(reopened.first(where: { $0.id == obtained.id })?.draft == obtained.draft)
        let other = try await client.login(email: "james.chen@lens.demo", password: "demo")
        client.sessionToken = other.sessionToken
        do {
            _ = try await client.medicationAccess(patientId: "pat_001")
            preconditionFailure("Another clinician read the case")
        } catch APIError.serverMessage(let message) { precondition(message.contains("not found")) }
        print("PASS: Swift → FastAPI policy, gaps, regeneration, review, submission, approval, receipt, reopen, conflict, and ownership")
    }
}

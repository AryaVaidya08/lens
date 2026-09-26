import Foundation

@main
struct MedicationAccessChecks {
    static func main() throws {
        var draft = MedicationAccessDraft()
        let original = draft.sourceContent
        draft.status = .submitted; draft.revision = 3; draft.assignee = "Staff"
        draft.followUp = "Tomorrow"; draft.statusNote = "Receipt"; draft.letter = "Letter"; draft.reviewed = true
        precondition(draft.sourceContent == original, "Workflow metadata should not change source facts")
        draft.rationale = "New clinical evidence"
        precondition(draft.sourceContent != original, "Clinical edits must invalidate the letter")
        precondition(!AccessStatus.incomplete.next.contains(.approved))
        precondition(AccessStatus.denied.next == [.incomplete])
        precondition(AccessStatus.obtained.packetLocked)
        precondition(!AccessStatus.ready.packetLocked)
        draft.policyId = "custom"
        draft.requirements = [AccessRequirement(id: "trial", title: "Trial or exception", detail: "")]
        draft.selectPolicy(nil)
        precondition(draft.evidence.map(\.requirementId) == ["trial"], "Returning to a custom policy must restore editable evidence rows")
        let data = try JSONEncoder().encode(draft)
        let decoded = try JSONDecoder().decode(MedicationAccessDraft.self, from: data)
        precondition(decoded == draft)
        let object = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        precondition(object["policy_id"] != nil && object["member_id"] != nil && object["medication_source"] != nil)
        print("PASS: access draft round-trip, invalidation boundaries, and status transitions")
    }
}

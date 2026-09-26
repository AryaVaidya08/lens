import Foundation

struct AccessRequirement: Codable, Equatable, Identifiable {
    var id = UUID().uuidString
    var title = ""
    var detail = ""
}

struct AccessEvidence: Codable, Equatable, Identifiable {
    var requirementId: String
    var text = ""
    var source = ""
    var confirmed = false
    var id: String { requirementId }
    enum CodingKeys: String, CodingKey {
        case requirementId = "requirement_id", text, source, confirmed
    }
}

struct AccessPolicy: Codable, Equatable, Identifiable {
    let id: String
    let title: String
    let payer: String
    let medication: String
    let strengths: [String]
    let formulation: String
    let sourceURL: String
    let sourceDate: String
    let scope: String
    let requirements: [AccessRequirement]
    enum CodingKeys: String, CodingKey {
        case id, title, payer, medication, strengths, formulation, scope, requirements
        case sourceURL = "source_url", sourceDate = "source_date"
    }
}

enum AccessStatus: String, Codable, CaseIterable {
    case incomplete, ready, submitted, approved, denied, obtained
    var label: String {
        switch self {
        case .incomplete: "Incomplete"
        case .ready: "Ready to submit"
        case .submitted: "Submitted"
        case .approved: "Approved"
        case .denied: "Denied"
        case .obtained: "Patient obtained medication"
        }
    }
    var next: [Self] {
        switch self {
        case .incomplete: [.ready]
        case .ready: [.incomplete, .submitted]
        case .submitted: [.incomplete, .approved, .denied]
        case .approved: [.incomplete, .obtained]
        case .denied, .obtained: [.incomplete]
        }
    }
    var packetLocked: Bool { [.submitted, .approved, .denied, .obtained].contains(self) }
}

struct MedicationAccessDraft: Codable, Equatable {
    var revision = 0
    var policyId = ""
    var policyTitle = ""
    var policySource = ""
    var policyDate = ""
    var requirements: [AccessRequirement] = []
    var policyConfirmed = false
    var medication = ""
    var strength = ""
    var formulation = ""
    var directions = ""
    var medicationSource = ""
    var quantity = ""
    var indication = ""
    var payer = ""
    var plan = ""
    var memberId = ""
    var patientDob = ""
    var prescriber = ""
    var prescriberContact = ""
    var rationale = ""
    var evidence: [AccessEvidence] = []
    var requestKind = "initial"
    var denialReason = ""
    var denialReference = ""
    var letter = ""
    var reviewed = false
    var status: AccessStatus = .incomplete
    var statusNote = ""
    var assignee = ""
    var followUp = ""

    /// Changes to source facts invalidate the generated letter and its review.
    var sourceContent: Self {
        var copy = self
        copy.revision = 0; copy.letter = ""; copy.reviewed = false
        copy.status = .incomplete; copy.statusNote = ""; copy.assignee = ""; copy.followUp = ""
        return copy
    }
    mutating func selectPolicy(_ policy: AccessPolicy?) {
        policyConfirmed = false
        evidence = []
        guard let policy else {
            if policyId == "custom" { evidence = requirements.map { AccessEvidence(requirementId: $0.id) } }
            return
        }
        // Selection never changes the prescription or insurance entered by staff.
        evidence = policy.requirements.map { AccessEvidence(requirementId: $0.id) }
    }
    enum CodingKeys: String, CodingKey {
        case revision, requirements, medication, strength, formulation, directions, quantity, indication
        case medicationSource = "medication_source"
        case payer, plan, prescriber, rationale, evidence, letter, reviewed, status, assignee
        case policyId = "policy_id", policyTitle = "policy_title", policySource = "policy_source"
        case policyDate = "policy_date", policyConfirmed = "policy_confirmed", memberId = "member_id"
        case patientDob = "patient_dob", prescriberContact = "prescriber_contact"
        case requestKind = "request_kind", denialReason = "denial_reason", denialReference = "denial_reference"
        case statusNote = "status_note", followUp = "follow_up"
    }
}

struct AccessEvent: Decodable {
    let status: AccessStatus
    let at: String
    let note: String
    let packet: String?
}

struct SavedMedicationAccess: Decodable, Identifiable {
    let id: String
    let updatedAt: String
    let draft: MedicationAccessDraft
    let policy: AccessPolicy?
    let missing: [String]
    let generatedLetter: String
    let checklist: [String]
    let history: [AccessEvent]
    enum CodingKeys: String, CodingKey {
        case id = "case_id", updatedAt = "updated_at", policy, missing, checklist, history
        case generatedLetter = "generated_letter"
    }
    init(from decoder: Decoder) throws {
        draft = try MedicationAccessDraft(from: decoder)
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        updatedAt = try c.decode(String.self, forKey: .updatedAt)
        policy = try c.decodeIfPresent(AccessPolicy.self, forKey: .policy)
        missing = try c.decode([String].self, forKey: .missing)
        generatedLetter = try c.decode(String.self, forKey: .generatedLetter)
        checklist = try c.decode([String].self, forKey: .checklist)
        history = try c.decode([AccessEvent].self, forKey: .history)
    }
    var exportText: String {
        ([draft.letter, "", "SUBMISSION CHECKLIST"] + checklist.map { "• " + $0 }).joined(separator: "\n")
    }
}

struct AccessPolicyList: Decodable { let policies: [AccessPolicy] }
struct MedicationAccessList: Decodable { let cases: [SavedMedicationAccess] }

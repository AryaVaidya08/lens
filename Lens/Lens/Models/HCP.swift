//
//  HCP model.
//
//  Matches backend GET /profile/{hcp_id}, /auth/login, and /auth/register.
//

import Foundation

struct HCP: Codable, Identifiable, Equatable {
    let id: String
    var name: String
    var specialty: String
    /// drug_id -> "new" | "returning" | "expert". Empty until the HCP has
    /// scanned something; absent entirely from the local demo profiles.
    var familiarity: [String: String]? = nil
    var email: String? = nil
    var firstName: String? = nil
    var lastName: String? = nil
    var professionalRole: String? = nil
    var credentials: String? = nil
    var organization: String? = nil
    var practiceSetting: String? = nil
    var workPhone: String? = nil
    var city: String? = nil
    var region: String? = nil
    var country: String? = nil
    var patientIds: [String]? = nil

    enum CodingKeys: String, CodingKey {
        case id = "hcp_id"
        case name, specialty, familiarity, email
        case firstName = "first_name"
        case lastName = "last_name"
        case professionalRole = "professional_role"
        case credentials
        case organization
        case practiceSetting = "practice_setting"
        case workPhone = "work_phone"
        case city, region, country
        case patientIds = "patient_ids"
    }
}

extension HCP {
    /// Local demo identities. Keep these IDs when backend seeding is connected —
    /// backend/app/db/seed.py seeds exactly these three.
    static let demoProfiles: [HCP] = [
        HCP(
            id: "hcp_001",
            name: "Dr. Maya Patel",
            specialty: "Primary Care",
            email: "maya.patel@lens.demo",
            firstName: "Maya",
            lastName: "Patel",
            professionalRole: "Physician",
            credentials: "MD"
        ),
        HCP(
            id: "hcp_002",
            name: "Dr. James Chen",
            specialty: "Cardiology",
            email: "james.chen@lens.demo",
            firstName: "James",
            lastName: "Chen",
            professionalRole: "Physician",
            credentials: "MD"
        ),
        HCP(
            id: "hcp_003",
            name: "Dr. Sofia Ramirez",
            specialty: "Endocrinology",
            email: "sofia.ramirez@lens.demo",
            firstName: "Sofia",
            lastName: "Ramirez",
            professionalRole: "Physician",
            credentials: "MD"
        )
    ]
}

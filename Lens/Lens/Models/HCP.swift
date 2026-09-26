//
//  HCP model.
//
//  Matches backend GET /profile/{hcp_id} response shape.
//

import Foundation

struct HCP: Codable, Identifiable {
    let id: String
    let name: String
    let specialty: String
    // TODO: implement — add `familiarity: [String: String]` (drug_id ->
    // tier) once routes/profile.py returns it.
}

extension HCP {
    /// Local demo identities. Keep these IDs when backend seeding is connected.
    static let demoProfiles: [HCP] = [
        HCP(id: "hcp_001", name: "Dr. Maya Patel", specialty: "Primary Care"),
        HCP(id: "hcp_002", name: "Dr. James Chen", specialty: "Cardiology"),
        HCP(id: "hcp_003", name: "Dr. Sofia Ramirez", specialty: "Endocrinology")
    ]
}

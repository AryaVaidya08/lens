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

//
//  DrugSummary model.
//
//  Matches backend GET /drug/{drug_id}/summary response shape. This is
//  what both HUDView and HUDOverlayView render.
//

import Foundation

struct DrugSummary: Codable {
    let drugId: String
    let name: String
    let tier: String
    let headline: String
    let bullets: [String]

    enum CodingKeys: String, CodingKey {
        case drugId = "drug_id"
        case name, tier, headline, bullets
    }
}

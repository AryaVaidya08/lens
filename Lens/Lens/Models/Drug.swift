//
//  Drug model.
//
//  Matches backend POST /detect response shape.
//

import Foundation

struct Drug: Codable, Identifiable, Equatable {
    let id: String
    let name: String

    enum CodingKeys: String, CodingKey {
        case id = "drug_id"
        case name
    }
}

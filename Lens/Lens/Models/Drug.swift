//
//  Drug model.
//
//  Matches backend POST /detect response shape.
//

import Foundation

struct Drug: Codable, Identifiable {
    let id: String
    let name: String
}

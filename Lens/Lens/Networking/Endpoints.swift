//
//  Single source of truth for backend paths.
//
//  Every path here must match its counterpart in backend/app/routes/
//  exactly. If you change one side, change this file and tell the
//  other lane — this is the contract, in one place.
//

enum Endpoints {
    static func profile(hcpId: String) -> String { "/profile/\(hcpId)" }
    static let detect = "/detect"
    static func summary(drugId: String) -> String { "/drug/\(drugId)/summary" }
    static func ask(drugId: String) -> String { "/drug/\(drugId)/ask" }
    static let engagementLog = "/engagement/log"
}

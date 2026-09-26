//
//  Single source of truth for backend paths.
//
//  Every path here must match its counterpart in backend/app/routes/
//  exactly. If you change one side, change this file and tell the
//  other lane — this is the contract, in one place.
//

import Foundation

enum Endpoints {
    static let login = "/auth/login"
    static let register = "/auth/register"
    static let logout = "/auth/logout"
    static let changePassword = "/auth/change-password"
    static let forgotPassword = "/auth/forgot-password"
    static let resetPassword = "/auth/reset-password"
    static func profile(hcpId: String) -> String { "/profile/\(pathSegment(hcpId))" }
    static func patients(hcpId: String) -> String { "/profile/\(pathSegment(hcpId))/patients" }
    static let syncPatients = "/patients/sync"
    static func patient(_ id: String) -> String { "/patients/\(pathSegment(id))" }
    static func medicationReviews(patientId: String) -> String { "/patients/\(pathSegment(patientId))/medication-reviews" }
    static func medicationReview(patientId: String, reviewId: String) -> String {
        "/patients/\(pathSegment(patientId))/medication-reviews/\(pathSegment(reviewId))"
    }
    static let detect = "/detect"
    static func summary(drugId: String) -> String { "/drug/\(pathSegment(drugId))/summary" }
    static func ask(drugId: String) -> String { "/drug/\(pathSegment(drugId))/ask" }
    static let engagementLog = "/engagement/log"

    static func pathSegment(_ value: String) -> String {
        var allowed = CharacterSet.urlPathAllowed
        allowed.remove(charactersIn: "/")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }

    /// Joins `base` and `path` without turning "/detect" into "%2Fdetect".
    static func url(base: URL, path: String, query: [URLQueryItem] = []) -> URL? {
        guard var components = URLComponents(url: base, resolvingAgainstBaseURL: false) else {
            return nil
        }
        let root = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let extra = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = "/" + [root, extra].filter { !$0.isEmpty }.joined(separator: "/")
        components.queryItems = query.isEmpty ? nil : query
        return components.url
    }
}

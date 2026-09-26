//
//  Backend API client.
//
//  One method per backend endpoint (see Endpoints.swift and
//  backend/app/routes/). Every view should go through this rather than
//  building URLRequests inline, so the contract stays in one place.
//
//  Owned by: whole team — this is the shared contract between iOS and
//  backend lanes. Coordinate before changing a method's signature.
//

import Foundation

enum APIError: LocalizedError, Equatable {
    case notConfigured
    case notFound
    case unauthorized
    case conflict
    case badStatus(Int)
    case serverMessage(String)
    case malformedResponse

    var errorDescription: String? {
        switch self {
        case .notConfigured: "No backend URL is configured."
        case .notFound: "The backend doesn't know about that yet."
        case .unauthorized: "Email or password is incorrect."
        case .conflict: "An account with that email already exists."
        case .badStatus(let code): "The backend returned status \(code)."
        case .serverMessage(let message): message
        case .malformedResponse: "The backend returned something unexpected."
        }
    }

    var requiresReauthentication: Bool {
        switch self {
        case .unauthorized:
            return true
        case .serverMessage(let message):
            let lower = message.lowercased()
            return lower.contains("sign in") || lower.contains("session expired")
        default:
            return false
        }
    }
}

final class APIClient {
    static let shared = APIClient()

    /// Set `LENS_API_BASE_URL` in the target's build settings to point a device
    /// at the laptop's LAN address — a phone can't reach the laptop's loopback.
    static let baseURLInfoKey = "LensAPIBaseURL"

    let baseURL: URL?
    var sessionToken: String?
    private let session: URLSession
    private let decoder = JSONDecoder()

    init(baseURL: URL? = nil, session: URLSession? = nil) {
        self.baseURL = baseURL ?? Self.configuredBaseURL()
        self.session = session ?? Self.makeSession()
    }

    /// Ephemeral + no cache: GET /summary is the personalization loop's read.
    /// URLSession.shared would cache the first "new" HUD and hide the tier jump.
    static func makeSession() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCache = nil
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 20
        configuration.waitsForConnectivity = false
        return URLSession(configuration: configuration)
    }

    static func configuredBaseURL(
        bundle: Bundle = .main,
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) -> URL? {
        let candidates = [
            environment["LENS_API_BASE_URL"],
            bundle.object(forInfoDictionaryKey: baseURLInfoKey) as? String
        ]
        for candidate in candidates {
            guard let trimmed = candidate?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !trimmed.isEmpty,
                  !trimmed.hasPrefix("$("),
                  let url = URL(string: trimmed),
                  let scheme = url.scheme,
                  scheme == "http" || scheme == "https" else { continue }
            return url
        }
        return nil
    }

    /// POST /auth/login
    func login(email: String, password: String) async throws -> AuthSession {
        try await post(Endpoints.login, body: LoginRequest(email: email, password: password), as: AuthSession.self)
    }

    /// POST /auth/register
    func register(_ body: RegisterRequest) async throws -> AuthSession {
        try await post(Endpoints.register, body: body, as: AuthSession.self)
    }

    /// POST /auth/logout
    func logout() async throws {
        _ = try await post(Endpoints.logout, body: EmptyBody(), as: LogoutResponse.self)
    }

    /// POST /auth/change-password
    func changePassword(current: String, new: String) async throws -> AuthSession {
        try await post(
            Endpoints.changePassword,
            body: ChangePasswordRequest(currentPassword: current, newPassword: new),
            as: AuthSession.self
        )
    }

    /// POST /auth/forgot-password
    func requestPasswordReset(email: String, recoveryCode: String) async throws -> PasswordResetStart {
        try await post(
            Endpoints.forgotPassword,
            body: ForgotPasswordRequest(email: email, recoveryCode: recoveryCode),
            as: PasswordResetStart.self
        )
    }

    /// POST /auth/reset-password
    func resetPassword(email: String, resetToken: String, newPassword: String) async throws -> PasswordResetResponse {
        try await post(
            Endpoints.resetPassword,
            body: ResetPasswordRequest(email: email, resetToken: resetToken, newPassword: newPassword),
            as: PasswordResetResponse.self
        )
    }

    /// GET /profile/{hcp_id}
    func getProfile(hcpId: String) async throws -> HCP {
        try await get(Endpoints.profile(hcpId: hcpId), as: HCP.self)
    }

    /// PATCH /profile/{hcp_id}
    func updateProfile(hcpId: String, _ body: ProfileUpdateRequest) async throws -> HCP {
        try await patch(Endpoints.profile(hcpId: hcpId), body: body, as: HCP.self)
    }

    /// GET /profile/{hcp_id}/patients
    func listPatients(hcpId: String) async throws -> [Patient] {
        try await get(Endpoints.patients(hcpId: hcpId), as: PatientListResponse.self).patients
    }

    /// POST /detect
    func detectDrug(barcode: String?, ocrText: String?) async throws -> Drug {
        try await post(
            Endpoints.detect,
            body: DetectRequest(barcode: barcode, ocrText: ocrText),
            as: Drug.self
        )
    }

    /// GET /drug/{drug_id}/summary?hcp_id=
    func getSummary(drugId: String, hcpId: String, patientId: String? = nil) async throws -> DrugSummary {
        var query = [URLQueryItem(name: "hcp_id", value: hcpId)]
        if let patientId, !patientId.isEmpty {
            query.append(URLQueryItem(name: "patient_id", value: patientId))
        }
        return try await get(
            Endpoints.summary(drugId: drugId),
            query: query,
            as: DrugSummary.self,
            timeout: 30
        )
    }

    /// POST /drug/{drug_id}/ask
    func askQuestion(drugId: String, hcpId: String, query: String) async throws -> String {
        try await post(
            Endpoints.ask(drugId: drugId),
            body: AskRequest(hcpId: hcpId, query: query),
            as: AnswerResponse.self
        ).answerText
    }

    /// POST /engagement/log
    @discardableResult
    func logEngagement(hcpId: String, drugId: String, patientId: String? = nil) async throws -> Int {
        try await post(
            Endpoints.engagementLog,
            body: EngagementRequest(hcpId: hcpId, drugId: drugId, patientId: patientId),
            as: EngagementResponse.self
        ).touchCount
    }

    // MARK: - Transport

    func medicationReviews(patientId: String) async throws -> [SavedMedicationReview] {
        try await get(Endpoints.medicationReviews(patientId: patientId), as: MedicationReviewList.self).reviews
    }

    func saveMedicationReview(patientId: String, reviewId: String, draft: MedicationReviewDraft) async throws -> SavedMedicationReview {
        try await sendJSON(
            Endpoints.medicationReview(patientId: patientId, reviewId: reviewId),
            method: "PUT", body: draft, as: SavedMedicationReview.self
        )
    }

    private func get<Response: Decodable>(
        _ path: String,
        query: [URLQueryItem] = [],
        as type: Response.Type,
        timeout: TimeInterval = 15
    ) async throws -> Response {
        var request = URLRequest(url: try url(for: path, query: query), timeoutInterval: timeout)
        request.httpMethod = "GET"
        request.cachePolicy = .reloadIgnoringLocalCacheData
        applyAuth(&request)
        return try await send(request, as: type)
    }

    private func post<Body: Encodable, Response: Decodable>(
        _ path: String,
        query: [URLQueryItem] = [],
        body: Body,
        as type: Response.Type
    ) async throws -> Response {
        try await sendJSON(path, method: "POST", query: query, body: body, as: type)
    }

    private func patch<Body: Encodable, Response: Decodable>(
        _ path: String,
        body: Body,
        as type: Response.Type
    ) async throws -> Response {
        try await sendJSON(path, method: "PATCH", body: body, as: type)
    }

    private func sendJSON<Body: Encodable, Response: Decodable>(
        _ path: String,
        method: String,
        query: [URLQueryItem] = [],
        body: Body,
        as type: Response.Type
    ) async throws -> Response {
        var request = URLRequest(url: try url(for: path, query: query), timeoutInterval: 15)
        request.httpMethod = method
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        applyAuth(&request)
        request.httpBody = try JSONEncoder().encode(body)
        return try await send(request, as: type)
    }

    func clearSession() {
        sessionToken = nil
    }

    private func applyAuth(_ request: inout URLRequest) {
        guard let sessionToken else { return }
        let token = sessionToken.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !token.isEmpty else { return }
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    }

    private func url(for path: String, query: [URLQueryItem] = []) throws -> URL {
        guard let baseURL, let url = Endpoints.url(base: baseURL, path: path, query: query) else {
            throw APIError.notConfigured
        }
        return url
    }

    private func send<Response: Decodable>(
        _ request: URLRequest,
        as type: Response.Type
    ) async throws -> Response {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.malformedResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            throw Self.failure(status: http.statusCode, data: data)
        }
        do {
            return try decoder.decode(type, from: data)
        } catch {
            throw APIError.malformedResponse
        }
    }

    private static func failure(status: Int, data: Data) -> APIError {
        if let detail = serverDetail(data) { return .serverMessage(detail) }
        switch status {
        case 401: return .unauthorized
        case 404: return .notFound
        case 409: return .conflict
        default: return .badStatus(status)
        }
    }

    private static func serverDetail(_ data: Data) -> String? {
        guard
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let detail = object["detail"] as? String,
            !detail.isEmpty
        else { return nil }
        return detail
    }
}

// MARK: - Request/response bodies
//
// Field names must match backend/app/routes/*.py exactly. The shared fixtures
// in backend/tests/contract/ are decoded by both sides to catch drift.

struct EmptyBody: Encodable {}

struct AuthSession: Decodable {
    let profile: HCP
    let sessionToken: String
    let recoveryCode: String?

    enum ExtraKeys: String, CodingKey {
        case sessionToken = "session_token"
        case recoveryCode = "recovery_code"
    }

    init(from decoder: Decoder) throws {
        profile = try HCP(from: decoder)
        let extra = try decoder.container(keyedBy: ExtraKeys.self)
        sessionToken = try extra.decode(String.self, forKey: .sessionToken)
        recoveryCode = try extra.decodeIfPresent(String.self, forKey: .recoveryCode)
    }
}

struct LogoutResponse: Decodable {
    let ok: Bool?
}

struct PasswordResetStart: Decodable {
    let resetToken: String
    let expiresIn: Int
    let detail: String?

    enum CodingKeys: String, CodingKey {
        case resetToken = "reset_token"
        case expiresIn = "expires_in"
        case detail
    }
}

struct PasswordResetResponse: Decodable {
    let ok: Bool?
    let recoveryCode: String?
    let detail: String?

    enum CodingKeys: String, CodingKey {
        case ok, detail
        case recoveryCode = "recovery_code"
    }
}

struct ChangePasswordRequest: Encodable {
    let currentPassword: String
    let newPassword: String

    enum CodingKeys: String, CodingKey {
        case currentPassword = "current_password"
        case newPassword = "new_password"
    }
}

struct ForgotPasswordRequest: Encodable {
    let email: String
    let recoveryCode: String

    enum CodingKeys: String, CodingKey {
        case email
        case recoveryCode = "recovery_code"
    }
}

struct ResetPasswordRequest: Encodable {
    let email: String
    let resetToken: String
    let newPassword: String

    enum CodingKeys: String, CodingKey {
        case email
        case resetToken = "reset_token"
        case newPassword = "new_password"
    }
}

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct RegisterRequest: Encodable {
    var firstName: String
    var lastName: String
    var email: String
    var password: String
    var professionalRole: String
    var specialty: String
    var credentials: String = ""
    var organization: String = ""
    var practiceSetting: String = ""
    var workPhone: String = ""
    var city: String = ""
    var region: String = ""
    var country: String = ""

    enum CodingKeys: String, CodingKey {
        case firstName = "first_name"
        case lastName = "last_name"
        case email, password
        case professionalRole = "professional_role"
        case specialty, credentials, organization
        case practiceSetting = "practice_setting"
        case workPhone = "work_phone"
        case city, region, country
    }
}

struct ProfileUpdateRequest: Encodable {
    var firstName: String
    var lastName: String
    var email: String
    var professionalRole: String
    var specialty: String
    var credentials: String
    var organization: String
    var practiceSetting: String
    var workPhone: String
    var city: String
    var region: String
    var country: String
    var currentPassword: String? = nil

    enum CodingKeys: String, CodingKey {
        case firstName = "first_name"
        case lastName = "last_name"
        case email
        case professionalRole = "professional_role"
        case specialty, credentials, organization
        case practiceSetting = "practice_setting"
        case workPhone = "work_phone"
        case city, region, country
        case currentPassword = "current_password"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(firstName, forKey: .firstName)
        try container.encode(lastName, forKey: .lastName)
        try container.encode(email, forKey: .email)
        try container.encode(professionalRole, forKey: .professionalRole)
        try container.encode(specialty, forKey: .specialty)
        try container.encode(credentials, forKey: .credentials)
        try container.encode(organization, forKey: .organization)
        try container.encode(practiceSetting, forKey: .practiceSetting)
        try container.encode(workPhone, forKey: .workPhone)
        try container.encode(city, forKey: .city)
        try container.encode(region, forKey: .region)
        try container.encode(country, forKey: .country)
        try container.encodeIfPresent(currentPassword, forKey: .currentPassword)
    }
}

struct DetectRequest: Encodable {
    let barcode: String?
    let ocrText: String?

    enum CodingKeys: String, CodingKey {
        case barcode
        case ocrText = "ocr_text"
    }
}

struct AskRequest: Encodable {
    let hcpId: String
    let query: String

    enum CodingKeys: String, CodingKey {
        case hcpId = "hcp_id"
        case query
    }
}

struct EngagementRequest: Encodable {
    let hcpId: String
    let drugId: String
    var patientId: String? = nil

    enum CodingKeys: String, CodingKey {
        case hcpId = "hcp_id"
        case drugId = "drug_id"
        case patientId = "patient_id"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(hcpId, forKey: .hcpId)
        try container.encode(drugId, forKey: .drugId)
        try container.encodeIfPresent(patientId, forKey: .patientId)
    }
}

struct AnswerResponse: Decodable {
    let answerText: String

    enum CodingKeys: String, CodingKey {
        case answerText = "answer_text"
    }
}

struct EngagementResponse: Decodable {
    let touchCount: Int

    enum CodingKeys: String, CodingKey {
        case touchCount = "touch_count"
    }
}

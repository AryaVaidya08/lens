import Foundation

struct Patient: Codable, Identifiable, Equatable, Hashable {
    var id: String
    var hcpId: String
    var firstName: String
    var lastName: String
    var age: Int?
    var weightKg: Double?
    var sex: String
    var medicalHistory: String
    var allergies: String
    var currentMedications: String
    var notes: String
    var source: String?
    var externalId: String?

    var displayName: String {
        "\(firstName) \(lastName)".trimmingCharacters(in: .whitespaces)
    }

    var sourceLabel: String { source ?? "" }
    var recordId: String { externalId ?? "" }

    enum CodingKeys: String, CodingKey {
        case id = "patient_id"
        case hcpId = "hcp_id"
        case firstName = "first_name"
        case lastName = "last_name"
        case age
        case weightKg = "weight_kg"
        case sex
        case medicalHistory = "medical_history"
        case allergies
        case currentMedications = "current_medications"
        case notes
        case source
        case externalId = "external_id"
    }
}

struct PatientListResponse: Decodable {
    let patients: [Patient]
}

struct ClinicSyncResponse: Decodable {
    let imported: Int
    let clinicians: Int
    let patients: [Patient]?
}

//
//  DrugSummary model.
//
//  Matches backend GET /drug/{drug_id}/summary response shape. This is
//  what both HUDView and HUDOverlayView render.
//

import Foundation

struct PatientChartCheck: Codable, Equatable {
    let status: String
    let patientId: String
    let patientName: String
    let headline: String
    let flags: [String]
    let disclaimer: String

    var isFlag: Bool { status == "flag" }

    enum CodingKeys: String, CodingKey {
        case status, headline, flags, disclaimer
        case patientId = "patient_id"
        case patientName = "patient_name"
    }
}

struct AccessPrefill: Codable, Equatable {
    var medication: String
    var strength: String
    var formulation: String
    var directions: String
    var indication: String
}

struct DrugSummary: Codable {
    let drugId: String
    let name: String
    let tier: String
    let headline: String
    let bullets: [String]
    var patientCheck: PatientChartCheck? = nil
    var accessPrefill: AccessPrefill? = nil

    enum CodingKeys: String, CodingKey {
        case drugId = "drug_id"
        case name, tier, headline, bullets
        case patientCheck = "patient_check"
        case accessPrefill = "access_prefill"
    }
}

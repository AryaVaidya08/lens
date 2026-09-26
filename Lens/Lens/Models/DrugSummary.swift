//
//  DrugSummary model.
//
//  Matches backend GET /drug/{drug_id}/summary response shape. This is
//  what both HUDView and HUDOverlayView render.
//

import Foundation

enum ScanSummaryPhase {
    case loading, loaded, offline

    static func resolve(drugId: String, summary: DrugSummary?, failedDrugId: String?) -> Self {
        if summary?.drugId == drugId { return .loaded }
        if failedDrugId == drugId { return .offline }
        return .loading
    }
}

struct PatientChartCheck: Codable, Equatable {
    let status: String
    let patientId: String
    let patientName: String
    let headline: String
    let flags: [String]
    let disclaimer: String

    var isFlag: Bool { status == "flag" }

    var displayFlags: [String] {
        flags.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    var hasConcerns: Bool { !displayFlags.isEmpty }
    var hasNoMatches: Bool { status == "clear" && !hasConcerns }

    enum CodingKeys: String, CodingKey {
        case status, headline, flags, disclaimer
        case patientId = "patient_id"
        case patientName = "patient_name"
    }
}

struct DrugSummary: Codable {
    let drugId: String
    let name: String
    let tier: String
    let headline: String
    let bullets: [String]
    var patientCheck: PatientChartCheck? = nil
    var fullBullets: [String]? = nil

    var expandedBullets: [String] { fullBullets ?? bullets }

    func chartCheck(for patientId: String) -> PatientChartCheck? {
        guard patientCheck?.patientId == patientId else { return nil }
        return patientCheck
    }

    enum CodingKeys: String, CodingKey {
        case drugId = "drug_id"
        case name, tier, headline, bullets
        case patientCheck = "patient_check"
        case fullBullets = "full_bullets"
    }
}

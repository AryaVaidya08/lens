import Foundation

/// Standalone checks that the iOS models encode/decode the same JSON the
/// backend emits, and that URL joining matches the FastAPI paths.
@main
struct ContractChecks {
    static func main() {
        urlJoining()
        baseURLConfig()
        encodeDetectMatchesBackend()
        encodeAskAndEngagement()
        decodeDetect()
        decodeProfile()
        decodeProfileWithoutFamiliarity()
        decodeProfileWithAccountFields()
        decodePatientFolder()
        decodeSummary()
        patientCheckIsolation()
        patientConcernVisibility()
        scanSummaryPhases()
        decodeAsk()
        decodeEngagement()
        rejectStaleCachePolicy()
        print("PASS: API contract encoding, decoding, URL joining, session cache")
    }

    private static func scanSummaryPhases() {
        let summary = DrugSummary(drugId: "a", name: "A", tier: "new", headline: "Live", bullets: [])
        precondition(ScanSummaryPhase.resolve(drugId: "a", summary: nil, failedDrugId: nil) == .loading)
        precondition(ScanSummaryPhase.resolve(drugId: "a", summary: summary, failedDrugId: nil) == .loaded)
        precondition(ScanSummaryPhase.resolve(drugId: "a", summary: nil, failedDrugId: "a") == .offline)
        precondition(ScanSummaryPhase.resolve(drugId: "b", summary: summary, failedDrugId: "a") == .loading)
        precondition(ScanSummaryPhase.resolve(drugId: "a", summary: summary, failedDrugId: "a") == .loaded)
        print("PASS: scan loading, live result, offline fallback, and drug-switch isolation")
    }

    private static func patientConcernVisibility() {
        func check(_ status: String, _ flags: [String]) -> PatientChartCheck {
            PatientChartCheck(status: status, patientId: "patient-a", patientName: "Patient A", headline: "Check result", flags: flags, disclaimer: "Name matching only")
        }
        precondition(check("clear", []).hasNoMatches)
        precondition(!check("clear", []).hasConcerns)
        precondition(check("clear", [" ", "\n"]).hasNoMatches)
        precondition(check("flag", ["Allergy list mentions penicillin."]).hasConcerns)
        precondition(check("flag", ["  Concern  "]).displayFlags == ["Concern"])
        precondition(!check("flag", []).hasNoMatches)
        precondition(!check("unavailable", []).hasNoMatches)
        precondition(check("clear", ["Concern"]).hasConcerns)
        print("PASS: concerns shown, no-match section hidden, unavailable checks retained")
    }

    private static func patientCheckIsolation() {
        var summary = DrugSummary(drugId: "drug-a", name: "Drug A", tier: "new", headline: "General info", bullets: [])
        precondition(summary.chartCheck(for: "patient-a") == nil)
        let check = PatientChartCheck(status: "flag", patientId: "patient-a", patientName: "Patient A", headline: "Review chart", flags: ["Recorded concern"], disclaimer: "Limited chart check")
        summary.patientCheck = check
        precondition(summary.chartCheck(for: "patient-a") == check)
        precondition(summary.chartCheck(for: "patient-b") == nil)
        summary.patientCheck = nil
        precondition(summary.chartCheck(for: "patient-a") == nil)
        print("PASS: patient scan rejects missing and other-patient checks")
    }

    private static func urlJoining() {
        let bases = [
            "http://localhost:8000",
            "http://localhost:8000/",
            "http://10.90.149.89:8000",
            "http://10.90.149.89:8000/"
        ]
        for raw in bases {
            let base = URL(string: raw)!
            let detect = Endpoints.url(base: base, path: Endpoints.detect)
            precondition(detect?.path == "/detect", "detect path from \(raw) was \(detect?.absoluteString ?? "nil")")
            precondition(detect?.absoluteString.hasSuffix("/detect") == true)
            let summary = Endpoints.url(
                base: base,
                path: Endpoints.summary(drugId: "adderall"),
                query: [URLQueryItem(name: "hcp_id", value: "hcp_001")]
            )
            precondition(summary?.path == "/drug/adderall/summary")
            precondition(summary?.query == "hcp_id=hcp_001")
        }
        let ask = Endpoints.url(base: URL(string: "http://localhost:8000")!, path: Endpoints.ask(drugId: "lorazepam"))
        precondition(ask?.absoluteString == "http://localhost:8000/drug/lorazepam/ask")
    }

    private static func baseURLConfig() {
        let fromEnv = APIClient.configuredBaseURL(
            bundle: Bundle(for: BundleProbe.self),
            environment: ["LENS_API_BASE_URL": "http://192.168.1.20:8000"]
        )
        precondition(fromEnv?.absoluteString == "http://192.168.1.20:8000")

        let unexpanded = APIClient.configuredBaseURL(
            bundle: Bundle(for: BundleProbe.self),
            environment: ["LENS_API_BASE_URL": "$(LENS_API_BASE_URL)"]
        )
        precondition(unexpanded == nil, "Unexpanded build settings must not become a base URL")

        let ftp = APIClient.configuredBaseURL(
            bundle: Bundle(for: BundleProbe.self),
            environment: ["LENS_API_BASE_URL": "ftp://example.com"]
        )
        precondition(ftp == nil)

        let blank = APIClient.configuredBaseURL(
            bundle: Bundle(for: BundleProbe.self),
            environment: ["LENS_API_BASE_URL": "   "]
        )
        precondition(blank == nil)
    }

    private static func encodeDetectMatchesBackend() {
        let ocr = jsonObject(DetectRequest(barcode: nil, ocrText: "LORAZEPAM 1 mg tablets"))
        precondition(ocr["ocr_text"] as? String == "LORAZEPAM 1 mg tablets")
        precondition(ocr["barcode"] == nil || ocr["barcode"] is NSNull)
        precondition(ocr["ocrText"] == nil, "must emit ocr_text, not ocrText")

        let barcode = jsonObject(DetectRequest(barcode: "0363323012345", ocrText: nil))
        precondition(barcode["barcode"] as? String == "0363323012345")
        precondition(barcode["ocr_text"] == nil || barcode["ocr_text"] is NSNull)
    }

    private static func encodeAskAndEngagement() {
        let ask = jsonObject(AskRequest(hcpId: "hcp_001", query: "how should I dose this"))
        precondition(ask["hcp_id"] as? String == "hcp_001")
        precondition(ask["query"] as? String == "how should I dose this")
        precondition(ask["hcpId"] == nil)

        let log = jsonObject(EngagementRequest(hcpId: "hcp_001", drugId: "biofreeze"))
        precondition(log["hcp_id"] as? String == "hcp_001")
        precondition(log["drug_id"] as? String == "biofreeze")
        precondition(log["drugId"] == nil)
    }

    private static func jsonObject<T: Encodable>(_ value: T) -> [String: Any] {
        let data = try! JSONEncoder().encode(value)
        return try! JSONSerialization.jsonObject(with: data) as! [String: Any]
    }

    private static func decodeDetect() {
        let drug = try! JSONDecoder().decode(Drug.self, from: Data("""
        {"drug_id":"adderall","name":"Adderall"}
        """.utf8))
        precondition(drug.id == "adderall" && drug.name == "Adderall")
    }

    private static func decodeProfile() {
        let profile = try! JSONDecoder().decode(HCP.self, from: Data("""
        {"hcp_id":"hcp_002","name":"Dr. James Chen","specialty":"Cardiology","familiarity":{"lorazepam":"expert"}}
        """.utf8))
        precondition(profile.id == "hcp_002")
        precondition(profile.familiarity?["lorazepam"] == "expert")
    }

    private static func decodeProfileWithoutFamiliarity() {
        let profile = try! JSONDecoder().decode(HCP.self, from: Data("""
        {"hcp_id":"hcp_001","name":"Dr. Maya Patel","specialty":"Primary Care"}
        """.utf8))
        precondition(profile.id == "hcp_001")
        precondition(profile.familiarity == nil)
        precondition(profile.patientIds == nil)
    }

    private static func decodeProfileWithAccountFields() {
        let profile = try! JSONDecoder().decode(HCP.self, from: Data("""
        {"hcp_id":"hcp_001","name":"Dr. Maya Patel","specialty":"Primary Care","email":"maya.patel@lens.demo","first_name":"Maya","last_name":"Patel","patient_ids":["pat_001"]}
        """.utf8))
        precondition(profile.email == "maya.patel@lens.demo")
        precondition(profile.patientIds == ["pat_001"])
    }

    private static func decodePatientFolder() {
        let patient = try! JSONDecoder().decode(Patient.self, from: Data("""
        {"patient_id":"pat_001","hcp_id":"hcp_001","first_name":"Elena","last_name":"Vasquez","birth_date":"1972-03-14","age":54,"weight_kg":72.5,"sex":"Female","medical_history":"Type 2 diabetes","allergies":"Penicillin","current_medications":"Metformin","notes":""}
        """.utf8))
        precondition(patient.displayName == "Elena Vasquez")
        precondition(patient.weightKg == 72.5)
        precondition(patient.birthDate == "1972-03-14")
    }

    private static func decodeSummary() {
        let summary = try! JSONDecoder().decode(DrugSummary.self, from: Data("""
        {"drug_id":"adderall","name":"Adderall","tier":"new","headline":"CNS stimulant · Schedule II","bullets":["Indicated for ADHD and narcolepsy"]}
        """.utf8))
        precondition(summary.drugId == "adderall" && summary.tier == "new")
        precondition(summary.bullets.count == 1)
        precondition(summary.patientCheck == nil)
        precondition(summary.expandedBullets == summary.bullets)
        let expanded = try! JSONDecoder().decode(DrugSummary.self, from: Data("""
        {"drug_id":"a","name":"A","tier":"new","headline":"Details","bullets":["Preview..."],"full_bullets":["The complete source text."]}
        """.utf8))
        precondition(expanded.expandedBullets == ["The complete source text."])

        let flagged = try! JSONDecoder().decode(DrugSummary.self, from: Data("""
        {"drug_id":"adderall","name":"Adderall","tier":"new","headline":"What it is","bullets":["ADHD"],"patient_check":{"status":"flag","patient_id":"pat_001","patient_name":"Elena Vasquez","headline":"Chart flag","flags":["Allergy list mentions amphetamines."],"disclaimer":"Name match."}}
        """.utf8))
        precondition(flagged.patientCheck?.isFlag == true)
        precondition(flagged.patientCheck?.patientId == "pat_001")
    }

    private static func decodeAsk() {
        let answer = try! JSONDecoder().decode(AnswerResponse.self, from: Data("""
        {"answer_text":"Immediate-release tablets are usually started at 5 mg."}
        """.utf8))
        precondition(answer.answerText.contains("5 mg"))
    }

    private static func decodeEngagement() {
        let log = try! JSONDecoder().decode(EngagementResponse.self, from: Data("""
        {"touch_count":2}
        """.utf8))
        precondition(log.touchCount == 2)
    }

    private static func rejectStaleCachePolicy() {
        let session = APIClient.makeSession()
        precondition(session.configuration.requestCachePolicy == .reloadIgnoringLocalCacheData)
        precondition(session.configuration.urlCache == nil)
        precondition(session.configuration.timeoutIntervalForRequest == 15)
    }
}

private final class BundleProbe: NSObject {}

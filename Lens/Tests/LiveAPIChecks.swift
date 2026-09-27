import Foundation

/// Hits a running backend with the same URLSession stack the app uses.
/// Skipped by the runner when /health isn't up.
@main
struct LiveAPIChecks {
    static func main() async {
        let host = ProcessInfo.processInfo.environment["LENS_API_BASE_URL"]
            ?? "http://127.0.0.1:8000"
        let client = APIClient(baseURL: URL(string: host))
        precondition(client.baseURL != nil)

        do {
            let health = try await getJSON(host + "/health")
            precondition(health["status"] as? String == "ok")
        } catch {
            preconditionFailure("health failed: \(error)")
        }

        do {
            let fromOCR = try await client.detectDrug(barcode: nil, ocrText: "LORAZEPAM 1 mg")
            precondition(fromOCR.id == "lorazepam", "OCR detect: \(fromOCR.id)")
            let fromBarcode = try await client.detectDrug(barcode: "0363-3230-12345", ocrText: nil)
            precondition(fromBarcode.id == "adderall", "formatted barcode: \(fromBarcode.id)")
            let fromAlias = try await client.detectDrug(barcode: nil, ocrText: "Ativan 1mg")
            precondition(fromAlias.id == "lorazepam")
        } catch {
            preconditionFailure("detect failed: \(error)")
        }

        do {
            try await assertThrowsNotFound {
                _ = try await client.detectDrug(barcode: nil, ocrText: "unrelated carton 99")
            }
        } catch {
            preconditionFailure("unknown detect should be notFound: \(error)")
        }

        do {
            let sofia = try await client.login(email: "sofia.ramirez@lens.demo", password: "demo")
            client.sessionToken = sofia.sessionToken
            let first = try await client.getSummary(drugId: "biofreeze", hcpId: "hcp_003")
            precondition(first.drugId == "biofreeze")
            precondition(["new", "returning", "expert"].contains(first.tier))
            precondition(!first.bullets.isEmpty)
            let james = try await client.login(email: "james.chen@lens.demo", password: "demo")
            client.sessionToken = james.sessionToken
            let profile = try await client.getProfile(hcpId: "hcp_002")
            precondition(profile.id == "hcp_002")
            precondition(profile.familiarity?["lorazepam"] == "expert")
            let maya = try await client.login(email: "maya.patel@lens.demo", password: "demo")
            client.sessionToken = maya.sessionToken
            let answer = try await client.askQuestion(
                drugId: "adderall", hcpId: "hcp_001", query: "what are the side effects"
            )
            precondition(!answer.isEmpty)
            precondition(!answer.lowercased().contains("thinking"))
        } catch {
            preconditionFailure("read path failed: \(error)")
        }

        print("PASS: live URLSession client against \(host)")
    }

    private static func assertThrowsNotFound(_ work: () async throws -> Void) async throws {
        do {
            try await work()
            preconditionFailure("expected APIError.notFound")
        } catch APIError.notFound {
            return
        } catch APIError.serverMessage {
            return
        }
    }

    private static func getJSON(_ url: String) async throws -> [String: Any] {
        let (data, response) = try await URLSession.shared.data(from: URL(string: url)!)
        let http = response as! HTTPURLResponse
        precondition(http.statusCode == 200)
        return try JSONSerialization.jsonObject(with: data) as! [String: Any]
    }
}

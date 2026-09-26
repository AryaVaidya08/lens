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

final class APIClient {
    // TODO: implement — base URL should come from a build setting/plist
    // entry, not be hardcoded, so it's easy to point at localhost vs. a
    // deployed instance during the demo.
    static let shared = APIClient()

    /// GET /profile/{hcp_id}
    /// TODO: implement
    func getProfile(hcpId: String) async throws -> HCP {
        // TODO: implement
        fatalError("TODO: implement")
    }

    /// POST /detect
    /// TODO: implement
    func detectDrug(barcode: String?, ocrText: String?) async throws -> Drug {
        // TODO: implement
        fatalError("TODO: implement")
    }

    /// GET /drug/{drug_id}/summary?hcp_id=
    /// TODO: implement
    func getSummary(drugId: String, hcpId: String) async throws -> DrugSummary {
        // TODO: implement
        fatalError("TODO: implement")
    }

    /// POST /drug/{drug_id}/ask
    /// TODO: implement
    func askQuestion(drugId: String, hcpId: String, query: String) async throws -> String {
        // TODO: implement
        fatalError("TODO: implement")
    }

    /// POST /engagement/log
    /// TODO: implement
    func logEngagement(hcpId: String, drugId: String) async throws {
        // TODO: implement
    }
}

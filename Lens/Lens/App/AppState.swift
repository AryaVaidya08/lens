//
//  App-wide observable state.
//
//  Single source of truth for "who is the demo user right now, what
//  drug are they looking at, and how familiar are they with it." Views
//  read/write this instead of passing data through init parameters.
//
//  Owned by: whole team — this is the shared contract between lanes.
//

import Foundation
import Combine

@MainActor
final class AppState: ObservableObject {
    @Published var selectedHCP: HCP? {
        didSet {
            if let selectedHCP {
                defaults.set(selectedHCP.id, forKey: Self.profileCacheKey)
            } else {
                defaults.removeObject(forKey: Self.profileCacheKey)
            }
            if oldValue?.id != selectedHCP?.id {
                currentDrug = nil
                familiarityTier = nil
            }
        }
    }
    @Published var currentDrug: Drug?
    @Published var familiarityTier: String?

    static let profileCacheKey = "lens.selectedHCPID"
    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        let savedID = defaults.string(forKey: Self.profileCacheKey)
        selectedHCP = HCP.demoProfiles.first { $0.id == savedID }
        if selectedHCP == nil {
            defaults.removeObject(forKey: Self.profileCacheKey)
        }
    }

    func logOut() {
        selectedHCP = nil
        currentDrug = nil
        familiarityTier = nil
    }
}

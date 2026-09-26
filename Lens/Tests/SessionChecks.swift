import Foundation

/// Standalone checks runnable with Command Line Tools; no iOS SDK required.
@main
struct SessionChecks {
    @MainActor
    static func main() {
        if CommandLine.arguments.count == 3 {
            persistencePhase(CommandLine.arguments[1], suiteName: CommandLine.arguments[2])
            return
        }
        let suiteName = "lens.session-checks.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let fresh = AppState(defaults: defaults)
        precondition(fresh.selectedHCP == nil, "First launch must show the picker")
        let profile = HCP.demoProfiles[0]
        fresh.selectedHCP = profile
        precondition(defaults.string(forKey: AppState.profileCacheKey) == profile.id)

        let restored = AppState(defaults: defaults)
        precondition(restored.selectedHCP?.id == profile.id, "Relaunch must restore the profile")
        precondition(restored.selectedHCP?.name == profile.name)
        restored.currentDrug = Drug(id: "demo_drug", name: "Demo drug")
        restored.familiarityTier = "expert"
        restored.selectedHCP = HCP.demoProfiles[1]
        precondition(restored.currentDrug == nil && restored.familiarityTier == nil,
                     "Switching profiles must clear the previous HCP's drug context")

        defaults.set("keep me", forKey: "unrelated.preference")
        restored.currentDrug = Drug(id: "demo_drug", name: "Demo drug")
        restored.familiarityTier = "returning"
        restored.logOut()
        precondition(restored.selectedHCP == nil)
        precondition(restored.currentDrug == nil && restored.familiarityTier == nil)
        precondition(defaults.object(forKey: AppState.profileCacheKey) == nil)
        precondition(defaults.string(forKey: "unrelated.preference") == "keep me")
        precondition(AppState(defaults: defaults).selectedHCP == nil,
                     "Logout must survive relaunch")

        defaults.set("deleted-profile", forKey: AppState.profileCacheKey)
        precondition(AppState(defaults: defaults).selectedHCP == nil)
        precondition(defaults.object(forKey: AppState.profileCacheKey) == nil,
                     "Unknown cached profiles must return to the picker")
        defaults.set(42, forKey: AppState.profileCacheKey)
        precondition(AppState(defaults: defaults).selectedHCP == nil)
        defaults.set(["unexpected": "dictionary"], forKey: AppState.profileCacheKey)
        precondition(AppState(defaults: defaults).selectedHCP == nil)
        precondition(defaults.object(forKey: AppState.profileCacheKey) == nil)
        for profile in HCP.demoProfiles {
            let state = AppState(defaults: defaults)
            state.selectedHCP = profile
            let restored = AppState(defaults: UserDefaults(suiteName: suiteName)!)
            precondition(restored.selectedHCP?.id == profile.id)
            precondition(restored.selectedHCP?.specialty == profile.specialty)
            state.logOut()
            state.logOut()
            precondition(AppState(defaults: defaults).selectedHCP == nil)
        }
        print("PASS: profile selection, restoration, switching, logout, stale cache, and unrelated preferences")
    }

    /// The runner invokes these phases in separate processes to check disk persistence.
    @MainActor
    private static func persistencePhase(_ phase: String, suiteName: String) {
        precondition(suiteName.hasPrefix("lens.persistence-checks."))
        let defaults = UserDefaults(suiteName: suiteName)!
        let state = AppState(defaults: defaults)
        switch phase {
        case "save":
            precondition(state.selectedHCP == nil)
            state.selectedHCP = HCP.demoProfiles[2]
            precondition(defaults.synchronize(), "Could not persist test preferences")
        case "restore-and-logout":
            precondition(state.selectedHCP?.id == HCP.demoProfiles[2].id,
                         "A new process must restore the saved profile")
            state.logOut()
            precondition(defaults.synchronize())
        case "verify-logout":
            precondition(state.selectedHCP == nil, "Logout must survive a process restart")
            precondition(defaults.object(forKey: AppState.profileCacheKey) == nil)
        case "cleanup":
            defaults.removePersistentDomain(forName: suiteName)
            defaults.synchronize()
        default:
            preconditionFailure("Unknown persistence phase")
        }
        print("PASS: separate-process profile persistence — \(phase)")
    }
}

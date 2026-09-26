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
        fresh.applySession(profile: profile, token: "tok_session", recoveryCode: "SAVECODE12")
        precondition(fresh.isSignedIn)
        precondition(defaults.string(forKey: AppState.sessionCacheKey) == "tok_session")
        precondition(fresh.pendingRecoveryCode == "SAVECODE12")
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
        precondition(restored.sessionToken == nil)
        precondition(!restored.isSignedIn)
        precondition(restored.pendingRecoveryCode == nil)
        precondition(restored.currentDrug == nil && restored.familiarityTier == nil)
        precondition(defaults.object(forKey: AppState.profileCacheKey) == nil)
        precondition(defaults.object(forKey: AppState.sessionCacheKey) == nil)
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
        historyChecks()
        scanSessionChecks()
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

    @MainActor
    private static func historyChecks() {
        let suiteName = "lens.history-checks.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        var instant = Date(timeIntervalSince1970: 1_700_000_000)
        let state = AppState(defaults: defaults, now: { instant })
        state.selectedHCP = HCP.demoProfiles[0]
        precondition(state.scanHistory.isEmpty)

        let drugA = Drug(id: "drug_a", name: "Drug A")
        let drugB = Drug(id: "drug_b", name: "Drug B")
        state.currentDrug = drugA
        state.currentDrug = drugB
        state.currentDrug = drugA
        precondition(state.scanHistory.isEmpty, "Scanning without asking a question must not be logged")

        state.recordChat(question: "What's the dose?", answer: "Demo reply")
        precondition(state.scanHistory.count == 1)
        precondition(state.scanHistory[0].drugName == "Drug A")
        precondition(state.scanHistory[0].chats.first?.question == "What's the dose?")

        instant += 30
        state.recordChat(question: "Side effects?", answer: "Demo reply 2")
        precondition(state.scanHistory.count == 1, "Follow-up questions on the same drug join the same chat")
        precondition(state.scanHistory[0].chats.count == 2)

        state.currentDrug = drugB
        state.recordChat(question: "What is it?", answer: "Demo reply 3")
        precondition(state.scanHistory.count == 2)
        precondition(state.scanHistory[1].drugName == "Drug B")

        let restored = AppState(defaults: defaults, now: { instant })
        precondition(restored.scanHistory.count == 2)
        precondition(restored.scanHistory[0].chats.last?.answer == "Demo reply 2")

        restored.selectedHCP = HCP.demoProfiles[1]
        precondition(restored.scanHistory.isEmpty, "History is per HCP")
        restored.recordChat(question: "Hello", answer: "Hi")
        precondition(restored.scanHistory.count == 1)
        precondition(restored.scanHistory[0].drugId == nil)
        precondition(restored.scanHistory[0].drugName == "Voice chat")

        restored.logOut()
        precondition(restored.scanHistory.isEmpty)

        let back = AppState(defaults: defaults, now: { instant })
        back.selectedHCP = HCP.demoProfiles[0]
        precondition(back.scanHistory.count == 2, "Logout must not erase another profile's local history")
        back.recordChat(question: "  ", answer: "ignored")
        precondition(back.scanHistory.count == 2 && back.scanHistory.last?.chats.count == 1,
                     "Blank questions must not be stored")

        let legacy = ScanLogEntry(hcpId: "hcp_003", drugId: "adderall", drugName: "Adderall", scannedAt: instant)
        let legacyData = try! JSONEncoder().encode(["hcp_003": [legacy]])
        defaults.set(legacyData, forKey: AppState.historyCacheKey)
        let upgraded = AppState(defaults: defaults, now: { instant })
        upgraded.selectedHCP = HCP.demoProfiles[2]
        precondition(upgraded.scanHistory.isEmpty, "Scan-only entries from older builds are hidden")
    }

    @MainActor
    private static func scanSessionChecks() {
        let suiteName = "lens.scan-session-checks.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let state = AppState(defaults: defaults)
        state.applySession(profile: HCP.demoProfiles[0], token: "tok_scan", recoveryCode: nil)
        let elena = Patient(
            id: "pat_001",
            hcpId: "hcp_001",
            firstName: "Elena",
            lastName: "Vasquez",
            birthDate: "1972-03-14",
            age: 54,
            weightKg: 68,
            sex: "F",
            medicalHistory: "T2DM",
            allergies: "Penicillin, amphetamines",
            currentMedications: "Metformin",
            notes: ""
        )

        state.useForScan(elena)
        precondition(state.selectedPatient?.id == "pat_001")
        precondition(state.scanSessionPatient?.id == "pat_001")
        precondition(state.openScanTab, "Use for scan must jump to the camera tab")

        state.openScanTab = false
        state.finishScanSelection()
        precondition(state.selectedPatient == nil, "Patient is unselected after the scan")
        precondition(state.scanSessionPatient?.id == "pat_001", "HUD can still check this patient's chart")

        state.endScanSession()
        precondition(state.selectedPatient == nil)
        precondition(state.scanSessionPatient == nil)
        precondition(!state.openScanTab)

        state.useForScan(elena)
        state.logOut()
        precondition(state.selectedPatient == nil)
        precondition(state.scanSessionPatient == nil)
        precondition(!state.openScanTab)
    }
}

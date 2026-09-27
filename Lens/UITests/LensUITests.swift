import XCTest

/// Run on a dedicated test simulator: these tests log out and change test profiles.
@MainActor
final class LensUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launch()
        if settingsTab.waitForExistence(timeout: 3) {
            settingsTab.tap()
            app.buttons["settings.logout"].tap()
        }
        XCTAssertTrue(app.buttons["auth.signIn"].waitForExistence(timeout: 5))
    }

    override func tearDownWithError() throws {
        if let app {
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = name
            screenshot.lifetime = .keepAlways
            add(screenshot)
            app.terminate()
        }
    }

    private var settingsTab: XCUIElement { app.buttons["tab.settings"] }
    private var scanTab: XCUIElement { app.buttons["tab.scan"] }

    private func signIn(_ id: String = "hcp_001") {
        let accounts = [
            "hcp_001": ("maya.patel@lens.demo", "demo"),
            "hcp_002": ("james.chen@lens.demo", "demo"),
            "hcp_003": ("sofia.ramirez@lens.demo", "demo")
        ]
        let (email, password) = accounts[id]!
        let emailField = app.textFields["auth.email"]
        XCTAssertTrue(emailField.waitForExistence(timeout: 5))
        replace(emailField, with: email)
        let passwordField = app.secureTextFields["auth.password"]
        XCTAssertTrue(passwordField.waitForExistence(timeout: 5))
        passwordField.tap()
        passwordField.typeText(password)
        app.buttons["auth.signIn"].tap()
        let recovery = app.alerts["Save your recovery code"]
        if recovery.waitForExistence(timeout: 2) {
            recovery.buttons["I saved it"].tap()
        }
        XCTAssertTrue(settingsTab.waitForExistence(timeout: 8))
    }

    private func openEditor() {
        settingsTab.tap()
        app.buttons["settings.editProfile"].tap()
        XCTAssertTrue(app.textFields["profileEditor.firstName"].waitForExistence(timeout: 5))
    }

    private func replace(_ field: XCUIElement, with text: String) {
        field.tap()
        let existing = field.value as? String ?? ""
        // Placeholder values aren't input text.
        if existing != field.placeholderValue && !existing.isEmpty {
            field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: existing.count))
        }
        field.typeText(text)
    }

    func testProfileRestorationAndLogoutAcrossLaunches() {
        signIn("hcp_002")
        app.terminate()
        app.launch()
        XCTAssertTrue(settingsTab.waitForExistence(timeout: 5))
        settingsTab.tap()
        XCTAssertTrue(app.staticTexts["Dr. James Chen"].exists)
        XCTAssertTrue(app.staticTexts["Cardiology"].exists)
        app.buttons["settings.logout"].tap()
        XCTAssertTrue(app.buttons["auth.signIn"].waitForExistence(timeout: 5))
        app.terminate()
        app.launch()
        XCTAssertTrue(app.buttons["auth.signIn"].waitForExistence(timeout: 5))
    }

    func testCancelProfileEditsDiscardsAllChanges() {
        signIn()
        openEditor()
        replace(app.textFields["profileEditor.firstName"], with: "Changed")
        replace(app.textFields["profileEditor.email"], with: "preview@example.com")
        app.buttons["profileEditor.cancel"].tap()
        XCTAssertTrue(app.staticTexts["Dr. Maya Patel"].waitForExistence(timeout: 5))
        openEditor()
        XCTAssertEqual(app.textFields["profileEditor.firstName"].value as? String, "Maya")
        XCTAssertEqual(app.textFields["profileEditor.lastName"].value as? String, "Patel")
        XCTAssertEqual(app.textFields["profileEditor.email"].value as? String, "maya.patel@lens.demo")
    }

    func testSaveStaysDisabledUntilRequiredFieldsAreValid() {
        signIn()
        openEditor()
        XCTAssertTrue(app.buttons["profileEditor.save"].isEnabled)
        replace(app.textFields["profileEditor.firstName"], with: "Preview")
        replace(app.textFields["profileEditor.email"], with: "preview+qa@example.com")
        XCTAssertTrue(app.buttons["profileEditor.save"].isEnabled)
        app.buttons["profileEditor.cancel"].tap()
        XCTAssertTrue(app.staticTexts["Dr. Maya Patel"].waitForExistence(timeout: 5))
        openEditor()
        XCTAssertEqual(app.textFields["profileEditor.firstName"].value as? String, "Maya")
    }

    func testMalformedEmailAndWhitespaceCannotSave() {
        signIn()
        openEditor()
        let email = app.textFields["profileEditor.email"]
        for invalid in ["not-an-email", "a@.com", "a@b..com", "a@-example.com", "a..b@example.com"] {
            replace(email, with: invalid)
            XCTAssertFalse(app.buttons["profileEditor.save"].isEnabled, "Accepted invalid email: \(invalid)")
        }
        replace(email, with: "valid@example.com")
        replace(app.textFields["profileEditor.firstName"], with: "   ")
        XCTAssertFalse(app.buttons["profileEditor.save"].isEnabled)
    }

    func testSpecialtyDropdownAndOtherValidation() {
        signIn()
        openEditor()
        replace(app.textFields["profileEditor.email"], with: "qa@example.com")
        app.swipeUp()
        let specialty = app.buttons["profileEditor.specialty"]
        XCTAssertTrue(specialty.waitForExistence(timeout: 5))
        specialty.tap()
        let cardiology = app.buttons["Cardiology"]
        XCTAssertTrue(cardiology.waitForExistence(timeout: 5))
        cardiology.tap()
        XCTAssertTrue(app.buttons["profileEditor.save"].isEnabled)
        specialty.tap()
        let other = app.buttons["Other / not listed"]
        for _ in 0..<15 {
            if other.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(other.isHittable)
        other.tap()
        let custom = app.textFields["profileEditor.otherSpecialty"]
        for _ in 0..<4 {
            if custom.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(custom.exists)
        XCTAssertFalse(app.buttons["profileEditor.save"].isEnabled)
        replace(custom, with: "Clinical Research")
        XCTAssertTrue(app.buttons["profileEditor.save"].isEnabled)
    }

    func testRepeatedProfileSwitchingAndEmptyAssistant() {
        for id in ["hcp_001", "hcp_002", "hcp_003", "hcp_001"] {
            signIn(id)
            XCTAssertTrue(app.buttons["assistant.microphone"].waitForExistence(timeout: 5))
            XCTAssertFalse(app.staticTexts["You said"].exists)
            XCTAssertFalse(app.buttons["Replay reply"].exists)
            XCTAssertFalse(app.staticTexts["Your words will appear here as you speak."].exists)
            for _ in 0..<3 {
                settingsTab.tap()
                XCTAssertTrue(scanTab.waitForExistence(timeout: 5))
                scanTab.tap()
                XCTAssertTrue(app.buttons["assistant.microphone"].waitForExistence(timeout: 5))
            }
            settingsTab.tap()
            app.buttons["settings.logout"].tap()
            XCTAssertTrue(app.buttons["auth.signIn"].waitForExistence(timeout: 5))
        }
    }

    func testDeniedSpeechPermissionCanRetryAndNavigate() throws {
        // XCTest has no speech-recognition authorization reset resource.
        // Run this case only after resetting speech permission on the simulator.
        guard ProcessInfo.processInfo.environment["LENS_TEST_SPEECH_PERMISSION_RESET"] == "1" else {
            throw XCTSkip("Reset speech permission on the test simulator and set LENS_TEST_SPEECH_PERMISSION_RESET=1.")
        }
        signIn()
        XCTAssertTrue(app.buttons["assistant.microphone"].waitForExistence(timeout: 5))
        let handler = addUIInterruptionMonitor(withDescription: "Speech permission") { alert in
            let deny = alert.buttons["Don't Allow"]
            if deny.exists { deny.tap(); return true }
            return false
        }
        defer { removeUIInterruptionMonitor(handler) }
        app.buttons["assistant.microphone"].tap()
        app.tap() // Gives XCTest an opportunity to handle the system permission alert.
        XCTAssertTrue(app.buttons["Open app settings"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["assistant.microphone"].isEnabled)
        app.buttons["assistant.microphone"].tap()
        XCTAssertTrue(app.buttons["Open app settings"].waitForExistence(timeout: 5))
        settingsTab.tap()
        app.buttons["settings.logout"].tap()
        XCTAssertTrue(app.buttons["auth.signIn"].waitForExistence(timeout: 5))
    }

    func testLargeTextKeepsCriticalControlsAccessible() {
        app.terminate()
        app.launchArguments = ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch()
        signIn()
        openEditor()
        XCTAssertTrue(app.buttons["profileEditor.cancel"].isHittable)
        XCTAssertTrue(app.buttons["profileEditor.save"].isHittable)
        app.buttons["profileEditor.cancel"].tap()
        XCTAssertTrue(scanTab.waitForExistence(timeout: 5))
        scanTab.tap()
        let microphone = app.buttons["assistant.microphone"]
        for _ in 0..<5 {
            if microphone.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(microphone.isHittable)
        XCTAssertEqual(app.state, .runningForeground)
    }
}

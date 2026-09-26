import XCTest

@MainActor
final class MedicationAccessUITests: XCTestCase {
    func testDraftSaveReopenAndMissingDocumentation() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchEnvironment["LENS_API_BASE_URL"] = "http://127.0.0.1:8001"
        app.launch()
        defer { app.terminate() }
        if app.buttons["tab.settings"].waitForExistence(timeout: 3) {
            app.buttons["tab.settings"].tap()
            app.buttons["settings.logout"].tap()
        }
        XCTAssertTrue(app.buttons["auth.demoSignIn"].waitForExistence(timeout: 5))
        app.buttons["auth.demoSignIn"].tap()
        let recovery = app.alerts["Save your recovery code"]
        if recovery.waitForExistence(timeout: 2) { recovery.buttons["I saved it"].tap() }
        XCTAssertTrue(app.buttons["tab.patients"].waitForExistence(timeout: 10))
        app.buttons["tab.patients"].tap()
        XCTAssertTrue(app.buttons["patient.pat_001"].waitForExistence(timeout: 10))
        app.buttons["patient.pat_001"].tap()
        app.buttons["patient.medicationAccess"].tap()
        XCTAssertTrue(app.buttons["access.start"].waitForExistence(timeout: 10))
        app.buttons["access.start"].tap()
        let name = "QA Access " + UUID().uuidString.prefix(6)
        let medication = app.textFields["access.medication"]
        XCTAssertTrue(medication.waitForExistence(timeout: 5))
        medication.tap()
        medication.typeText(name)
        app.buttons["access.save"].tap()
        let saved = app.staticTexts["access.savedState"]
        for _ in 0..<20 {
            if saved.exists { break }
            app.swipeUp()
        }
        XCTAssertTrue(saved.waitForExistence(timeout: 10))
        app.buttons["access.close"].tap()
        let caseName = app.staticTexts[name]
        XCTAssertTrue(caseName.waitForExistence(timeout: 10))
        caseName.tap()
        XCTAssertTrue(medication.waitForExistence(timeout: 5))
        XCTAssertEqual(medication.value as? String, name)
        let ready = app.buttons["access.status.ready"]
        for _ in 0..<20 {
            if ready.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(ready.exists)
        XCTAssertFalse(ready.isEnabled)
        XCTAssertTrue(app.buttons["access.export"].exists)
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "Access case documentation gaps"
        shot.lifetime = .keepAlways
        add(shot)
    }
}

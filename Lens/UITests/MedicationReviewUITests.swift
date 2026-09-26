import XCTest

/// Run against the isolated mock backend on port 8001; never uses Atlas.
@MainActor
final class MedicationReviewUITests: XCTestCase {
    func testMedicationReviewSaveCompareAndReopen() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchEnvironment["LENS_API_BASE_URL"] = "http://127.0.0.1:8001"
        app.launch()
        defer {
            let attachment = XCTAttachment(screenshot: app.screenshot())
            attachment.lifetime = .keepAlways
            add(attachment)
            app.terminate()
        }
        if app.buttons["tab.settings"].waitForExistence(timeout: 3) {
            app.buttons["tab.settings"].tap()
            app.buttons["settings.logout"].tap()
        }
        XCTAssertTrue(app.textFields["auth.email"].waitForExistence(timeout: 5))
        app.textFields["auth.email"].tap()
        app.textFields["auth.email"].typeText("maya.patel@lens.demo")
        app.secureTextFields["auth.password"].tap()
        app.secureTextFields["auth.password"].typeText("demo")
        app.buttons["auth.signIn"].tap()
        let recovery = app.alerts["Save your recovery code"]
        if recovery.waitForExistence(timeout: 2) { recovery.buttons["I saved it"].tap() }
        XCTAssertTrue(app.buttons["tab.patients"].waitForExistence(timeout: 10))
        app.buttons["tab.patients"].tap()
        XCTAssertTrue(app.buttons["patient.pat_001"].waitForExistence(timeout: 10))
        app.buttons["patient.pat_001"].tap()
        app.buttons["patient.medicationReviews"].tap()
        XCTAssertTrue(app.buttons["review.start"].waitForExistence(timeout: 5))
        app.buttons["review.start"].tap()
        app.buttons["review.addReference"].tap()
        fillMedication(app, strength: "5 mg")
        reveal(app.switches["review.referenceVerified"], in: app)
        app.switches["review.referenceVerified"].tap()
        app.buttons["review.saveDraft"].tap()
        reveal(app.staticTexts["review.draftSaved"], in: app)
        XCTAssertTrue(app.staticTexts["review.draftSaved"].exists)
        app.buttons["review.close"].tap()
        XCTAssertTrue(app.buttons["review.saved"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["review.saved"].firstMatch.tap()
        reveal(app.buttons["review.addBottle"], in: app)
        app.buttons["review.addBottle"].tap()
        fillMedication(app, strength: "10 mg")
        reveal(app.switches["review.collectionComplete"], in: app)
        app.switches["review.collectionComplete"].tap()
        reveal(app.buttons["review.compare"], in: app)
        XCTAssertTrue(app.buttons["review.compare"].isEnabled)
        app.buttons["review.compare"].tap()
        reveal(app.staticTexts["Strength text differs"], in: app)
        XCTAssertTrue(app.staticTexts["Strength text differs"].exists)
        reveal(app.buttons["review.share"], in: app)
        XCTAssertTrue(app.buttons["review.share"].isEnabled)
        let report = XCTAttachment(screenshot: app.screenshot())
        report.name = "Medication discrepancy report"
        report.lifetime = .keepAlways
        add(report)
        app.buttons["review.share"].tap()
        XCTAssertTrue(app.buttons["Copy"].waitForExistence(timeout: 5))
        app.buttons["Copy"].tap()
        app.buttons["review.close"].tap()
        XCTAssertTrue(app.buttons["review.saved"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["review.saved"].firstMatch.tap()
        reveal(app.staticTexts["Strength text differs"], in: app)
        XCTAssertTrue(app.staticTexts["Strength text differs"].exists)
        app.buttons["review.close"].tap()
    }

    private func fillMedication(_ app: XCUIApplication, strength: String) {
        XCTAssertFalse(app.buttons["medication.save"].isEnabled)
        let fields = [("medication.name", "Examplemed"), ("medication.strength", strength),
                      ("medication.formulation", "tablet"), ("medication.directions", "Take one daily")]
        for (identifier, value) in fields {
            let field = app.descendants(matching: .any).matching(identifier: identifier).firstMatch
            reveal(field, in: app)
            field.tap()
            field.typeText(value)
        }
        let confirm = app.switches["medication.confirmed"]
        reveal(confirm, in: app)
        confirm.tap()
        XCTAssertTrue(app.buttons["medication.save"].isEnabled)
        app.buttons["medication.save"].tap()
    }

    private func reveal(_ element: XCUIElement, in app: XCUIApplication) {
        for _ in 0..<10 {
            if element.isHittable { return }
            app.swipeUp()
        }
        XCTAssertTrue(element.isHittable)
    }
}

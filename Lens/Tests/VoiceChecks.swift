import Foundation

@MainActor
private final class FakeSpeechDriver: SpeechRecognitionDriving {
    var permission: SpeechPermission = .authorized
    var microphoneAllowed = true
    var speechRequests = 0
    var microphoneRequests = 0
    var starts = 0
    var stops = 0
    var cancellations = 0
    var permissionGate: CheckedContinuation<SpeechPermission, Never>?
    var microphoneGate: CheckedContinuation<Bool, Never>?
    var deferSpeechPermission = false
    var deferMicrophonePermission = false
    var failStart = false
    var immediateResult: SpeechUpdate?
    var resultOnStop: SpeechUpdate?
    var callbacks: [@MainActor (SpeechUpdate) -> Void] = []

    enum Failure: LocalizedError {
        case noInput
        var errorDescription: String? { "No microphone available for this test." }
    }

    func requestSpeechPermission() async -> SpeechPermission {
        speechRequests += 1
        if deferSpeechPermission {
            return await withCheckedContinuation { permissionGate = $0 }
        }
        return permission
    }
    func requestMicrophonePermission() async -> Bool {
        microphoneRequests += 1
        if deferMicrophonePermission {
            return await withCheckedContinuation { microphoneGate = $0 }
        }
        return microphoneAllowed
    }
    func start(onUpdate: @escaping @MainActor (SpeechUpdate) -> Void) throws {
        starts += 1
        callbacks.append(onUpdate)
        if failStart { throw Failure.noInput }
        if let immediateResult { onUpdate(immediateResult) }
    }
    func finishAudio() {
        stops += 1
        if let resultOnStop { callbacks.last?(resultOnStop) }
    }
    func cancel() { cancellations += 1 }
    func emit(_ text: String? = nil, final: Bool = false, failed: Bool = false, index: Int? = nil) {
        callbacks[index ?? (callbacks.count - 1)](SpeechUpdate(text: text, isFinal: final, failed: failed))
    }
}

@MainActor
private final class ManualClock {
    var waits: [(Duration, CheckedContinuation<Void, any Error>)] = []
    func sleep(_ duration: Duration) async throws {
        try await withCheckedThrowingContinuation { waits.append((duration, $0)) }
    }
    func contains(_ duration: Duration) -> Bool { waits.contains { $0.0 == duration } }
    func fire(_ duration: Duration) {
        let ready = waits.filter { $0.0 == duration }
        waits.removeAll { $0.0 == duration }
        ready.forEach { $0.1.resume() }
    }
    func drain() {
        let remaining = waits
        waits = []
        remaining.forEach { $0.1.resume(throwing: CancellationError()) }
    }
}

@MainActor
private final class Fixture {
    let driver = FakeSpeechDriver()
    let clock = ManualClock()
    let recognizer: SpeechRecognizer
    var replies: [String] = []
    init() {
        let clock = clock
        recognizer = SpeechRecognizer(driver: driver, sleep: { try await clock.sleep($0) })
    }
    func start() { recognizer.startListening { [weak self] in self?.replies.append($0) } }
    func listening() async {
        start()
        await eventually { self.recognizer.state == .listening }
    }
    func close() async {
        recognizer.cancel()
        driver.permissionGate?.resume(returning: .authorized)
        driver.permissionGate = nil
        driver.microphoneGate?.resume(returning: true)
        driver.microphoneGate = nil
        // Let newly scheduled timer tasks enter the clock before draining them.
        for _ in 0..<10 { await Task.yield() }
        clock.drain()
    }
}

@MainActor
private func eventually(_ condition: @escaping @MainActor () -> Bool,
                        file: StaticString = #file, line: UInt = #line) async {
    let deadline = ContinuousClock.now + .seconds(3)
    while !condition() && ContinuousClock.now < deadline {
        try? await Task.sleep(for: .milliseconds(1))
    }
    precondition(condition(), "Timed out waiting for expected state", file: file, line: line)
}

@main
struct VoiceChecks {
    @MainActor
    static func main() async {
        var count = 0
        func run(_ name: String, _ body: @MainActor (Fixture) async -> Void) async {
            let fixture = Fixture()
            await body(fixture)
            await fixture.close()
            count += 1
            print("PASS: \(name)")
        }

        await run("denied speech permission never starts microphone") { f in
            f.driver.permission = .denied
            f.start()
            await eventually { f.recognizer.state == .idle }
            precondition(f.recognizer.needsSettings && f.recognizer.errorMessage != nil)
            precondition(f.driver.microphoneRequests == 0 && f.driver.starts == 0)
        }
        await run("restricted speech permission does not suggest an ineffective Settings fix") { f in
            f.driver.permission = .restricted
            f.start()
            await eventually { f.recognizer.state == .idle }
            precondition(!f.recognizer.needsSettings && f.recognizer.errorMessage != nil)
        }
        await run("denied microphone permission never records") { f in
            f.driver.microphoneAllowed = false
            f.start()
            await eventually { f.recognizer.state == .idle }
            precondition(f.recognizer.needsSettings && f.driver.starts == 0 && f.replies.isEmpty)
        }
        await run("immediate cancellation avoids even requesting permission") { f in
            f.start()
            f.recognizer.cancel()
            for _ in 0..<10 { await Task.yield() }
            precondition(f.driver.speechRequests == 0 && f.driver.starts == 0)
        }
        await run("cancellation during speech permission ignores late approval") { f in
            f.driver.deferSpeechPermission = true
            f.start()
            await eventually { f.driver.permissionGate != nil }
            f.recognizer.cancel()
            f.driver.permissionGate?.resume(returning: .authorized)
            f.driver.permissionGate = nil
            for _ in 0..<10 { await Task.yield() }
            precondition(f.recognizer.state == .idle && f.driver.microphoneRequests == 0)
        }
        await run("cancellation during microphone permission ignores late approval") { f in
            f.driver.deferMicrophonePermission = true
            f.start()
            await eventually { f.driver.microphoneGate != nil }
            f.recognizer.cancel()
            f.driver.microphoneGate?.resume(returning: true)
            f.driver.microphoneGate = nil
            for _ in 0..<10 { await Task.yield() }
            precondition(f.recognizer.state == .idle && f.driver.starts == 0)
        }
        await run("partial transcript is visible but does not submit") { f in
            await f.listening()
            f.driver.emit("What is the dose")
            precondition(f.recognizer.transcript == "What is the dose" && f.replies.isEmpty)
            precondition(f.recognizer.state == .listening)
        }
        await run("final result submits exactly once and releases recording") { f in
            await f.listening()
            let before = f.driver.cancellations
            f.driver.emit("  Hello there  \n", final: true)
            f.driver.emit("duplicate", final: true)
            precondition(f.replies == ["Hello there"] && f.recognizer.state == .idle)
            precondition(f.driver.cancellations == before + 1)
        }
        await run("Finish waits for final words instead of submitting a partial") { f in
            await f.listening()
            f.driver.emit("Hello")
            f.recognizer.stopListening()
            precondition(f.recognizer.state == .finishing && f.replies.isEmpty && f.driver.stops == 1)
            f.driver.emit("Hello world", final: true)
            precondition(f.replies == ["Hello world"])
        }
        await run("silent recognition reports a retry and never speaks") { f in
            await f.listening()
            f.driver.emit(" \n ", final: true)
            precondition(f.recognizer.state == .idle && f.recognizer.errorMessage != nil && f.replies.isEmpty)
        }
        await run("recognition error clears the recording without a reply") { f in
            await f.listening()
            f.driver.emit("partial", failed: true)
            precondition(f.recognizer.state == .idle && f.recognizer.errorMessage != nil && f.replies.isEmpty)
        }
        await run("microphone startup failure releases resources and retains useful error") { f in
            f.driver.failStart = true
            f.start()
            await eventually { f.recognizer.state == .idle }
            precondition(f.recognizer.errorMessage == "No microphone available for this test.")
            precondition(f.driver.cancellations >= 2 && f.replies.isEmpty)
        }
        await run("cancelled session cannot reply or overwrite the next session") { f in
            await f.listening()
            f.recognizer.cancel()
            await f.listening()
            f.driver.emit("stale", final: true, index: 0)
            precondition(f.recognizer.transcript.isEmpty && f.recognizer.state == .listening && f.replies.isEmpty)
            f.driver.emit("current", final: true)
            precondition(f.replies == ["current"])
        }
        await run("restart replaces active session and rejects its late callbacks") { f in
            await f.listening()
            await f.listening()
            f.driver.emit("stale error", failed: true, index: 0)
            precondition(f.recognizer.errorMessage == nil && f.recognizer.state == .listening)
            f.driver.emit("new", final: true)
            precondition(f.replies == ["new"])
        }
        await run("permission retry clears stale errors and Settings prompt") { f in
            f.driver.permission = .denied
            f.start()
            await eventually { f.recognizer.state == .idle }
            f.driver.permission = .authorized
            await f.listening()
            precondition(!f.recognizer.needsSettings && f.recognizer.errorMessage == nil)
        }
        await run("45-second recording limit ends input") { f in
            await f.listening()
            await eventually { f.clock.contains(.seconds(45)) }
            f.clock.fire(.seconds(45))
            await eventually { f.recognizer.state == .finishing }
            precondition(f.driver.stops == 1)
        }
        await run("finalization timeout submits latest transcript once") { f in
            await f.listening()
            f.driver.emit("Latest words")
            f.recognizer.stopListening()
            await eventually { f.clock.contains(.seconds(3)) }
            f.clock.fire(.seconds(3))
            await eventually { f.recognizer.state == .idle }
            f.driver.emit("too late", final: true)
            precondition(f.replies == ["Latest words"])
        }
        await run("silent finalization timeout returns useful error") { f in
            await f.listening()
            f.recognizer.stopListening()
            await eventually { f.clock.contains(.seconds(3)) }
            f.clock.fire(.seconds(3))
            await eventually { f.recognizer.state == .idle }
            precondition(f.recognizer.errorMessage != nil && f.replies.isEmpty)
        }
        await run("cancel during finalization prevents timeout reply") { f in
            await f.listening()
            f.driver.emit("Do not reply")
            f.recognizer.stopListening()
            await eventually { f.clock.contains(.seconds(3)) }
            f.recognizer.cancel()
            f.clock.fire(.seconds(3))
            for _ in 0..<10 { await Task.yield() }
            precondition(f.recognizer.state == .idle && f.replies.isEmpty)
        }
        await run("immediate final result during start cannot revive recording") { f in
            f.driver.immediateResult = SpeechUpdate(text: "Immediate", isFinal: true, failed: false)
            f.start()
            await eventually { f.recognizer.state == .idle }
            precondition(f.replies == ["Immediate"] && f.clock.waits.isEmpty)
        }
        await run("final result during Finish cannot schedule a stale timer") { f in
            await f.listening()
            f.driver.resultOnStop = SpeechUpdate(text: "Complete", isFinal: true, failed: false)
            f.recognizer.stopListening()
            precondition(f.recognizer.state == .idle && f.replies == ["Complete"])
            precondition(!f.clock.contains(.seconds(3)))
        }
        await run("error after Finish preserves captured words and replies once") { f in
            await f.listening()
            f.driver.emit("What did you hear")
            f.recognizer.stopListening()
            f.driver.emit(failed: true)
            f.driver.emit("late duplicate", final: true)
            precondition(f.replies == ["What did you hear"])
            precondition(f.recognizer.state == .idle && f.recognizer.errorMessage == nil)
        }
        await run("empty final update does not erase words captured before Finish") { f in
            await f.listening()
            f.driver.emit("Keep these words")
            f.recognizer.stopListening()
            f.driver.emit("", final: true)
            precondition(f.replies == ["Keep these words"])
        }
        await run("error after silent Finish remains an error without a reply") { f in
            await f.listening()
            f.recognizer.stopListening()
            f.driver.emit(failed: true)
            precondition(f.replies.isEmpty && f.recognizer.errorMessage != nil)
        }
        await run("cancelled Finish never replies to a late error") { f in
            await f.listening()
            f.driver.emit("Do not submit this")
            f.recognizer.stopListening()
            f.recognizer.cancel()
            f.driver.emit(failed: true)
            precondition(f.replies.isEmpty && f.recognizer.errorMessage == nil)
        }
        await run("100 repeated recordings recover after finalization errors") { f in
            for index in 0..<100 {
                await f.listening()
                f.driver.emit("Question \(index)")
                f.recognizer.stopListening()
                f.recognizer.stopListening()
                f.driver.emit(failed: true)
                f.driver.emit("late", final: true)
                precondition(f.replies.count == index + 1)
                precondition(f.replies.last == "Question \(index)")
                precondition(f.recognizer.state == .idle)
                f.clock.drain()
            }
        }
        let question = "What did you hear?"
        let reply = PlaceholderAssistant.reply(to: question, drug: nil)
        precondition(reply.contains(question) && reply.contains("demo reply"))
        precondition(Set(DemoDrugCatalog.all.map(\.id)) == ["adderall", "biofreeze", "lorazepam", "xyzal", "claritin"])
        for demo in DemoDrugCatalog.all {
            precondition(DemoDrugCatalog.resolve(payload: "text: \(demo.name.uppercased()) 10 MG")?.id == demo.id)
            precondition(DemoDrugCatalog.resolve(payload: demo.barcode)?.id == demo.id,
                         "Exact barcode match must resolve \(demo.name)")
            precondition(Set(demo.answers.keys) == Set(DemoDrug.Topic.allCases))
            let dosing = PlaceholderAssistant.reply(to: "What's the dose?", drug: demo.drug)
            precondition(dosing.contains("Grok"))
            precondition(!dosing.contains(demo.answers[.dosing]!))
            let sideEffects = PlaceholderAssistant.reply(to: "Any side effects?", drug: demo.drug)
            precondition(!sideEffects.contains(demo.answers[.sideEffects]!))
            let overview = PlaceholderAssistant.reply(to: "Tell me about it", drug: demo.drug)
            precondition(overview.contains("Grok"))
            precondition(!overview.contains(demo.headline))
        }
        precondition(DemoDrugCatalog.resolve(payload: "barcode: 0123456789") == nil,
                     "Unrecognized payloads must not resolve to any demo drug")
        print("PASS: demo replies for Adderall, Biofreeze, Lorazepam, Xyzal, and Claritin; exact barcode/text matching")
        print("PASS: \(count + 1) voice regression cases")
    }
}

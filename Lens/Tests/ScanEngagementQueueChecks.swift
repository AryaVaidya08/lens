import Foundation

@main
struct ScanEngagementQueueChecks {
    @MainActor static func main() async throws {
        let queue = ScanEngagementQueue()
        precondition(queue.startsNewScan(hcpId: "hcp", drugId: "drug"))
        for _ in 0..<500 {
            precondition(!queue.startsNewScan(hcpId: "hcp", drugId: "drug"), "Continuous sightings of the same bottle must not advance familiarity")
        }
        queue.noteTrackingLost()
        precondition(queue.startsNewScan(hcpId: "hcp", drugId: "drug"), "A new sighting after the bottle leaves view should advance familiarity")
        precondition(!queue.startsNewScan(hcpId: "hcp", drugId: "drug"))
        queue.noteTrackingLost()
        queue.keepCurrentSighting(hcpId: "hcp", drugId: "drug")
        precondition(!queue.startsNewScan(hcpId: "hcp", drugId: "drug"), "Returning during an in-flight scan must not log another touch")
        precondition(queue.startsNewScan(hcpId: "hcp", drugId: "other-drug"))
        precondition(queue.startsNewScan(hcpId: "other-hcp", drugId: "other-drug"))
        var touches = 0
        var writeStarted = false
        var release: CheckedContinuation<Void, Never>?
        let first = Task {
            try await queue.record(hcpId: "hcp", drugId: "drug") {
                writeStarted = true
                await withCheckedContinuation { release = $0 }
                touches += 1
                return touches
            }
        }
        for _ in 0..<100 where !writeStarted { await Task.yield() }
        precondition(writeStarted && queue.isRecording)

        var nextRead: Int?
        let next = Task {
            await queue.wait(hcpId: "hcp", drugId: "drug")
            nextRead = touches
        }
        let duplicate = Task {
            try await queue.record(hcpId: "hcp", drugId: "drug") {
                preconditionFailure("An overlapping tracking update must not write another touch")
            }
        }
        for _ in 0..<100 { await Task.yield() }
        precondition(nextRead == nil, "A rescan must wait for the previous touch to finish")
        release?.resume()
        let firstCount = try await first.value
        let duplicateCount = try await duplicate.value
        await next.value
        precondition(firstCount == 1 && duplicateCount == 1 && nextRead == 1)
        precondition(touches == 1 && !queue.isRecording)

        // The next deliberate scan reads the prior count, then records once.
        var priorCounts = [0, nextRead!]
        _ = try await queue.record(hcpId: "hcp", drugId: "drug") { touches += 1; return touches }
        await queue.wait(hcpId: "hcp", drugId: "drug")
        priorCounts.append(touches)
        precondition(priorCounts == [0, 1, 2], "Summary reads should progress new -> returning -> expert")

        enum Failure: Error { case offline }
        do {
            _ = try await queue.record(hcpId: "hcp", drugId: "drug") { throw Failure.offline }
            preconditionFailure("Write failures must reach the UI")
        } catch Failure.offline {}
        precondition(!queue.isRecording, "A failed write must not permanently disable Scan again")
        await queue.wait(hcpId: "hcp", drugId: "drug")
        let recovered = try await queue.record(hcpId: "hcp", drugId: "drug") { touches += 1; return touches }
        precondition(recovered == 3)
        print("PASS: repeat-scan ordering, overlapping writes, familiarity counts, failure, and recovery")
    }
}

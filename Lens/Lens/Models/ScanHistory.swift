import Foundation

struct ChatTurn: Codable, Identifiable, Equatable {
    let id: UUID
    let askedAt: Date
    let question: String
    let answer: String

    init(id: UUID = UUID(), askedAt: Date, question: String, answer: String) {
        self.id = id
        self.askedAt = askedAt
        self.question = question
        self.answer = answer
    }
}

/// One local scan (or voice-only session) and the assistant turns that followed.
/// Stored on-device until a history API exists.
struct ScanLogEntry: Codable, Identifiable, Equatable {
    let id: UUID
    let hcpId: String
    let drugId: String?
    let drugName: String
    let scannedAt: Date
    var chats: [ChatTurn]

    init(
        id: UUID = UUID(),
        hcpId: String,
        drugId: String?,
        drugName: String,
        scannedAt: Date,
        chats: [ChatTurn] = []
    ) {
        self.id = id
        self.hcpId = hcpId
        self.drugId = drugId
        self.drugName = drugName
        self.scannedAt = scannedAt
        self.chats = chats
    }

    var title: String {
        drugName.isEmpty ? "Voice chat" : drugName
    }
}

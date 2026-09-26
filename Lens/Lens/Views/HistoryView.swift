import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        NavigationStack {
            Group {
                if appState.scanHistory.isEmpty {
                    ContentUnavailableView(
                        "No chats yet",
                        systemImage: "clock.arrow.circlepath",
                        description: Text("Questions you ask the assistant will show up here. History is saved on this device until a backend log exists.")
                    )
                    .accessibilityIdentifier("history.empty")
                } else {
                    List {
                        Section {
                            ForEach(appState.scanHistory.reversed()) { entry in
                                NavigationLink {
                                    HistoryDetailView(entryID: entry.id)
                                } label: {
                                    HistoryRow(entry: entry)
                                }
                                .accessibilityIdentifier("history.entry.\(entry.id.uuidString)")
                            }
                        } footer: {
                            Text("Saved on this iPhone. A shared history API is not connected yet.")
                        }
                    }
                    .accessibilityIdentifier("history.list")
                }
            }
            .contentMargins(.top, 8, for: .scrollContent)
            .tabIslandBottomClearance()
            .tabHeader("History")
        }
    }
}

private struct HistoryRow: View {
    let entry: ScanLogEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(entry.title)
                .font(.headline)
            HStack(spacing: 8) {
                Text(entry.scannedAt, format: Date.FormatStyle(date: .abbreviated, time: .shortened))
                Text("·")
                Text(chatSummary)
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }

    private var chatSummary: String {
        entry.chats.count == 1 ? "1 question" : "\(entry.chats.count) questions"
    }
}

struct HistoryDetailView: View {
    let entryID: UUID
    @EnvironmentObject private var appState: AppState

    var body: some View {
        if let entry = appState.scanHistory.first(where: { $0.id == entryID }) {
            List {
                Section {
                    LabeledContent("When", value: entry.scannedAt.formatted(date: .abbreviated, time: .shortened))
                    if let drugId = entry.drugId {
                        LabeledContent("Drug ID", value: drugId)
                    }
                } header: {
                    Text(entry.title)
                }

                ForEach(entry.chats) { turn in
                    Section {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("You")
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.secondary)
                            Text(turn.question)
                                .lineLimit(nil)
                                .fixedSize(horizontal: false, vertical: true)
                                .textSelection(.enabled)
                        }
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Assistant")
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.secondary)
                            Text(turn.answer)
                                .lineLimit(nil)
                                .fixedSize(horizontal: false, vertical: true)
                                .textSelection(.enabled)
                        }
                    } header: {
                        Text(turn.askedAt, format: Date.FormatStyle(date: .omitted, time: .shortened))
                    }
                }
            }
            .navigationTitle(entry.title)
            .navigationBarTitleDisplayMode(.inline)
            .tabIslandBottomClearance()
        } else {
            ContentUnavailableView("Chat unavailable", systemImage: "clock.arrow.circlepath")
                .tabIslandBottomClearance()
        }
    }
}

#Preview {
    HistoryView()
        .environmentObject(AppState())
}

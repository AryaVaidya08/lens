import SwiftUI
import UIKit
import AVFoundation

struct MedicationReviewsView: View {
    let patient: Patient
    @State private var reviews: [SavedMedicationReview] = []
    @State private var loading = false
    @State private var error: String?
    @State private var editing: ReviewSelection?

    var body: some View {
        List {
            Section {
                Text("Compare confirmed medication labels with a reference list and record what the patient reports taking.")
                    .foregroundStyle(.secondary)
                Button { editing = ReviewSelection(saved: nil) } label: {
                    Label("Start medication review", systemImage: "plus.circle.fill")
                }
                .accessibilityIdentifier("review.start")
            }
            if loading { ProgressView("Loading reviews") }
            if let error {
                Section { Text(error).foregroundStyle(.red); Button("Retry") { Task { await load() } } }
            }
            Section("Saved reviews") {
                if reviews.isEmpty && !loading { Text("No reviews saved yet.").foregroundStyle(.secondary) }
                ForEach(reviews) { review in
                    Button { editing = ReviewSelection(saved: review) } label: {
                        VStack(alignment: .leading, spacing: 5) {
                            Text(review.draft.referenceSource.isEmpty ? "Medication review" : review.draft.referenceSource)
                                .font(.headline).foregroundStyle(.primary)
                            Text("\(review.draft.reviewed ? "Compared" : "Draft") · \(review.draft.observed.count) bottles · \(review.dateLabel)")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .accessibilityIdentifier("review.saved")
                }
            }
        }
        .navigationTitle("Medication Review")
        .tabIslandBottomClearance()
        .task { await load() }
        .refreshable { await load() }
        .sheet(item: $editing, onDismiss: { Task { await load() } }) { selection in
            MedicationReviewEditor(patient: patient, saved: selection.saved)
        }
    }

    private func load() async {
        loading = true
        defer { loading = false }
        do { reviews = try await APIClient.shared.medicationReviews(patientId: patient.id); error = nil }
        catch { self.error = error.localizedDescription }
    }
}

private struct ReviewSelection: Identifiable {
    let id = UUID()
    let saved: SavedMedicationReview?
}

private struct EntrySelection: Identifiable {
    let id = UUID()
    let isReference: Bool
    let entry: MedicationEntry
}

struct MedicationReviewEditor: View {
    let patient: Patient
    @Environment(\.dismiss) private var dismiss
    @State private var reviewId: String
    @State private var draft: MedicationReviewDraft
    @State private var lastSaved: MedicationReviewDraft
    @State private var saved: SavedMedicationReview?
    @State private var entrySelection: EntrySelection?
    @State private var saving = false
    @State private var error: String?
    @State private var discardPrompt = false

    init(patient: Patient, saved: SavedMedicationReview?) {
        self.patient = patient
        var initial = saved?.draft ?? MedicationReviewDraft()
        if saved == nil {
            initial.referenceSource = "Clinic chart" + (patient.sourceLabel.isEmpty ? "" : " — " + patient.sourceLabel)
            initial.referenceText = patient.currentMedications
        }
        _reviewId = State(initialValue: saved?.id ?? UUID().uuidString)
        _draft = State(initialValue: initial)
        _lastSaved = State(initialValue: initial)
        _saved = State(initialValue: saved)
    }

    private var dirty: Bool { draft != lastSaved }
    private var currentReport: SavedMedicationReview? { !dirty && draft.reviewed ? saved : nil }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(patient.displayName).font(.headline)
                    Text("Save a draft anytime. Confirm both lists before comparing. Reviews do not change the clinic chart.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                referenceSection
                bottlesSection
                Section("Handoff notes") {
                    TextField("Questions, patient concerns, or follow-up needed", text: $draft.notes, axis: .vertical)
                        .lineLimit(3...8)
                }
                Section {
                    Button { Task { await save(compare: true) } } label: {
                        Label("Compare and save report", systemImage: "list.bullet.clipboard")
                    }
                    .disabled(!draft.canCompare || saving)
                    .accessibilityIdentifier("review.compare")
                    if !draft.canCompare {
                        Text("Enter a reference source and confirm the two checkboxes above to compare.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                    if saving { ProgressView("Saving review") }
                    if let saved, !dirty && !draft.reviewed {
                        Text("Draft saved \(saved.dateLabel)").font(.footnote).foregroundStyle(.secondary)
                            .accessibilityIdentifier("review.draftSaved")
                    }
                    if let error { Text(error).foregroundStyle(.red).accessibilityIdentifier("review.error") }
                    if dirty && saved != nil {
                        Text("Unsaved changes. Compare again to update the report.").font(.footnote)
                    }
                }
                if let result = currentReport { reportSection(result) }
            }
            .disabled(saving)
            .navigationTitle("Medication Review")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { if dirty { discardPrompt = true } else { dismiss() } }
                        .disabled(saving).accessibilityIdentifier("review.close")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save draft") { Task { await save(compare: false) } }
                        .disabled(saving || (saved != nil && !dirty))
                        .accessibilityIdentifier("review.saveDraft")
                }
            }
            .interactiveDismissDisabled(dirty || saving)
            .confirmationDialog("Discard unsaved changes?", isPresented: $discardPrompt, titleVisibility: .visible) {
                Button("Discard changes", role: .destructive) { dismiss() }
                Button("Keep editing", role: .cancel) {}
            }
            .sheet(item: $entrySelection) { selection in
                MedicationEntryEditor(entry: selection.entry, isReference: selection.isReference, references: draft.reference) { entry in
                    if selection.isReference {
                        upsert(entry, into: &draft.reference)
                        draft.referenceVerified = false
                    } else {
                        upsert(entry, into: &draft.observed)
                        draft.collectionComplete = false
                    }
                }
            }
        }
    }

    private var referenceSection: some View {
        Section {
            TextField("Source and date (e.g. discharge list Sep 27)", text: $draft.referenceSource)
                .accessibilityIdentifier("review.source")
                .onChange(of: draft.referenceSource) { _, value in
                    if value != lastSaved.referenceSource { draft.referenceVerified = false }
                }
            DisclosureGroup("Reference document / chart text") {
                TextField("Paste the reference medication list", text: $draft.referenceText, axis: .vertical)
                    .lineLimit(4...12)
                    .onChange(of: draft.referenceText) { _, value in
                        if value != lastSaved.referenceText { draft.referenceVerified = false }
                    }
                Text("Add and confirm each medication below. Pasted text is source material, not an automatically verified medication list.")
                    .font(.caption).foregroundStyle(.secondary)
            }
            ForEach(draft.reference) { entry in entryRow(entry, isReference: true) }
                .onDelete { offsets in
                    let removed = Set(offsets.map { draft.reference[$0].id })
                    draft.reference.remove(atOffsets: offsets)
                    for i in draft.observed.indices where removed.contains(draft.observed[i].referenceId ?? "") {
                        draft.observed[i].referenceId = nil
                    }
                    draft.referenceVerified = false
                }
            Button("Add reference medication") {
                entrySelection = EntrySelection(isReference: true, entry: MedicationEntry())
            }.accessibilityIdentifier("review.addReference")
            Toggle(draft.reference.isEmpty ? "I verified the source lists no medications" : "I verified all reference medications are entered", isOn: $draft.referenceVerified)
                .accessibilityIdentifier("review.referenceVerified")
        } header: { Text("1. Reference list") }
    }

    private var bottlesSection: some View {
        Section {
            ForEach(draft.observed) { entry in entryRow(entry, isReference: false) }
                .onDelete { draft.observed.remove(atOffsets: $0); draft.collectionComplete = false }
            Button { entrySelection = EntrySelection(isReference: false, entry: MedicationEntry()) } label: {
                Label("Add bottle / scan label", systemImage: "camera")
            }.accessibilityIdentifier("review.addBottle")
            Toggle(draft.observed.isEmpty ? "Collection complete: no bottles located" : "I finished collecting bottle details", isOn: $draft.collectionComplete)
                .accessibilityIdentifier("review.collectionComplete")
            Text("Include nonprescription products and supplements. A bottle being present does not establish that the patient takes it.")
                .font(.caption).foregroundStyle(.secondary)
        } header: { Text("2. Bottles and reported use") }
    }

    private func entryRow(_ entry: MedicationEntry, isReference: Bool) -> some View {
        Button { entrySelection = EntrySelection(isReference: isReference, entry: entry) } label: {
            VStack(alignment: .leading, spacing: 4) {
                Text(entry.name).font(.headline).foregroundStyle(.primary)
                Text(entry.detail.isEmpty ? "Details not recorded" : entry.detail).font(.caption).foregroundStyle(.secondary)
                if !isReference {
                    Text("Reported use: \(entry.reportedUse.replacingOccurrences(of: "_", with: " "))")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
        }
    }

    private func reportSection(_ result: SavedMedicationReview) -> some View {
        Section {
            Text("Saved \(result.dateLabel)").font(.caption).foregroundStyle(.secondary)
            if result.findings.isEmpty {
                Text("No differences found by literal comparison. This is not a clinical safety assessment.")
            }
            ForEach(Array(result.findings.enumerated()), id: \.offset) { _, finding in
                VStack(alignment: .leading, spacing: 4) {
                    Text(finding.title).font(.headline)
                    Text(finding.detail).font(.subheadline)
                }
            }
            Text("Name matching is literal unless you link an entry yourself. Text differences may be equivalent instructions. Clarify findings before any medication change.")
                .font(.footnote).foregroundStyle(.secondary)
            ShareLink(item: result.report) { Label("Share report", systemImage: "square.and.arrow.up") }
                .accessibilityIdentifier("review.share")
            DisclosureGroup("Full report") { Text(result.report).font(.footnote).textSelection(.enabled) }
        } header: { Text("3. Items for follow-up") }
    }

    private func upsert(_ entry: MedicationEntry, into entries: inout [MedicationEntry]) {
        if let i = entries.firstIndex(where: { $0.id == entry.id }) { entries[i] = entry }
        else { entries.append(entry) }
    }

    private func save(compare: Bool) async {
        saving = true
        error = nil
        defer { saving = false }
        var payload = draft
        payload.reviewed = compare
        do {
            let result = try await APIClient.shared.saveMedicationReview(patientId: patient.id, reviewId: reviewId, draft: payload)
            draft = result.draft
            lastSaved = result.draft
            saved = result
        } catch { self.error = error.localizedDescription }
    }
}

struct MedicationEntryEditor: View {
    @Environment(\.dismiss) private var dismiss
    @State var entry: MedicationEntry
    let isReference: Bool
    let references: [MedicationEntry]
    let onConfirm: (MedicationEntry) -> Void
    @State private var scanner = false
    @State private var image: UIImage?
    @State private var reading = false
    @State private var error: String?
    @State private var confirmed = false
    @State private var cameraDenied = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Button("Scan label or document") { Task { await openScanner() } }
                        .disabled(!MedicationDocumentScanner.isSupported || reading)
                    if cameraDenied {
                        Button("Open camera settings") {
                            if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
                        }
                    }
                    if !MedicationDocumentScanner.isSupported {
                        Text("Scanning is unavailable on this device. Enter details or paste label text below.").font(.caption)
                    }
                    if reading { ProgressView("Reading label on device") }
                    if let error { Text(error).foregroundStyle(.red) }
                    if let image {
                        Image(uiImage: image).resizable().scaledToFit().frame(maxHeight: 260)
                            .accessibilityLabel("Captured medication label")
                    }
                    TextField("Original label / source text", text: $entry.sourceText, axis: .vertical)
                        .lineLimit(3...12)
                    Button("Suggest fields from text") { suggest() }
                        .disabled(entry.sourceText.isEmpty || reading)
                    Text("Suggestions may be incomplete. Compare every field with the original source. Photos stay on this screen; the transcription is saved with the record.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Section("Confirm medication details") {
                    TextField("Medication name", text: $entry.name).accessibilityIdentifier("medication.name")
                    TextField("Strength (e.g. 10 mg)", text: $entry.strength).accessibilityIdentifier("medication.strength")
                    TextField("Formulation / release type", text: $entry.formulation).accessibilityIdentifier("medication.formulation")
                    TextField("Directions exactly as written", text: $entry.directions, axis: .vertical).accessibilityIdentifier("medication.directions")
                    Text("Leave unavailable details blank. Strength is not the same as the dose taken.").font(.caption).foregroundStyle(.secondary)
                }
                if !isReference {
                    Section("Patient-reported use") {
                        Picker("Taking this?", selection: $entry.reportedUse) {
                            Text("Not asked").tag("not_asked")
                            Text("Taking").tag("taking")
                            Text("Not taking").tag("not_taking")
                            Text("Unsure").tag("unsure")
                        }
                        TextField("Actual use / patient's words", text: $entry.notes, axis: .vertical)
                        Picker("Corresponding reference entry", selection: $entry.referenceId) {
                            Text("Match by exact name / unresolved").tag(nil as String?)
                            ForEach(references) { ref in
                                Text("\(ref.name) \(ref.strength) \(ref.formulation)").tag(Optional(ref.id))
                            }
                        }
                        Text("Link only after confirming medication identity, including brand/generic differences.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
                Section {
                    Toggle("I checked these details against the source", isOn: $confirmed)
                        .accessibilityIdentifier("medication.confirmed")
                }
            }
            .onChange(of: entry) { _, _ in confirmed = false }
            .navigationTitle(isReference ? "Reference medication" : "Bottle details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Confirm") { onConfirm(entry); dismiss() }
                        .disabled(!entry.isValid || !confirmed || reading)
                        .accessibilityIdentifier("medication.save")
                }
            }
            .interactiveDismissDisabled()
            .sheet(isPresented: $scanner) {
                MedicationDocumentScanner { result in
                    scanner = false
                    switch result {
                    case .success(let captured):
                        image = captured
                        reading = true
                        Task {
                            do {
                                entry.sourceText = try await MedicationDocumentScanner.recognize(captured)
                                error = entry.sourceText.isEmpty ? "No text found. Retake the photo or enter details manually." : nil
                                suggest()
                            } catch { self.error = "Couldn't read this image. Enter the label details manually or retry." }
                            reading = false
                        }
                    case .failure(let failure): error = failure.localizedDescription
                    }
                } onCancel: { scanner = false }
            }
        }
    }

    private func suggest() {
        let suggestion = MedicationLabelSuggestions.entry(from: entry.sourceText)
        // Existing corrections are never overwritten by a subsequent OCR pass.
        if entry.name.isEmpty { entry.name = suggestion.name }
        if entry.strength.isEmpty { entry.strength = suggestion.strength }
        if entry.formulation.isEmpty { entry.formulation = suggestion.formulation }
        if entry.directions.isEmpty { entry.directions = suggestion.directions }
        confirmed = false
    }

    private func openScanner() async {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        let allowed: Bool
        if status == .notDetermined { allowed = await AVCaptureDevice.requestAccess(for: .video) }
        else { allowed = status == .authorized }
        cameraDenied = !allowed
        if allowed { error = nil; scanner = true }
        else { error = "Camera access is unavailable. Enter details manually or enable access in Settings." }
    }
}

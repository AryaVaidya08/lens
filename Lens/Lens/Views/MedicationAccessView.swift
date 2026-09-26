import SwiftUI

struct MedicationAccessView: View {
    let patient: Patient
    @State private var cases: [SavedMedicationAccess] = []
    @State private var policies: [AccessPolicy] = []
    @State private var loading = true
    @State private var error: String?
    @State private var selection: AccessSelection?

    var body: some View {
        List {
            Section {
                Text("Prepare a prior-authorization packet, find documentation gaps, and track access through patient receipt.")
                    .foregroundStyle(.secondary)
                Button { selection = AccessSelection(saved: nil) } label: {
                    Label("Start access case", systemImage: "plus.circle.fill")
                }
                .disabled(loading || error != nil)
                .accessibilityIdentifier("access.start")
            }
            if loading { ProgressView("Loading access cases") }
            if let error {
                Text(error).foregroundStyle(.red)
                Button("Retry") { Task { await load() } }
            }
            Section("Saved cases") {
                if cases.isEmpty && !loading { Text("No access cases yet.").foregroundStyle(.secondary) }
                ForEach(cases) { item in
                    Button { selection = AccessSelection(saved: item) } label: {
                        VStack(alignment: .leading, spacing: 5) {
                            Text(item.draft.medication.isEmpty ? "Medication access case" : item.draft.medication).font(.headline)
                            Text(item.draft.status.label).font(.subheadline)
                            Text([item.draft.payer, item.draft.assignee, item.draft.followUp].filter { !$0.isEmpty }.joined(separator: " · "))
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .accessibilityIdentifier("access.saved")
                }
            }
        }
        .navigationTitle("Medication Access")
        .tabIslandBottomClearance()
        .task { await load() }
        .refreshable { await load() }
        .sheet(item: $selection, onDismiss: { Task { await load() } }) { choice in
            MedicationAccessEditor(patient: patient, policies: policies, saved: choice.saved)
        }
    }

    private func load() async {
        loading = true
        defer { loading = false }
        do {
            async let loadedPolicies = APIClient.shared.accessPolicies()
            async let loadedCases = APIClient.shared.medicationAccess(patientId: patient.id)
            (policies, cases) = try await (loadedPolicies, loadedCases)
            error = nil
        } catch { self.error = error.localizedDescription }
    }
}

private struct AccessSelection: Identifiable {
    let id = UUID()
    let saved: SavedMedicationAccess?
}

struct MedicationAccessEditor: View {
    let patient: Patient
    let policies: [AccessPolicy]
    @Environment(\.dismiss) private var dismiss
    @StateObject private var speech = SpeechRecognizer()
    @State private var caseId: String
    @State private var draft: MedicationAccessDraft
    @State private var lastSaved: MedicationAccessDraft
    @State private var saved: SavedMedicationAccess?
    @State private var saving = false
    @State private var error: String?
    @State private var discard = false
    @State private var medicationEditor = false
    @State private var requirementTitle = ""
    @State private var requirementDetail = ""
    @State private var transitionNote = ""

    init(patient: Patient, policies: [AccessPolicy], saved: SavedMedicationAccess?) {
        self.patient = patient
        self.policies = policies
        let initial = saved?.draft ?? MedicationAccessDraft()
        _caseId = State(initialValue: saved?.id ?? UUID().uuidString)
        _draft = State(initialValue: initial)
        _lastSaved = State(initialValue: initial)
        _saved = State(initialValue: saved)
    }

    private var dirty: Bool { draft != lastSaved || !requirementTitle.isEmpty || !requirementDetail.isEmpty }
    private var busy: Bool { saving || speech.state != .idle }
    private var policy: AccessPolicy? { policies.first { $0.id == draft.policyId } }
    private var requirements: [AccessRequirement] { draft.policyId == "custom" ? draft.requirements : policy?.requirements ?? [] }
    private var current: SavedMedicationAccess? { dirty ? nil : saved }
    private var canReady: Bool {
        saved != nil && saved?.missing.isEmpty == true && draft.sourceContent == lastSaved.sourceContent
            && !draft.letter.isEmpty && draft.reviewed
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(patient.displayName).font(.headline)
                    Text(draft.status.label).foregroundStyle(.secondary)
                    Text("Lens prepares documentation. Submit through the payer's channel and record outcomes here.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Group {
                    prescriptionSection
                    insuranceSection
                    policySection
                    evidenceSection
                    rationaleSection
                    letterSection
                }
                .disabled(saving || draft.status.packetLocked)
                resultsSection
                trackingSection
                if let error { Section { Text(error).foregroundStyle(.red).accessibilityIdentifier("access.error") } }
                if saving { ProgressView("Saving case") }
            }
            .navigationTitle("Access case")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { if dirty || !transitionNote.isEmpty { discard = true } else { dismiss() } }.disabled(busy)
                        .accessibilityIdentifier("access.close")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { Task { await save() } }.disabled(busy)
                        .accessibilityIdentifier("access.save")
                }
            }
            .interactiveDismissDisabled(dirty || busy || !transitionNote.isEmpty)
            .confirmationDialog("Discard unsaved changes?", isPresented: $discard, titleVisibility: .visible) {
                Button("Discard changes", role: .destructive) { dismiss() }
            }
            .sheet(isPresented: $medicationEditor) {
                MedicationEntryEditor(entry: medicationEntry, isReference: true, references: []) { entry in
                    draft.medication = entry.name; draft.strength = entry.strength
                    draft.formulation = entry.formulation; draft.directions = entry.directions
                    draft.medicationSource = entry.sourceText
                }
            }
            .onChange(of: draft.sourceContent) { _, content in
                guard content != lastSaved.sourceContent else { return }
                draft.letter = ""; draft.reviewed = false
                if draft.status == .ready { draft.status = .incomplete }
            }
            .onChange(of: draft.letter) { _, value in
                if value != lastSaved.letter { draft.reviewed = false }
            }
            .onChange(of: [draft.medication, draft.strength, draft.formulation, draft.payer, draft.plan, draft.indication]) { _, _ in
                if draft.sourceContent != lastSaved.sourceContent { draft.policyConfirmed = false }
            }
            .onChange(of: [draft.policyTitle, draft.policySource, draft.policyDate]) { _, _ in
                if draft.sourceContent != lastSaved.sourceContent { draft.policyConfirmed = false }
            }
            .onDisappear { speech.cancel() }
        }
    }

    private var prescriptionSection: some View {
        Section("Prescription") {
            Button("Scan or enter medication") { medicationEditor = true }.disabled(busy)
            TextField("Medication name", text: $draft.medication).accessibilityIdentifier("access.medication")
            TextField("Strength", text: $draft.strength)
            TextField("Formulation", text: $draft.formulation)
            TextField("Prescribed directions", text: $draft.directions, axis: .vertical)
            TextField("Quantity and days' supply", text: $draft.quantity)
            TextField("Indication / diagnosis", text: $draft.indication, axis: .vertical)
            if !draft.medicationSource.isEmpty {
                DisclosureGroup("Medication source transcription") { Text(draft.medicationSource).textSelection(.enabled) }
            }
            Text("Confirm the prescription details; a scanned label may describe an older prescription.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    private var insuranceSection: some View {
        Section("Patient, plan, and prescriber") {
            TextField("Payer", text: $draft.payer)
            TextField("Exact plan / pharmacy benefit", text: $draft.plan)
            TextField("Member ID", text: $draft.memberId)
            TextField("Patient date of birth", text: $draft.patientDob)
            TextField("Prescriber name and NPI", text: $draft.prescriber)
            TextField("Prescriber phone / fax / address", text: $draft.prescriberContact, axis: .vertical)
        }
    }

    private var policySection: some View {
        Section("Payer requirements") {
            Picker("Policy", selection: $draft.policyId) {
                Text("Select a policy").tag("")
                ForEach(policies) { Text($0.title).tag($0.id) }
                Text("Enter requirements from payer source").tag("custom")
            }
            .onChange(of: draft.policyId) { _, _ in draft.selectPolicy(policy) }
            if let policy {
                Text(policy.scope).font(.footnote)
                Text("Payer: \(policy.payer)").font(.footnote)
                Text("Medication: \(policy.medication), \(policy.strengths.joined(separator: ", ")) \(policy.formulation)").font(.footnote)
                if let url = URL(string: policy.sourceURL) { Link("Open official policy", destination: url) }
                Text(policy.sourceDate).font(.caption).foregroundStyle(.secondary)
            } else if draft.policyId == "custom" {
                TextField("Policy title", text: $draft.policyTitle)
                TextField("Source URL or document reference", text: $draft.policySource, axis: .vertical)
                TextField("Policy version / effective date / checked date", text: $draft.policyDate)
                Text("Enter every applicable requirement, including alternatives and exceptions. Lens checks documentation presence against your checklist.")
                    .font(.caption).foregroundStyle(.secondary)
                ForEach(draft.requirements) { requirement in
                    VStack(alignment: .leading) {
                        Text(requirement.title).font(.headline)
                        Text(requirement.detail).font(.caption)
                        Button("Remove requirement", role: .destructive) {
                            draft.requirements.removeAll { $0.id == requirement.id }
                            draft.evidence.removeAll { $0.requirementId == requirement.id }
                            draft.policyConfirmed = false
                        }
                    }
                }
                TextField("Requirement title", text: $requirementTitle)
                TextField("Exact condition, alternatives, and exceptions", text: $requirementDetail, axis: .vertical)
                Button("Add requirement") {
                    let item = AccessRequirement(title: requirementTitle.trimmingCharacters(in: .whitespacesAndNewlines), detail: requirementDetail)
                    draft.requirements.append(item)
                    draft.evidence.append(AccessEvidence(requirementId: item.id))
                    requirementTitle = ""; requirementDetail = ""; draft.policyConfirmed = false
                }
                .disabled(requirementTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || draft.requirements.count >= 30)
            }
            Toggle("I verified this policy is current and applies to this member and request", isOn: $draft.policyConfirmed)
                .disabled(draft.policyId.isEmpty)
        }
    }

    private var evidenceSection: some View {
        Section("Supporting documentation") {
            if requirements.isEmpty { Text("Select or enter payer requirements first.").foregroundStyle(.secondary) }
            ForEach(requirements) { requirement in
                VStack(alignment: .leading, spacing: 8) {
                    Text(requirement.title).font(.headline)
                    Text(requirement.detail).font(.footnote)
                    AccessEvidenceFields(evidence: evidenceBinding(requirement.id))
                }
            }
            Text("Record references here; attach the actual records when submitting. Completed fields do not establish coverage eligibility.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    private var rationaleSection: some View {
        Section("Clinical rationale") {
            Picker("Request type", selection: $draft.requestKind) {
                Text("Initial request").tag("initial")
                Text("Appeal").tag("appeal")
            }
            if draft.requestKind == "appeal" {
                TextField("Reason given in denial", text: $draft.denialReason, axis: .vertical)
                TextField("Notice date, reference, deadline, and instructions", text: $draft.denialReference, axis: .vertical)
            }
            TextField("Why this patient needs the prescribed medication", text: $draft.rationale, axis: .vertical)
                .lineLimit(4...12).disabled(speech.state != .idle)
                .accessibilityIdentifier("access.rationale")
            Button(speech.state == .idle ? "Dictate rationale" : "Finish dictation") {
                if speech.state == .idle {
                    speech.startListening { text in
                        draft.rationale += (draft.rationale.isEmpty ? "" : "\n") + text
                    }
                } else { speech.stopListening() }
            }
            .disabled(speech.state == .requestingPermission || speech.state == .finishing)
            if speech.state != .idle {
                Text(speech.transcript.isEmpty ? "Listening…" : speech.transcript).foregroundStyle(.secondary)
                Button("Cancel dictation") { speech.cancel() }
            }
            if let message = speech.errorMessage { Text(message).font(.footnote).foregroundStyle(.red) }
            Text("Review dictated text before saving. The draft uses only the facts you enter.").font(.caption).foregroundStyle(.secondary)
        }
    }

    private var letterSection: some View {
        Section("Request letter") {
            if draft.letter.isEmpty {
                Text("Save to check documentation and generate an editable draft. Changing source facts regenerates the letter and clears its review.")
                    .font(.footnote).foregroundStyle(.secondary)
            } else {
                TextEditor(text: $draft.letter).frame(minHeight: 240)
                    .accessibilityIdentifier("access.letter")
                Toggle("I reviewed the letter and supporting documentation", isOn: $draft.reviewed)
                    .accessibilityIdentifier("access.reviewed")
            }
        }
    }

    private var resultsSection: some View {
        Section("Documentation check and export") {
            if let current {
                if current.missing.isEmpty {
                    Label("Required documentation fields are complete", systemImage: "checkmark.circle")
                    Text("This is a documentation check, not a payer decision.").font(.caption)
                } else {
                    ForEach(Array(current.missing.enumerated()), id: \.offset) { _, item in
                        Text("Missing: \(item)").foregroundStyle(.orange)
                    }
                }
                DisclosureGroup("Submission checklist") {
                    ForEach(Array(current.checklist.enumerated()), id: \.offset) { _, item in Text(item) }
                }
                ShareLink(item: current.exportText) {
                    Label("Export draft and checklist", systemImage: "square.and.arrow.up")
                }
                .accessibilityIdentifier("access.export")
                Text("Saved").font(.caption).foregroundStyle(.secondary).accessibilityIdentifier("access.savedState")
            } else {
                Text("Save changes to refresh the documentation check and export.").font(.footnote)
            }
        }
    }

    private var trackingSection: some View {
        Section("Staff follow-up") {
            TextField("Responsible staff member", text: $draft.assignee)
            TextField("Follow-up date and next action", text: $draft.followUp, axis: .vertical)
            if draft.status.packetLocked {
                Text("The submitted packet is preserved. Reopen as incomplete to change documentation or prepare an appeal.").font(.footnote)
            }
            TextField("New status note / confirmation reference", text: $transitionNote, axis: .vertical)
            ForEach(draft.status.next, id: \.self) { status in
                Button(status == .incomplete ? "Reopen as incomplete" : "Mark \(status.label.lowercased())") {
                    Task { await save(target: status) }
                }
                .disabled(busy || (status == .ready && !canReady)
                          || ([AccessStatus.submitted, .approved, .denied, .obtained].contains(status)
                              && transitionNote.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty))
                .accessibilityIdentifier("access.status.\(status.rawValue)")
            }
            if let saved {
                DisclosureGroup("Status history") {
                    ForEach(Array(saved.history.enumerated()), id: \.offset) { _, event in
                        VStack(alignment: .leading, spacing: 5) {
                            Text(event.status.label).font(.headline)
                            Text(event.at).font(.caption)
                            if !event.note.isEmpty { Text(event.note) }
                            if let packet = event.packet {
                                ShareLink("Export submitted letter", item: packet)
                            }
                        }
                    }
                }
            }
        }
        .disabled(saving)
    }

    private var medicationEntry: MedicationEntry {
        var entry = MedicationEntry()
        entry.name = draft.medication; entry.strength = draft.strength
        entry.formulation = draft.formulation; entry.directions = draft.directions
        entry.sourceText = draft.medicationSource
        return entry
    }

    private func save(target: AccessStatus? = nil) async {
        guard !busy else { return }
        guard requirementTitle.isEmpty && requirementDetail.isEmpty else {
            error = "Add the requirement you entered, or clear its fields, before saving."
            return
        }
        saving = true
        error = nil
        defer { saving = false }
        var payload = draft
        if let target {
            payload.status = target
            payload.statusNote = transitionNote.trimmingCharacters(in: .whitespacesAndNewlines)
            if target == .incomplete { payload.reviewed = false }
        }
        do {
            let result = try await APIClient.shared.saveMedicationAccess(patientId: patient.id, caseId: caseId, draft: payload)
            lastSaved = result.draft
            draft = result.draft
            saved = result
            if target != nil { transitionNote = "" }
        } catch { self.error = error.localizedDescription }
    }

    private func evidenceBinding(_ id: String) -> Binding<AccessEvidence> {
        Binding {
            draft.evidence.first { $0.requirementId == id } ?? AccessEvidence(requirementId: id)
        } set: { entry in
            if let index = draft.evidence.firstIndex(where: { $0.requirementId == id }) {
                draft.evidence[index] = entry
            }
        }
    }
}

private struct AccessEvidenceFields: View {
    @Binding var evidence: AccessEvidence
    var body: some View {
        TextField("Patient-specific evidence", text: Binding(get: { evidence.text }, set: {
            evidence.text = $0; evidence.confirmed = false
        }), axis: .vertical)
        TextField("Source: dated note, lab, or record reference", text: Binding(get: { evidence.source }, set: {
            evidence.source = $0; evidence.confirmed = false
        }), axis: .vertical)
        Toggle("I reviewed this evidence for the request", isOn: $evidence.confirmed)
    }
}

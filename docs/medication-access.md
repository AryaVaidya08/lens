# Medication Access Copilot

Open **Patients → a patient → Medication Access → Start access case**.

1. Scan a label/document or enter the prescribed medication. Confirm strength,
   formulation, directions, quantity, and indication against the prescription.
2. Enter the patient DOB, member ID, exact plan, payer, and prescriber details.
3. Select the supported policy, or enter a policy title, source, date/version,
   and its applicable requirements. Confirm current member/plan applicability.
4. For each requirement, enter the patient-specific evidence and a dated record
   reference. Review the evidence. Actual record attachments remain in the
   submitting staff member's workflow; Lens does not upload them.
5. Type or dictate the clinical rationale. For appeals, include the denial
   reason and notice reference, deadline, and instructions.
6. Save. Lens lists documentation gaps and assembles an editable request letter
   using entered facts. Review the draft, correct it, and confirm review.
7. Mark ready, export the draft and checklist, and submit through the payer's
   required form/portal. Record the submission reference when marking submitted.
8. Record approved/denied outcomes and confirmation that the patient obtained
   the medication. Assign a staff contact and next follow-up action as free text.

## Policy coverage

The built-in snapshot covers **Oklahoma SoonerCare requests for generic
rivaroxaban 10, 15, or 20 mg tablets instead of preferred brand Xarelto**.
It references the official [OHCA 2026 cardiovascular policy](https://oklahoma.gov/ohca/providers/types/pharmacy/prior-authorization/2026/cardiovascular.html),
retrieved September 26, 2026. The section does not publish its effective date;
the app says this explicitly. This is one narrow policy scope, not general
anticoagulant coverage. A payer name alone does not identify member benefits.

Staff can enter sourced requirements for other plans. Lens checks the presence
of evidence, a source, and a review attestation against that checklist; it does
not infer the full policy, adjudicate clinical criteria, verify attachments,
check eligibility, or predict approval. The built-in policy additionally checks
drug, strength, formulation, and payer scope. The user confirms current policy
and applicability each time a relevant field changes.

## Drafts, statuses, and data

Drafting uses a deterministic template, not generated clinical assertions. It
works without an LLM key and leaves missing fields visibly marked. Source edits
clear the UI letter and review; the server also detects retained stale letters
and regenerates them. Custom letter edits must be reviewed again.

Statuses follow incomplete → ready → submitted → approved/denied, then approved
→ obtained. Submitted cases can be reopened as incomplete for corrections or
an appeal. The server gates readiness on documentation and review, requires
outcome notes, prevents editing submitted clinical content without reopening,
and retains the submitted letter, source facts, policy snapshot, actor, and time
in history. Decision status is entered by staff, never fetched from a payer.

MongoDB collection: `medication_access`. Records are separate from clinic charts,
scoped to the authenticated clinician and patient, and use revision-based
optimistic concurrency. Staff assignment is a note, not account sharing or a
notification. There is no automatic submission, fax, EHR writeback, or payer
integration.

- `GET /medication-access/policies`
- `GET /patients/{patient_id}/medication-access`
- `PUT /patients/{patient_id}/medication-access/{case_id}`

## Verification

Backend tests: `backend/tests/test_medication_access.py` cover missing evidence,
policy mismatch, custom requirements, auth/ownership, stale saves, stale letter
regeneration, transitions, appeals, preserved submissions, and chart isolation.

`LENS_SKIP_LIVE_API=1 bash Lens/Tests/run-checks.sh` runs local Swift checks without
calling an existing server on port 8000. The access model checks include Codable
round trips and the boundary between clinical edits and workflow metadata.

`Lens/Tests/MedicationAccessLiveChecks.swift` exercises the actual Swift APIClient
against an isolated backend at `127.0.0.1:8001`. Start that backend with
`MONGODB_URI=mongomock://localhost MONGODB_DB=lens_access_qa SEED_ON_STARTUP=1`
and an empty `LLM_API_KEY`; never point these checks at production/Atlas.

The UI test `MedicationAccessUITests` targets the same isolated backend and
checks draft persistence, reopening, gaps, and blocked readiness. Physical-device
camera quality and speech capture still need device verification.

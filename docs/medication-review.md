# Medication Review

Open **Patients → a patient → Medication Review → Start medication review**.
This feature is available to any signed-in HCP with access to that patient.

1. Enter the reference source and date. The current clinic medication text is
   included as source material; it is not automatically interpreted as verified
   structured data. Add each reference medication and confirm its details.
2. Add bottles individually. On a supported physical iOS device, scan one label
   page per entry. Vision OCR runs on device. Review the image and transcription,
   correct the suggested fields, and confirm the entry. Manual entry and pasted
   text also work, including on the simulator. Images are temporary; the saved
   review preserves the transcription and confirmed fields.
3. Record reported use separately from the bottle directions. Link a bottle to
   a reference entry explicitly when names differ, such as a brand/generic pair.
4. Confirm that the reference list is complete and bottle collection is finished.
   An empty list is permitted only with the corresponding explicit confirmation.
5. Compare and save. Review discrepancies and share the text report using the
   system share sheet. Save draft permits interruption before collection finishes.
   Reopen saved drafts or reports from the review list.

Reviews are separate MongoDB documents in `medication_reviews`. They never write
to the imported clinic chart. Endpoints use existing bearer authentication and
check patient ownership on every read and write:

- `GET /patients/{patient_id}/medication-reviews`
- `PUT /patients/{patient_id}/medication-reviews/{review_id}`

The PUT body is `MedicationReviewDraft` / `ReviewInput`. New records use revision
0; the response returns the next revision. Stale updates return 409. After an
uncertain network outcome or conflict, reopen the saved review before editing.

Comparison uses exact names after case/whitespace normalization, or an explicit
HCP-confirmed reference link. It flags missing fields, text differences, unmatched
names, unmatched reference entries, multiple bottles, and unresolved reported
use. It does not establish therapeutic equivalence, adherence, interactions,
appropriate doses, or clinical safety. Missing bottles do not mean medications
have been stopped. The report is a handoff for review, not an order or EHR update.

Validation: backend tests cover persistence, ownership, conflicts, chart isolation,
and comparison edge cases. Swift checks cover OCR suggestions and JSON contracts.
The simulator UI test exercises manual entry, comparison, sharing availability,
and reopening. Camera capture and OCR quality on actual labels still require a
physical-device check.

`LENS_RUN_VISION_OCR_CHECKS=1 bash Lens/Tests/run-checks.sh` additionally runs an
image-based Vision OCR fixture. This requires working Apple Vision runtime
services; the normal model/contract checks do not depend on those services.

For isolated end-to-end checks, run the backend with
`MONGODB_URI=mongomock://localhost MONGODB_DB=lens_medreview_ui LLM_API_KEY=''`
on `127.0.0.1:8001`. `MedicationReviewUITests` and
`MedicationReviewLiveChecks.swift` use this address. Never point this test server
at a real patient database. Run the UI case with
`-only-testing:LensUITests/MedicationReviewUITests` on a dedicated simulator.

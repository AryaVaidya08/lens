# Anthony's iOS features

The profile picker, voice demo, and settings run without a backend. The app restores the last selected profile using `UserDefaults`; Settings → Log out removes it and clears the current drug and familiarity tier. The Scan tab hosts the existing `CameraView` for the AR lane.

Local demo profiles are defined in `Lens/Lens/Models/HCP.swift`:

| ID | Name | Specialty |
|---|---|---|
| `hcp_001` | Dr. Maya Patel | Primary Care |
| `hcp_002` | Dr. James Chen | Cardiology |
| `hcp_003` | Dr. Sofia Ramirez | Endocrinology |

These are local presets, not real accounts. Backend seed data is still a stub; align its IDs with these presets when integrating profiles.

The Assistant tab requests microphone and speech recognition permissions on first use, shows a live English transcript, and speaks a clearly labeled demo reply. Tap **Finish** to submit the transcript. Recording stops automatically after 45 seconds. **Cancel** discards the pending question; **Stop speaking** interrupts playback. Leaving the tab, logging out, backgrounding the app, an audio interruption, or disconnecting an audio device stops audio. Recognition uses the device when supported; otherwise availability can depend on the network.

`Voice/PlaceholderAssistant.swift` is the explicit reply placeholder. Future work can replace its use in `VoiceAssistantView` with `APIClient.askQuestion(drugId:hcpId:query:)`. There are no LLM calls or clinical answers in this demo.

## Edit profile preview

Settings → Edit profile opens a temporary form with first and last name, email, professional role, credentials, primary specialty, practice/organization, practice setting, work phone, city, state/province/region, and country. The existing name and specialty are prefilled; unknown contact or practice information stays blank.

The specialty dropdown contains 101 choices in nine groups, plus Other / not listed with a custom field. The list covers medical specialties and common subspecialties informed by [ABMS](https://abms.org/member-boards/specialty-subspecialty-certificates/), and broader healthcare practice areas informed by [NUCC](https://taxonomy.nucc.org/). These are display choices, not a complete credentialing or billing taxonomy.

First name, last name, a plausibly formatted email address, professional role, and specialty are required to enable Save. Other role/specialty selections require a description. Credentials and practice details are optional. Save shows the preview notice and Done closes the sheet; Cancel dismisses it directly. Nothing updates the HCP model, cached identity, or backend. Reopening the form starts from the selected demo profile again.

The expanded form passes the Debug simulator build. The specialty list was checked for duplicate entries and compatibility with all three preset profiles. On-device checks: open the menu, choose Other and enter a specialty, try a malformed email, fill the required fields, then confirm Save/Done and Cancel both leave the current profile unchanged.

## Assistant voice

The assistant uses one fixed US English voice: **Ava**. It selects Ava Premium when installed, then Ava Enhanced, then standard Ava. There is no voice picker. Download Ava Premium in iPhone Settings → Accessibility → Read & Speak → Voices → English, then return to Lens. Available voices are checked before each reply, so a new download can be used without changing app preferences. If Ava is absent, the system English voice is used to keep playback working; the upgraded sound requires the Ava download on each demo device.

See [Apple's spoken-content settings guide](https://support.apple.com/guide/iphone/hear-whats-on-the-screen-or-typed-iph96b214f0/ios). The automated runner includes seven fixed-voice checks for quality variants, locale, missing voices, and stable selection. Actual voice quality must be auditioned on the iPhone.

## Validation

Scan now includes the assistant: tap the bottom-left microphone to start, then
tap the stop icon to finish and hear the demo reply. The compact overlay shows
the transcript, replay, cancel/stop, and permission errors. Closing it stops
audio while leaving the camera visible. The separate Assistant tab has been
removed; switching to Settings or backgrounding still stops audio. ARKit only
captures video, leaving microphone capture to the speech driver. Drug answers
remain the existing local demo until backend integration.

The microphone floats separately at the bottom-left alongside the native
Scan/Settings tab island. Its idle background and border use native glass to
match the island; it turns black with a white icon and blue ring while recording,
finishing, or speaking. Before text arrives, only a compact status/cancel pill
appears; transcript/reply/error content opens a panel sized to its content,
scrolling when longer. Tapping the microphone during playback stops speech.

Run the automated checks from the repository root:

```sh
Lens/Tests/run-checks.sh
```

The runner compiles the production profile and voice coordinator code with warnings treated as errors. Profile checks cover all three presets, restoration, profile switching, repeated logout, malformed cached profiles, and unrelated preferences. Three separate processes verify saving a profile, restoring it and logging out, then confirming logout persisted. The test preferences domain is uniquely named and removed afterward. Run outside a restrictive filesystem sandbox because Foundation must persist this isolated preferences domain.

The 27 voice cases use a fake Apple API driver and a manually controlled clock to cover permission denial/restriction, cancellation before and during permission prompts, live partial text, final text, silent input, errors, retry, repeated starts, stale callbacks, recording/finalization timeouts, and exactly-once completion. They exercise the production conversation logic without requiring a microphone or network. They do not validate Apple's recognition service or audible playback.

`Lens/Tests` is outside the app's synchronized source group.

The camera lifecycle checks cover first-layout gating, 500 tab-switch and
background/foreground cycles, repeated events, and late layout while Scan is
hidden. The merged camera now resumes a retained view when Scan reappears,
pauses when hidden or inactive, and discards in-flight detection results from a
previous session. These checks test lifecycle decisions, not camera frames.
On an iPhone, also open and close the assistant on Scan repeatedly, including during
recording and reply playback. Confirm the live feed and detection keep updating.
Switch Scan → Settings → Scan and background/foreground Scan; confirm the feed
resumes with no lingering microphone audio. Rotate the phone
and repeat. ARKit capture cannot be verified in the simulator.

On a physical iPhone, build `Lens/Lens.xcodeproj` and check:

1. Choose a profile, force-quit, and reopen. The picker should be skipped and Settings should show the same name and specialty.
2. Tap the microphone on Scan, grant both permissions, speak, and tap the stop icon. Confirm the visible transcript and audible demo reply match. Replay the reply and stop it mid-sentence.
3. Start another recording. Cancel, switch tabs, or background the app. Confirm the microphone stops and no delayed reply plays. Repeat while a reply is speaking.
4. Finish without speaking. Confirm a retry message appears. Deny microphone or speech permission in iOS Settings and confirm a useful error and the Open app settings button appear. Restore permission and retry.
5. Log out from Settings. Confirm the picker appears immediately and still appears after relaunch. Choose a different profile and confirm the previous voice conversation is gone.

Microphone and speech privacy descriptions are configured for both Debug and Release through generated Info.plist build settings. Actual recognition, playback, and permission prompts require device validation; Swift syntax checks alone do not verify these behaviors.

## Latest verification

- Automated profile and all 27 voice cases: passed, including separate-process persistence.
- Full Debug iOS Simulator build (arm64 and x86_64): passed.
- Full Release iPhone build (arm64, signing disabled): passed.
- Generated microphone/speech permission descriptions in both built apps: verified.
- Project plist and whitespace checks: passed.

Xcode 27 emits deprecation warnings for the existing audio tap and interruption APIs; these APIs remain available. It also reports that App Intents metadata extraction is skipped because this app has no App Intents dependency.

The automated tests exercise recognition logic with simulated driver events; they do not verify screen interactions or real microphone/recognition/playback. Use the device checklist above before the demo. The current build targets iOS 26.6.

The build exposed a missing `Combine` import in the existing `ARSessionManager` scaffold. Only that import was added to make the full app build; no AR or detection behavior was implemented. Voice fixes include preventing permission requests after immediate cancellation, ignoring stale finalization callbacks, and avoiding passing a non-Sendable utterance into the playback completion task.

Microphone reliability follow-up: the full circular button is tappable, and the
assistant is removed (and audio cancelled) when leaving Scan. After Finish, a
recognition error now completes using already captured words, matching the
existing timeout behavior; empty final callbacks no longer erase those words.
Silent input and errors during active recording still report an error. Added
regressions cover those paths, cancellation before a late error, and 100 repeated
recordings. This reproduces a missing-reply path in the coordinator; audible
playback and live recognition still require checking on the iPhone.

### Patient-specific scan presentation

When a scan session has a patient, the scan bubble shows only the drug name,
patient name, recorded allergies/current medications, and the existing backend
patient-check results. General drug headlines and bullets remain exclusive to
scans without a patient. Loading, missing checks, and offline failures never
fall back to general information or imply that interactions were ruled out;
unavailable checks offer Retry. Checks for a different patient are rejected,
and late requests cannot overwrite a newer patient/drug scan. The patient chip
remains visible for the session, including after engagement logging.

### Specialty-aware general scans

General scan summaries now use the authenticated HCP's saved specialty as well
as familiarity. Initial display preferences cover primary care (including family
and internal medicine), cardiology, endocrinology, pediatrics, geriatrics,
obstetrics/gynecology, psychiatry, nephrology, and oncology. The backend selects
existing dossier sections, reserving a slot for a prominent warning when
available, then familiarity and specialty content. These are editorial section
priorities, not validated clinical recommendations. The headline identifies the
specialty when relevant content exists. Unknown specialties or missing relevant
sections use the existing general summary; offline catalog content remains
general. Patient-specific scan checks are unchanged. Editing specialty refreshes
the active general scan without logging another engagement.

Patient-check display follow-up: after detecting a drug in patient mode, keep
its check panel visible even when live detection goes stale. The panel is fixed
below the patient chip instead of shrinking/flashing with the bottle. Results
(or an unavailable/retry message) appear before the chart details in a bounded
scroll area. Scanning another drug replaces the retained result; changing or
clearing the patient resets it. The existing checker remains chart/dossier name
matching, not a comprehensive clinical allergy or interaction assessment.

The concerns heading and details now appear only when the patient-check response
contains nonblank flags. A completed `clear` response with no flags omits that
section entirely; errors or incomplete responses retain an unavailable/retry
message. Recorded chart allergies remain visible independently of a match to the
scanned drug. The panel sizes to its text and scrolls only beyond its height cap,
so an empty concerns section no longer reserves a large blank area. Contract
checks cover flagged, clear, whitespace-only, inconsistent, and unavailable
results. No-match results are not proof of clinical safety; the backend currently
performs name matching only.

General scan loading now shows only the detected drug name and a loading
indicator until its personalized response arrives. The built-in catalog appears
only after a request failure, labeled Offline information with Retry live details.
A failed request stays in that state until retry or a different scan instead of
repeatedly swapping content on detection updates. Engagement-log failures do not
replace a successfully loaded summary. Patient checks keep their separate
loading/error presentation and never use generic offline information.

### Full-screen scan messages

Tap a loaded scan card or its expand arrow to read it full-screen. The reader
uses normal-sized, selectable text in a scroll view, with an X at the top-right.
It snapshots the selected drug/patient result so changing camera detections do
not replace it while reading. Patient messages keep the patient-only content.
The summary API now includes optional `full_bullets` alongside compact `bullets`;
the reader uses the untruncated selected dossier sections when available. Older
backends and offline summaries fall back to the text they provide. Restart the
backend to serve the new full-text field.

### Deliberate repeat scans and voice history

After a result loads, **Scan again** refreshes that medication using the latest
server familiarity, then records one new engagement. It waits for any prior
engagement write before reading the next summary and is disabled while loading
or saving. Brief tracking losses, reopening the retained camera, and chart-only
refreshes do not create another touch for the same detected drug. Switching to a
different drug begins a new scan. To demonstrate the same bottle twice, tap
Scan again; removing and returning the bottle alone does not advance it.

A failed summary can recover through Retry without losing its pending touch.
A failed engagement write preserves the reference card and displays that saving
could not be confirmed; it is not automatically retried because the existing API
does not support idempotent engagement requests. Offline scans cannot guarantee
familiarity progression.

Voice questions capture the drug, HCP, and scan-session patient when recording
starts. Local history now receives that same drug/HCP snapshot, including nil
for a question started without a drug. A later bottle detection cannot rename
the saved conversation. Account changes and logout reject stale replies.

Regression checks cover scan read/write ordering, repeated detections, concurrent
writes, failures/recovery, voice context, drug-free questions, and account changes.
The test runner accepts `LENS_SKIP_PERSISTENCE=1 LENS_SKIP_LIVE_API=1` in restricted
environments; those skips do not verify cross-process preferences or a live API.
Rehearse new → returning → expert on a device with a fresh account/drug pairing;
patient mode intentionally continues to show chart checks rather than general
tier-based reference bullets.

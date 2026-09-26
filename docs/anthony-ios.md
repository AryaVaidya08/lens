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

## Assistant voice

The assistant uses one fixed US English voice: **Ava**. It selects Ava Premium when installed, then Ava Enhanced, then standard Ava. There is no voice picker. Download Ava Premium in iPhone Settings → Accessibility → Read & Speak → Voices → English, then return to Lens. Available voices are checked before each reply, so a new download can be used without changing app preferences. If Ava is absent, the system English voice is used to keep playback working; the upgraded sound requires the Ava download on each demo device.

See [Apple's spoken-content settings guide](https://support.apple.com/guide/iphone/hear-whats-on-the-screen-or-typed-iph96b214f0/ios). The automated runner includes seven fixed-voice checks for quality variants, locale, missing voices, and stable selection. Actual voice quality must be auditioned on the iPhone.

## Validation

Run the automated checks from the repository root:

```sh
Lens/Tests/run-checks.sh
```

The runner compiles the production profile and voice coordinator code with warnings treated as errors. Profile checks cover all three presets, restoration, profile switching, repeated logout, malformed cached profiles, and unrelated preferences. Three separate processes verify saving a profile, restoring it and logging out, then confirming logout persisted. The test preferences domain is uniquely named and removed afterward. Run outside a restrictive filesystem sandbox because Foundation must persist this isolated preferences domain.

The 22 voice cases use a fake Apple API driver and a manually controlled clock to cover permission denial/restriction, cancellation before and during permission prompts, live partial text, final text, silent input, errors, retry, repeated starts, stale callbacks, recording/finalization timeouts, and exactly-once completion. They exercise the production conversation logic without requiring a microphone or network. They do not validate Apple's recognition service or audible playback.

`Lens/Tests` is outside the app's synchronized source group.

On a physical iPhone, build `Lens/Lens.xcodeproj` and check:

1. Choose a profile, force-quit, and reopen. The picker should be skipped and Settings should show the same name and specialty.
2. Open Assistant, grant both permissions, speak, and tap Finish. Confirm the visible transcript and audible demo reply match. Replay the reply and stop it mid-sentence.
3. Start another recording. Cancel, switch tabs, or background the app. Confirm the microphone stops and no delayed reply plays. Repeat while a reply is speaking.
4. Finish without speaking. Confirm a retry message appears. Deny microphone or speech permission in iOS Settings and confirm a useful error and the Open app settings button appear. Restore permission and retry.
5. Log out from Settings. Confirm the picker appears immediately and still appears after relaunch. Choose a different profile and confirm the previous voice conversation is gone.

Microphone and speech privacy descriptions are configured for both Debug and Release through generated Info.plist build settings. Actual recognition, playback, and permission prompts require device validation; Swift syntax checks alone do not verify these behaviors.

## Latest verification

- Automated profile and all 22 voice cases: passed, including separate-process persistence.
- Full Debug iOS Simulator build (arm64 and x86_64): passed.
- Full Release iPhone build (arm64, signing disabled): passed.
- Generated microphone/speech permission descriptions in both built apps: verified.
- Project plist and whitespace checks: passed.

Xcode 27 emits deprecation warnings for the existing audio tap and interruption APIs; these APIs remain available. It also reports that App Intents metadata extraction is skipped because this app has no App Intents dependency.

The automated tests exercise recognition logic with simulated driver events; they do not verify screen interactions or real microphone/recognition/playback. Use the device checklist above before the demo. The current build targets iOS 26.6.

The build exposed a missing `Combine` import in the existing `ARSessionManager` scaffold. Only that import was added to make the full app build; no AR or detection behavior was implemented. Voice fixes include preventing permission requests after immediate cancellation, ignoring stale finalization callbacks, and avoiding passing a non-Sendable utterance into the playback completion task.

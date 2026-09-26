#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
check_dir=$(mktemp -d /tmp/lens-checks.XXXXXX)
preference_suite="lens.persistence-checks.$(uuidgen)"
cleanup() {
    if [[ -x "$check_dir/session-checks" ]]; then
        "$check_dir/session-checks" cleanup "$preference_suite"
    fi
    rm -rf "$check_dir"
}
trap cleanup EXIT

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/AR/CameraSessionLifecycle.swift Lens/Tests/CameraLifecycleChecks.swift \
    -o "$check_dir/camera-checks"
"$check_dir/camera-checks"

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Models/HCP.swift Lens/Lens/Models/Drug.swift \
    Lens/Lens/App/AppState.swift Lens/Tests/SessionChecks.swift \
    -o "$check_dir/session-checks"
"$check_dir/session-checks"
"$check_dir/session-checks" save "$preference_suite"
"$check_dir/session-checks" restore-and-logout "$preference_suite"
"$check_dir/session-checks" verify-logout "$preference_suite"

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Voice/SpeechRecognitionDriver.swift \
    Lens/Lens/Voice/SpeechRecognizer.swift Lens/Lens/Voice/PlaceholderAssistant.swift \
    Lens/Tests/VoiceChecks.swift -o "$check_dir/voice-checks"
"$check_dir/voice-checks"

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Voice/SpeechVoiceSelection.swift Lens/Tests/VoiceSelectionChecks.swift \
    -o "$check_dir/voice-selection-checks"
"$check_dir/voice-selection-checks"

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
    Lens/Lens/Models/ScanHistory.swift \
    Lens/Lens/App/AppState.swift Lens/Tests/SessionChecks.swift \
    -o "$check_dir/session-checks"
"$check_dir/session-checks"
"$check_dir/session-checks" save "$preference_suite"
"$check_dir/session-checks" restore-and-logout "$preference_suite"
"$check_dir/session-checks" verify-logout "$preference_suite"

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Voice/SpeechRecognitionDriver.swift \
    Lens/Lens/Voice/SpeechRecognizer.swift Lens/Lens/Voice/PlaceholderAssistant.swift \
    Lens/Lens/Models/DemoDrugCatalog.swift Lens/Lens/Models/Drug.swift \
    Lens/Lens/Models/DrugSummary.swift \
    Lens/Tests/VoiceChecks.swift -o "$check_dir/voice-checks"
"$check_dir/voice-checks"

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Voice/SpeechVoiceSelection.swift Lens/Tests/VoiceSelectionChecks.swift \
    -o "$check_dir/voice-selection-checks"
"$check_dir/voice-selection-checks"

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Networking/Endpoints.swift Lens/Lens/Networking/APIClient.swift \
    Lens/Lens/Models/HCP.swift Lens/Lens/Models/Patient.swift Lens/Lens/Models/Drug.swift \
    Lens/Lens/Models/DrugSummary.swift Lens/Lens/Models/MedicationReview.swift Lens/Lens/Models/MedicationAccess.swift Lens/Tests/ContractChecks.swift \
    -o "$check_dir/contract-checks"
"$check_dir/contract-checks"

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Networking/DrugResolver.swift Lens/Lens/Models/DemoDrugCatalog.swift \
    Lens/Lens/Models/HCP.swift Lens/Lens/Models/Patient.swift Lens/Lens/Models/Drug.swift Lens/Lens/Models/DrugSummary.swift \
    Lens/Lens/Networking/APIClient.swift Lens/Lens/Networking/Endpoints.swift Lens/Lens/Models/MedicationReview.swift Lens/Lens/Models/MedicationAccess.swift \
    Lens/Tests/ResolverChecks.swift \
    -o "$check_dir/resolver-checks"
"$check_dir/resolver-checks"

if [[ "${LENS_SKIP_LIVE_API:-0}" != "1" ]] && curl -sf --max-time 2 http://127.0.0.1:8000/health >/dev/null; then
    swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
        Lens/Lens/Networking/Endpoints.swift Lens/Lens/Networking/APIClient.swift \
        Lens/Lens/Models/HCP.swift Lens/Lens/Models/Patient.swift Lens/Lens/Models/Drug.swift \
        Lens/Lens/Models/DrugSummary.swift Lens/Lens/Models/MedicationReview.swift Lens/Lens/Models/MedicationAccess.swift Lens/Tests/LiveAPIChecks.swift \
        -o "$check_dir/live-api-checks"
    "$check_dir/live-api-checks"
else
    echo "SKIP: live URLSession checks (disabled or backend not running on :8000)"
fi

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Models/MedicationReview.swift Lens/Tests/MedicationReviewChecks.swift \
    -o "$check_dir/medication-review-checks"
"$check_dir/medication-review-checks"

swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
    Lens/Lens/Models/MedicationAccess.swift Lens/Tests/MedicationAccessChecks.swift \
    -o "$check_dir/medication-access-checks"
"$check_dir/medication-access-checks"

if [[ "${LENS_RUN_VISION_OCR_CHECKS:-0}" == "1" ]]; then
    swiftc -warnings-as-errors -module-cache-path "$check_dir/modules" \
        Lens/Lens/Detection/MedicationLabelOCR.swift Lens/Lens/Models/MedicationReview.swift \
        Lens/Tests/MedicationOCRChecks.swift -o "$check_dir/medication-ocr-checks"
    "$check_dir/medication-ocr-checks"
fi

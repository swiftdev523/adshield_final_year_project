# Phase 6 - Final Consistency Test Plan

Date: 2026-08-29

## Scope

Phase 6 validates the completed integration on the existing physical Android device. It does not add application features.

## Files created

- `docs/phase6/PHASE6_TEST_PLAN.md`
- `docs/phase6/protected_files_before.sha256`
- `docs/phase6/protected_files_after.sha256`
- `docs/phase6/PHASE6_VALIDATION_REPORT.md`

## Production files edited

None are planned. A production edit is permitted only if a reproducible Phase 6 defect requires a minimal fix; any such edit must be documented and retested.

## Protected behavior

- Existing APK analysis and its binary/category models.
- Existing installed-app discovery and analysis.
- Existing notification listener, event capture and explicit notification analysis.
- Existing scan-history persistence and Home derivation.
- Phase 5 local Privacy Mode and truthful Settings controls.
- All backend thresholds, feature contracts and model artifacts.

## Required checks

1. Run TypeScript and complete frontend Jest tests.
2. Run active Kotlin/native module unit tests.
3. Run backend pytest tests.
4. Exercise the specified APK, installed-app, notification, history/Home and Settings states on the connected phone where safely reproducible.
5. Preserve or restore phone state after destructive-state tests where feasible.
6. Recompute protected-file hashes and compare them with the pre-test manifest.

## Build rule

The Android debug APK is rebuilt only if native code changes. With no native change, the previously verified Phase 4 APK remains the native baseline and JavaScript is verified through Metro on the installed development build.

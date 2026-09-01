"""Generate the frozen binary model's input-contract audit.

This is an inspection utility only.  It never reads or rewrites training rows,
changes the estimator, or generates model predictions.  The classification is
anchored to the feature names embedded in the frozen Random Forest and to the
runtime normalizer in ``backend.apk_analysis.permission_mapping``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "adware_detection_rf_model.pkl"
OUTPUT_PATH = ROOT / "models" / "binary_feature_contract_audit.json"

EXPECTED_MODEL_SHA256 = (
    "54b7560bf7845b5eb5fb7a60057fd9a166c2843c5c8e65c133ad78d80d2aeba5"
)
EXPECTED_ORDERED_FEATURE_SHA256 = (
    "024ca7f02a42988fd35bb8154d10dd1e1315089cb0d77361bcda7b9164e0d4d8"
)
EXPECTED_FEATURE_COUNT = 241

# These names cannot be activated faithfully by the current final-token
# manifest normalizer.  The probable intended names are documentary only;
# they are deliberately not used as runtime aliases.
UNCLEAR_FEATURES: dict[str, dict[str, str]] = {
    "activityCalled": {
        "probable_training_meaning": (
            "Unknown aggregate or extraction-pipeline field named activityCalled; "
            "it is located inside the dataset-declared permission block."
        ),
        "reason": (
            "Not a permission constant, not an API signature, and no original "
            "extraction code or definition is present."
        ),
    },
    "AUTORUN_MANAGER_LICENSE_SERVICE(.autorun)": {
        "probable_training_meaning": "A vendor-specific autorun-service permission.",
        "reason": (
            "Embedded punctuation/dot means the runtime final-token normalizer "
            "cannot reproduce the full stored header."
        ),
    },
    "BIND_goodwareTIFICATION_LISTENER_SERVICE": {
        "probable_training_meaning": (
            "Probably BIND_NOTIFICATION_LISTENER_SERVICE with a corrupted header."
        ),
        "reason": (
            "Mixed-case 'goodware' insertion is present in the frozen header; "
            "upper-case normalization can never equal it."
        ),
    },
    "DIAGgoodwareSTIC": {
        "probable_training_meaning": "Probably DIAGNOSTIC with a corrupted header.",
        "reason": (
            "Mixed-case 'goodware' insertion is present in the frozen header; "
            "upper-case normalization can never equal it."
        ),
    },
    "DOWNLOAD_WITHOUT_goodwareTIFICATION": {
        "probable_training_meaning": (
            "Probably DOWNLOAD_WITHOUT_NOTIFICATION with a corrupted header."
        ),
        "reason": (
            "Mixed-case 'goodware' insertion is present in the frozen header; "
            "upper-case normalization can never equal it."
        ),
    },
    "FULLSCREEN.FULL": {
        "probable_training_meaning": "A vendor-specific full-screen permission.",
        "reason": (
            "The embedded dot makes the runtime normalizer return only FULL, so "
            "the complete frozen name is unreachable."
        ),
    },
    "Landroid/location/LocationManager;->getLastKgoodwarewnLocation": {
        "probable_training_meaning": (
            "Probably a reference to LocationManager.getLastKnownLocation with a "
            "corrupted method name."
        ),
        "reason": (
            "The stored method name is corrupted and the original extractor's "
            "matching rule is unavailable."
        ),
    },
}

# Standard Android permissions observed in the real-device WhatsApp snapshot
# but absent from the 241-name training contract.  This is a schema-gap
# inventory (classification D), not an input to the model.
MODERN_PERMISSIONS_NOT_REPRESENTED = [
    "android.permission.ACCESS_MEDIA_LOCATION",
    "android.permission.ANSWER_PHONE_CALLS",
    "android.permission.BLUETOOTH_CONNECT",
    "android.permission.DETECT_SCREEN_CAPTURE",
    "android.permission.DETECT_SCREEN_RECORDING",
    "android.permission.FOREGROUND_SERVICE",
    "android.permission.FOREGROUND_SERVICE_CAMERA",
    "android.permission.FOREGROUND_SERVICE_DATA_SYNC",
    "android.permission.FOREGROUND_SERVICE_LOCATION",
    "android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK",
    "android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION",
    "android.permission.FOREGROUND_SERVICE_MICROPHONE",
    "android.permission.FOREGROUND_SERVICE_PHONE_CALL",
    "android.permission.MANAGE_OWN_CALLS",
    "android.permission.NEARBY_WIFI_DEVICES",
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.READ_BASIC_PHONE_STATE",
    "android.permission.READ_MEDIA_AUDIO",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
    "android.permission.READ_PHONE_NUMBERS",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.RUN_USER_INITIATED_JOBS",
    "android.permission.SCHEDULE_EXACT_ALARM",
    "android.permission.USE_BIOMETRIC",
    "android.permission.USE_FULL_SCREEN_INTENT",
]

REAL_DEVICE_NORMALIZATION_AUDIT = {
    "captured_on": "2026-08-11",
    "package": "com.whatsapp",
    "submitted_permission_count": 85,
    "unique_normalized_token_count": 82,
    "matched_binary_model_feature_count": 46,
    "colliding_token_count": 3,
    "all_collisions_affect_binary_model_features": True,
    "collisions": [
        {
            "normalized_token": "INSTALL_SHORTCUT",
            "original_permissions": [
                "android.permission.INSTALL_SHORTCUT",
                "com.android.launcher.permission.INSTALL_SHORTCUT",
            ],
        },
        {
            "normalized_token": "READ",
            "original_permissions": [
                "com.sec.android.provider.badge.permission.READ",
                "com.whatsapp.sticker.READ",
            ],
        },
        {
            "normalized_token": "READ_SETTINGS",
            "original_permissions": [
                "com.htc.launcher.permission.READ_SETTINGS",
                "com.huawei.android.launcher.permission.READ_SETTINGS",
            ],
        },
    ],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ordered_feature_sha256(names: list[str]) -> str:
    payload = json.dumps(names, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def _method_meaning(name: str) -> str:
    owner, method = name.split(";->", 1)
    return f"Binary static reference to {owner[1:].replace('/', '.')}.{method}."


def _feature_row(index: int, name: str, importance: float) -> dict[str, Any]:
    if name in UNCLEAR_FEATURES:
        detail = UNCLEAR_FEATURES[name]
        return {
            "index": index,
            "feature_name": name,
            "classification": "C_unclear_corrupted_or_unreachable",
            "model_importance": importance,
            "probable_training_meaning": detail["probable_training_meaning"],
            "current_extraction_logic": "None that can activate this exact frozen name.",
            "uploaded_apk_reproducible_now": False,
            "installed_app_reproducible_now": False,
            "safe_static_observation_possible": name.startswith("L") and ";->" in name,
            "contract_faithful_recovery_supported": False,
            "requires_new_dependency_or_native_contract": name.startswith("L") and ";->" in name,
            "semantics_confidence": "low",
            "permanently_zero_today": True,
            "potentially_recoverable_without_retraining": False,
            "notes": detail["reason"],
        }

    if index >= 214:
        return {
            "index": index,
            "feature_name": name,
            "classification": "B_static_apk_code_potentially_observable",
            "model_importance": importance,
            "probable_training_meaning": _method_meaning(name),
            "current_extraction_logic": (
                "None; uploaded and installed-app routes currently submit manifest "
                "permissions only."
            ),
            "uploaded_apk_reproducible_now": False,
            "installed_app_reproducible_now": False,
            "safe_static_observation_possible": True,
            "contract_faithful_recovery_supported": False,
            "requires_new_dependency_or_native_contract": True,
            "semantics_confidence": "medium_for_reference_name_low_for_training_rule",
            "permanently_zero_today": True,
            "potentially_recoverable_without_retraining": False,
            "notes": (
                "A DEX method-reference parser can observe this signature without "
                "execution, but the repository does not establish whether training "
                "used references, invoke instructions, reachable calls, or another rule."
            ),
        }

    return {
        "index": index,
        "feature_name": name,
        "classification": "A_manifest_permission_reproducible",
        "model_importance": importance,
        "probable_training_meaning": (
            f"Binary presence of a declared permission whose final token is {name}."
        ),
        "current_extraction_logic": (
            "permission.strip().rsplit('.', 1)[-1].upper(), followed by exact "
            "binary-presence matching in model order."
        ),
        "uploaded_apk_reproducible_now": True,
        "installed_app_reproducible_now": True,
        "safe_static_observation_possible": True,
        "contract_faithful_recovery_supported": True,
        "requires_new_dependency_or_native_contract": False,
        "semantics_confidence": "high_for_runtime_matching_medium_for_historical_provenance",
        "permanently_zero_today": False,
        "potentially_recoverable_without_retraining": True,
        "notes": (
            "Original full permission strings remain available for display and "
            "diagnostics; final-token normalization can collide for vendor permissions."
        ),
    }


def build_audit() -> dict[str, Any]:
    model_sha256 = _sha256(MODEL_PATH)
    if model_sha256 != EXPECTED_MODEL_SHA256:
        raise ValueError("Frozen binary model SHA-256 changed; audit aborted.")

    estimator = joblib.load(MODEL_PATH)
    if isinstance(estimator, dict):
        estimator = (
            estimator.get("model")
            or estimator.get("estimator")
            or estimator.get("clf")
        )
    feature_names = [str(name) for name in estimator.feature_names_in_]
    importances = [float(value) for value in estimator.feature_importances_]
    if len(feature_names) != EXPECTED_FEATURE_COUNT:
        raise ValueError("Binary estimator no longer expects exactly 241 features.")
    feature_hash = _ordered_feature_sha256(feature_names)
    if feature_hash != EXPECTED_ORDERED_FEATURE_SHA256:
        raise ValueError("Frozen binary ordered feature contract changed; audit aborted.")

    rows = [
        _feature_row(index, name, importances[index])
        for index, name in enumerate(feature_names)
    ]
    group_keys = {
        "A_manifest_permission_reproducible",
        "B_static_apk_code_potentially_observable",
        "C_unclear_corrupted_or_unreachable",
    }
    group_summary = {}
    for group in sorted(group_keys):
        selected = [row for row in rows if row["classification"] == group]
        group_summary[group] = {
            "feature_count": len(selected),
            "model_importance_sum": sum(row["model_importance"] for row in selected),
        }

    non_manifest = [
        row for row in rows if row["feature_name"] == "activityCalled" or row["index"] >= 214
    ]
    permanently_zero = [row for row in rows if row["permanently_zero_today"]]
    return {
        "audit_version": 1,
        "audit_date": "2026-08-11",
        "decision": "CASE_B_CONTRACT_CANNOT_BE_REPRODUCED_RELIABLY",
        "binary_input_contract": "partial",
        "model": {
            "path": MODEL_PATH.relative_to(ROOT).as_posix(),
            "sha256": model_sha256,
            "estimator": type(estimator).__name__,
            "classes": [int(value) for value in estimator.classes_],
            "decision_threshold": 0.5,
            "feature_count": len(feature_names),
            "ordered_feature_contract_sha256": feature_hash,
        },
        "source_contract": {
            "dataset": "TUANDROMD",
            "uci_documented_permission_block": 214,
            "uci_documented_api_block": 27,
            "repository_original_extractor_found": False,
            "repository_training_provenance_sufficient_for_api_semantics": False,
        },
        "summary": {
            "dataset_declared_permission_block_features": 214,
            "artifact_non_manifest_features": len(non_manifest),
            "manifest_features_reproducible_by_current_runtime": group_summary[
                "A_manifest_permission_reproducible"
            ]["feature_count"],
            "exact_api_reference_names_potentially_observable_statically": group_summary[
                "B_static_apk_code_potentially_observable"
            ]["feature_count"],
            "unclear_corrupted_or_unreachable_features": group_summary[
                "C_unclear_corrupted_or_unreachable"
            ]["feature_count"],
            "non_manifest_model_importance_sum": sum(
                row["model_importance"] for row in non_manifest
            ),
            "permanently_zero_feature_count_today": len(permanently_zero),
            "permanently_zero_model_importance_sum_today": sum(
                row["model_importance"] for row in permanently_zero
            ),
            "contract_faithful_missing_features_implemented": 0,
        },
        "group_summary": group_summary,
        "runtime_capability": {
            "expected": 241,
            "available": 208,
            "missing": 33,
            "static_api_features_available": 0,
            "uploaded_apk_path": "manifest permissions only",
            "installed_app_path": "PackageManager requestedPermissions only",
        },
        "static_extraction_feasibility": {
            "uploaded_apk": (
                "DEX reference inspection is technically possible without execution, "
                "but is not implemented and cannot be asserted equivalent to training."
            ),
            "installed_app": (
                "Android ApplicationInfo.sourceDir and splitSourceDirs can identify "
                "installed APK files, but the protected native scanner does not expose "
                "or upload them and the training semantics remain unknown."
            ),
            "new_dependency": (
                "A DEX parser such as Androguard, or an equivalent audited parser, "
                "would be needed for structured method-reference analysis."
            ),
            "simple_string_search_rejected": True,
            "reference_vs_execution": (
                "Static analysis can prove that a reference/invoke instruction exists; "
                "it cannot prove that the method executes at runtime."
            ),
        },
        "normalization_audit": REAL_DEVICE_NORMALIZATION_AUDIT,
        "modern_permissions_not_represented": [
            {
                "permission": permission,
                "classification": "D_modern_permission_not_represented_by_training_schema",
            }
            for permission in MODERN_PERMISSIONS_NOT_REPRESENTED
        ],
        "features": rows,
        "sources": [
            {
                "title": "UCI TUANDROMD dataset page",
                "url": "https://archive.ics.uci.edu/dataset/855/tuandromd",
                "supports": "214 permission features and 27 API features",
            },
            {
                "title": "Androguard Analysis API",
                "url": "https://androguard.github.io/androguard/reference/androguard/core/analysis/analysis.html",
                "supports": "structured DEX class/method cross-reference analysis",
            },
            {
                "title": "Android ApplicationInfo API",
                "url": "https://developer.android.com/reference/android/content/pm/ApplicationInfo",
                "supports": "sourceDir and splitSourceDirs installed-APK paths",
            },
        ],
        "remediation_recommendation": [
            "Train and validate a genuinely permission-only binary model using the exact runtime normalizer and ordered schema.",
            "Alternatively, define and version a reproducible manifest-plus-DEX static feature extractor first, then retrain and validate a model on exactly that extractor's output.",
            "Do not retrofit guessed API flags into the current frozen estimator.",
        ],
    }


def main() -> None:
    payload = build_audit()
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

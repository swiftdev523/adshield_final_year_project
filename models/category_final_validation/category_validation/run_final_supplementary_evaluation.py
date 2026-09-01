"""Run the approved one-time supplementary holdout evaluation.

This program is fail-closed. It refuses to score unless every frozen input,
runtime, model, feature, and class-mapping precondition is satisfied. It also
refuses to run if the final-evaluation directory already exists.

The evaluation performs one ``predict`` call and one ``predict_proba`` call in
the same immutable scoring transaction. Probabilities are saved only as raw,
uncalibrated research diagnostics and are never described as confidence.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)


SCRIPT_PATH = Path(__file__).resolve()
CATEGORY_VALIDATION_DIR = SCRIPT_PATH.parent
PROJECT_ROOT = SCRIPT_PATH.parents[3]
HOLDOUT_DIR = CATEGORY_VALIDATION_DIR / "final_supplementary_holdout"
OUTPUT_DIR = CATEGORY_VALIDATION_DIR / "final_evaluation"
MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "category_final_validation"
    / "artifacts"
    / "selected_category_model_provisional.joblib"
)
RUN_MANIFEST_PATH = (
    PROJECT_ROOT
    / "models"
    / "category_final_validation"
    / "artifacts"
    / "run_manifest.json"
)
CV_RESULTS_PATH = (
    PROJECT_ROOT
    / "models"
    / "category_final_validation"
    / "artifacts"
    / "cv_results.json"
)

HOLDOUT_MANIFEST_NAME = "final_holdout_manifest.csv"
HOLDOUT_FEATURES_NAME = "final_holdout_features.csv"
HOLDOUT_REPORT_NAME = "final_holdout_selection_report.json"
HOLDOUT_HASHES_NAME = "final_holdout_sha256.txt"

METRICS_NAME = "final_evaluation_metrics.json"
REPORT_NAME = "final_evaluation_report.md"
CONFUSION_NAME = "final_confusion_matrix.csv"
PREDICTIONS_NAME = "final_predictions.csv"
OUTPUT_HASHES_NAME = "final_evaluation_artifacts_sha256.txt"
EVALUATION_STARTED_MARKER = ".one_time_evaluation_started.json"

EXPECTED_SKLEARN_VERSION = "1.6.1"
EXPECTED_MODEL_SHA256 = (
    "9b2f3b2a880372ff077fdc37e6e3d7909c9ba3ba28cabce371a58d1f6b80f3b9"
)
EXPECTED_FEATURE_COUNT = 153
EXPECTED_ORDERED_FEATURE_SHA256 = (
    "7aecf3b202c88d707e458a3705b4e3a326a9ee062c9b1e0f209a6b9a5c087c34"
)
EXPECTED_MODEL_CLASSES = [0, 1, 2, 3]
CLASS_NAMES = ["Adware", "Banking Malware", "SMS Malware", "Riskware"]
CLASS_TO_INDEX = {name: index for index, name in enumerate(CLASS_NAMES)}
EXPECTED_SAMPLES_PER_CLASS = 49
EXPECTED_SAMPLE_COUNT = 196
CV_MACRO_F1_REPORTED = 0.914532
CV_MACRO_F1_STORED = 0.9145319265188838
INTEGRATION_MACRO_F1_THRESHOLD = 0.80
INTEGRATION_MIN_RECALL_THRESHOLD = 0.70
HASH_LINE = re.compile(r"^([0-9a-f]{64})  ([^/\\]+)$")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def ordered_feature_hash(features: list[str]) -> str:
    payload = json.dumps(
        features, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(payload)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def csv_payload(fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=fieldnames, extrasaction="raise", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def verify_frozen_holdout_hashes() -> dict[str, dict[str, Any]]:
    hash_path = HOLDOUT_DIR / HOLDOUT_HASHES_NAME
    lines = hash_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 3:
        raise ValueError("Frozen holdout hash manifest must contain exactly three entries")
    expected_names = {
        HOLDOUT_MANIFEST_NAME,
        HOLDOUT_FEATURES_NAME,
        HOLDOUT_REPORT_NAME,
    }
    observed: dict[str, dict[str, Any]] = {}
    for line in lines:
        match = HASH_LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"Malformed frozen hash-manifest line: {line!r}")
        expected, name = match.groups()
        path = HOLDOUT_DIR / name
        if not path.is_file():
            raise FileNotFoundError(f"Frozen artifact is missing: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"Frozen artifact hash mismatch for {name}: expected {expected}, got {actual}"
            )
        observed[name] = {
            "bytes": path.stat().st_size,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "matches": True,
        }
    if set(observed) != expected_names:
        raise ValueError(f"Unexpected frozen hash-manifest names: {sorted(observed)}")
    observed[HOLDOUT_HASHES_NAME] = {
        "bytes": hash_path.stat().st_size,
        "sha256": sha256_file(hash_path),
        "note": "Checksum manifest is recorded separately and does not self-hash.",
    }
    return observed


def load_and_verify_holdout() -> tuple[list[dict[str, str]], list[str], np.ndarray]:
    manifest_fields, manifest_rows = read_csv(HOLDOUT_DIR / HOLDOUT_MANIFEST_NAME)
    feature_names, feature_rows = read_csv(HOLDOUT_DIR / HOLDOUT_FEATURES_NAME)
    selection_report = json.loads(
        (HOLDOUT_DIR / HOLDOUT_REPORT_NAME).read_text(encoding="utf-8")
    )

    if len(manifest_rows) != EXPECTED_SAMPLE_COUNT:
        raise ValueError("Frozen manifest must contain exactly 196 rows")
    if len(feature_rows) != EXPECTED_SAMPLE_COUNT:
        raise ValueError("Frozen features must contain exactly 196 rows")
    if len(feature_names) != EXPECTED_FEATURE_COUNT:
        raise ValueError("Frozen feature CSV must contain exactly 153 columns")
    if len(set(feature_names)) != EXPECTED_FEATURE_COUNT:
        raise ValueError("Frozen feature CSV contains duplicate feature columns")
    if ordered_feature_hash(feature_names) != EXPECTED_ORDERED_FEATURE_SHA256:
        raise ValueError("Frozen ordered feature-contract SHA-256 does not match")
    if selection_report["feature_contract"]["ordered_compact_json_sha256"] != (
        EXPECTED_ORDERED_FEATURE_SHA256
    ):
        raise ValueError("Frozen selection report records a different feature hash")

    required_manifest_fields = {
        "holdout_row_index",
        "class_name",
        "dataset_class_id",
        "model_class_index",
        "package",
        "normalized_package",
        "sha256",
        "positive_feature_count",
        "ordered_feature_contract_sha256",
    }
    if not required_manifest_fields.issubset(manifest_fields):
        raise ValueError("Frozen manifest is missing required fields")

    matrix = np.zeros((EXPECTED_SAMPLE_COUNT, EXPECTED_FEATURE_COUNT), dtype=np.uint8)
    for row_index, (manifest, feature_row) in enumerate(
        zip(manifest_rows, feature_rows, strict=True)
    ):
        if int(manifest["holdout_row_index"]) != row_index:
            raise ValueError("Manifest row order/index alignment changed")
        class_name = manifest["class_name"]
        if class_name not in CLASS_TO_INDEX:
            raise ValueError(f"Unexpected holdout class name: {class_name}")
        class_index = CLASS_TO_INDEX[class_name]
        if int(manifest["model_class_index"]) != class_index:
            raise ValueError("Manifest class name/model index mapping changed")
        if int(manifest["dataset_class_id"]) != class_index + 1:
            raise ValueError("Manifest dataset/model class mapping changed")
        if manifest["normalized_package"] != manifest["package"].strip().casefold():
            raise ValueError("Manifest normalized package does not use strip+casefold")
        if manifest["ordered_feature_contract_sha256"] != EXPECTED_ORDERED_FEATURE_SHA256:
            raise ValueError("Manifest row records a different feature-contract hash")
        values: list[int] = []
        for feature in feature_names:
            value = feature_row[feature]
            if value not in {"0", "1"}:
                raise ValueError(f"Non-binary frozen feature value: {feature}={value!r}")
            values.append(int(value))
        matrix[row_index] = np.asarray(values, dtype=np.uint8)
        positive_count = int(matrix[row_index].sum())
        if positive_count < 1:
            raise ValueError("Frozen holdout contains an all-zero feature vector")
        if int(manifest["positive_feature_count"]) != positive_count:
            raise ValueError("Manifest positive feature count differs from feature CSV")

    class_counts = Counter(row["class_name"] for row in manifest_rows)
    expected_counts = Counter(
        {class_name: EXPECTED_SAMPLES_PER_CLASS for class_name in CLASS_NAMES}
    )
    if class_counts != expected_counts:
        raise ValueError(f"Frozen class counts changed: {dict(class_counts)}")
    normalized_packages = [row["normalized_package"] for row in manifest_rows]
    if len(set(normalized_packages)) != EXPECTED_SAMPLE_COUNT:
        raise ValueError("Frozen normalized packages are not 196/196 unique")
    return manifest_rows, feature_names, matrix


def json_scalar(value: Any) -> int | float | str | bool | None:
    if isinstance(value, np.generic):
        return value.item()
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def load_and_verify_model(feature_names: list[str]) -> tuple[dict[str, Any], Any, list[int]]:
    if sklearn.__version__ != EXPECTED_SKLEARN_VERSION:
        raise RuntimeError(
            f"Runtime scikit-learn is {sklearn.__version__}; required {EXPECTED_SKLEARN_VERSION}"
        )
    current_model_sha = sha256_file(MODEL_PATH)
    if current_model_sha != EXPECTED_MODEL_SHA256:
        raise ValueError(
            f"Selected model hash changed: expected {EXPECTED_MODEL_SHA256}, got {current_model_sha}"
        )
    run_manifest = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8"))
    if run_manifest["selected_model_artifact_sha256"] != current_model_sha:
        raise ValueError("Current model hash differs from historical run_manifest.json")
    if run_manifest["selected_model_artifact"] != MODEL_PATH.name:
        raise ValueError("Historical run manifest names a different model artifact")
    if run_manifest["selected_model"] != "Random Forest":
        raise ValueError("Historical run manifest no longer selects Random Forest")
    if int(run_manifest["feature_count"]) != EXPECTED_FEATURE_COUNT:
        raise ValueError("Historical run manifest feature count is not 153")
    if run_manifest["feature_sha256"] != EXPECTED_ORDERED_FEATURE_SHA256:
        raise ValueError("Historical run manifest feature hash changed")
    if run_manifest["classes"] != CLASS_NAMES:
        raise ValueError("Historical run manifest class mapping changed")

    bundle = joblib.load(MODEL_PATH)
    if not isinstance(bundle, dict):
        raise TypeError("Selected model artifact is not the expected metadata bundle")
    if bundle.get("model_name") != "Random Forest":
        raise ValueError("Bundle model_name is not Random Forest")
    if bundle.get("scikit_learn_version") != EXPECTED_SKLEARN_VERSION:
        raise ValueError("Bundle was not exported under scikit-learn 1.6.1")
    if bundle.get("probabilities_calibrated") is not False:
        raise ValueError("Bundle probability-calibration metadata changed")
    if bundle.get("user_facing_confidence_allowed") is not False:
        raise ValueError("Bundle unexpectedly allows user-facing confidence")
    if bundle.get("feature_names") != feature_names:
        raise ValueError("Bundle feature names/order differ from frozen feature CSV")
    if len(bundle["feature_names"]) != EXPECTED_FEATURE_COUNT:
        raise ValueError("Bundle feature count is not 153")
    if bundle.get("feature_list_sha256") != EXPECTED_ORDERED_FEATURE_SHA256:
        raise ValueError("Bundle feature-list hash differs from required contract")
    if bundle.get("class_names_in_probability_order") != CLASS_NAMES:
        raise ValueError("Bundle class-name order differs from the approved mapping")

    model = bundle.get("model")
    if not isinstance(model, RandomForestClassifier):
        raise TypeError(f"Bundle estimator is not RandomForestClassifier: {type(model)!r}")
    if int(getattr(model, "n_features_in_", -1)) != EXPECTED_FEATURE_COUNT:
        raise ValueError("Random Forest n_features_in_ is not 153")
    raw_model_classes = [json_scalar(value) for value in model.classes_]
    if not np.issubdtype(model.classes_.dtype, np.integer):
        raise ValueError(
            f"model.classes_ must be numeric integer labels, got dtype {model.classes_.dtype}"
        )
    model_classes = [int(value) for value in raw_model_classes]
    if raw_model_classes != EXPECTED_MODEL_CLASSES or model_classes != EXPECTED_MODEL_CLASSES:
        raise ValueError(
            f"Unexpected/ambiguous model.classes_: {raw_model_classes}; expected numeric "
            "[0, 1, 2, 3]"
        )
    return bundle, model, model_classes


def metric_payload(
    actual: np.ndarray, predicted: np.ndarray
) -> tuple[dict[str, Any], np.ndarray]:
    labels = np.asarray(EXPECTED_MODEL_CLASSES, dtype=int)
    accuracy = float(accuracy_score(actual, predicted))
    macro_f1 = float(f1_score(actual, predicted, labels=labels, average="macro"))
    weighted_f1 = float(f1_score(actual, predicted, labels=labels, average="weighted"))
    balanced_accuracy = float(balanced_accuracy_score(actual, predicted))
    precision, recall, per_class_f1, support = precision_recall_fscore_support(
        actual,
        predicted,
        labels=labels,
        zero_division=0,
    )
    matrix = confusion_matrix(actual, predicted, labels=labels)

    if matrix.shape != (4, 4) or int(matrix.sum()) != EXPECTED_SAMPLE_COUNT:
        raise AssertionError("Confusion matrix shape/total is invalid")
    if not np.array_equal(matrix.sum(axis=1), np.full(4, EXPECTED_SAMPLES_PER_CLASS)):
        raise AssertionError("Confusion-matrix actual-class supports are not all 49")
    if not np.array_equal(support, np.full(4, EXPECTED_SAMPLES_PER_CLASS)):
        raise AssertionError("Per-class supports are not all 49")
    if not np.allclose(np.diag(matrix) / support, recall, atol=1e-15):
        raise AssertionError("Per-class recalls disagree with the confusion matrix")
    if not np.isclose(accuracy, np.trace(matrix) / matrix.sum(), atol=1e-15):
        raise AssertionError("Accuracy disagrees with the confusion matrix")
    if not np.isclose(balanced_accuracy, float(np.mean(recall)), atol=1e-15):
        raise AssertionError("Balanced accuracy disagrees with mean class recall")
    if not np.isclose(accuracy, balanced_accuracy, atol=1e-15):
        raise AssertionError("Balanced 49-per-class holdout must have accuracy=balanced accuracy")
    if not np.isclose(macro_f1, weighted_f1, atol=1e-15):
        raise AssertionError("Equal-support holdout must have macro F1=weighted F1")

    per_class = {
        CLASS_NAMES[index]: {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(per_class_f1[index]),
            "support": int(support[index]),
        }
        for index in range(4)
    }
    return (
        {
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "weighted_f1": weighted_f1,
            "balanced_accuracy": balanced_accuracy,
            "per_class": per_class,
        },
        matrix,
    )


def probability_column_name(class_name: str) -> str:
    slug = class_name.casefold().replace(" ", "_")
    return f"raw_uncalibrated_probability_{slug}"


def build_markdown_report(payload: dict[str, Any]) -> str:
    metrics = payload["metrics"]
    per_class = metrics["per_class"]
    matrix = payload["confusion_matrix"]["rows_actual_columns_predicted"]
    criterion = payload["experimental_integration_criterion"]
    comparison = payload["repeated_grouped_cv_comparison"]
    decision = "PASSED" if criterion["passed"] else "NOT PASSED"
    lines = [
        "# Final supplementary holdout evaluation",
        "",
        "## Outcome",
        "",
        f"The predeclared FYP experimental-integration criterion **{decision}**.",
        "",
        (
            "This criterion is a project-specific experimental prototype heuristic. "
            "It is **not** a production-security certification threshold."
        ),
        "",
        "## Immutable pre-prediction checks",
        "",
        f"- Model SHA-256: `{payload['preflight']['model']['sha256']}`",
        f"- Runtime scikit-learn: `{payload['preflight']['runtime']['scikit_learn']}`",
        f"- Model input features: `{payload['preflight']['model']['n_features_in']}`",
        (
            "- Ordered feature-contract SHA-256: "
            f"`{payload['preflight']['feature_contract']['ordered_sha256']}`"
        ),
        f"- `model.classes_`: `{payload['preflight']['model']['classes']}`",
        "- Verified class mapping: `0=Adware, 1=Banking Malware, 2=SMS Malware, 3=Riskware`",
        "- All frozen holdout hashes matched before prediction: `true`",
        "",
        "## Overall metrics",
        "",
        "Frozen holdout composition: **196 total samples; 49 per category**.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Accuracy | {metrics['accuracy']:.6f} |",
        f"| Macro F1 (primary) | {metrics['macro_f1']:.6f} |",
        f"| Weighted F1 | {metrics['weighted_f1']:.6f} |",
        f"| Balanced accuracy | {metrics['balanced_accuracy']:.6f} |",
        "",
        "## Per-class results",
        "",
        "| Category | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for class_name in CLASS_NAMES:
        item = per_class[class_name]
        lines.append(
            f"| {class_name} | {item['precision']:.6f} | {item['recall']:.6f} | "
            f"{item['f1']:.6f} | {item['support']} |"
        )
    lines.extend(
        [
            "",
            "## Confusion matrix",
            "",
            "Rows are actual categories; columns are predicted categories.",
            "",
            "| Actual / predicted | Adware | Banking Malware | SMS Malware | Riskware |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for index, class_name in enumerate(CLASS_NAMES):
        values = " | ".join(str(int(value)) for value in matrix[index])
        lines.append(f"| {class_name} | {values} |")
    lines.extend(
        [
            "",
            "## Banking and SMS recall",
            "",
            f"- Banking Malware recall: **{per_class['Banking Malware']['recall']:.6f}**",
            f"- SMS Malware recall: **{per_class['SMS Malware']['recall']:.6f}**",
            "",
            "## Repeated grouped-CV comparison",
            "",
            (
                f"The supplementary holdout Macro F1 is `{metrics['macro_f1']:.6f}`. "
                f"The previously reported repeated grouped-CV Random Forest Macro F1 was "
                f"`{comparison['baseline_macro_f1_reported']:.6f}`."
            ),
            "",
            (
                f"Holdout minus repeated-CV Macro F1: "
                f"`{comparison['holdout_minus_reported_baseline']:+.6f}` "
                f"({comparison['difference_percentage_points']:+.4f} percentage points)."
            ),
            "",
            "This is a descriptive comparison only; no statistical-significance claim is made.",
            "",
            "## Predeclared experimental-integration criterion",
            "",
            f"- Macro F1 >= 0.80: `{str(criterion['macro_f1_requirement_passed']).lower()}`",
            (
                "- Recall >= 0.70 for every supported category: "
                f"`{str(criterion['all_class_recall_requirement_passed']).lower()}`"
            ),
            f"- Lowest category recall: `{criterion['minimum_class_recall']:.6f}`",
            f"- Overall decision: **{decision}**",
            "",
            (
                "Passing this heuristic supports experimental prototype integration only. "
                "It does not certify production malware-detection safety or security."
            ),
            "",
            "## Raw probability diagnostics",
            "",
            (
                "`final_predictions.csv` contains raw `predict_proba` outputs. They are "
                "uncalibrated research diagnostics, conditional on the upstream detector and "
                "the true category being one of the four supported classes. They are not "
                "calibrated confidence values and must not be presented to users as confidence."
            ),
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["limitations"])
    lines.extend(
        [
            "",
            "## Non-actions",
            "",
            "- No retraining, calibration, threshold change, tuning, or sample reselection occurred.",
            "- The selected Random Forest and frozen holdout artifacts were not modified.",
            "- No FastAPI integration was performed.",
            "- This holdout must not be reused to choose a changed model.",
            "",
        ]
    )
    return "\n".join(lines)


def reserve_one_time_evaluation() -> Path:
    """Atomically consume the one-time run immediately before inference."""

    OUTPUT_DIR.mkdir(parents=False, exist_ok=False)
    marker = OUTPUT_DIR / EVALUATION_STARTED_MARKER
    marker_payload = {
        "status": "one_time_evaluation_reserved_before_prediction",
        "model_sha256": EXPECTED_MODEL_SHA256,
        "holdout_manifest_sha256": sha256_file(HOLDOUT_DIR / HOLDOUT_MANIFEST_NAME),
        "holdout_features_sha256": sha256_file(HOLDOUT_DIR / HOLDOUT_FEATURES_NAME),
        "note": (
            "Directory existence permanently prevents an automatic rerun if the process "
            "fails after model inference starts."
        ),
    }
    marker.write_text(
        json.dumps(marker_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return marker


def write_new_results(payloads: dict[str, bytes]) -> None:
    if not OUTPUT_DIR.is_dir():
        raise FileNotFoundError("The one-time evaluation directory was not reserved")
    existing_results = [name for name in payloads if (OUTPUT_DIR / name).exists()]
    if existing_results:
        raise FileExistsError(
            f"Refusing to overwrite one-time evaluation results: {existing_results}"
        )
    for name, payload in payloads.items():
        target = OUTPUT_DIR / name
        temporary = target.with_name(f".{target.name}.tmp")
        try:
            temporary.write_bytes(payload)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> int:
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"One-time evaluation directory already exists; refusing to run: {OUTPUT_DIR}"
        )
    if sklearn.__version__ != EXPECTED_SKLEARN_VERSION:
        raise RuntimeError(
            f"Wrong evaluation runtime: scikit-learn {sklearn.__version__}; "
            f"required {EXPECTED_SKLEARN_VERSION}"
        )

    print("Preflight: verifying frozen holdout hashes...", flush=True)
    frozen_hashes_before = verify_frozen_holdout_hashes()
    manifest_rows, feature_names, features = load_and_verify_holdout()
    print("Preflight: verifying selected model hash, bundle, width, and classes...", flush=True)
    bundle, model, model_classes = load_and_verify_model(feature_names)
    cv_results = json.loads(CV_RESULTS_PATH.read_text(encoding="utf-8"))
    selected_cv_mean = float(cv_results["selection"]["leader_mean_macro_f1"])
    if cv_results["selection"]["selected_model"] != "Random Forest":
        raise AssertionError("Repeated-CV selection no longer identifies Random Forest")
    if not np.isclose(selected_cv_mean, CV_MACRO_F1_STORED, atol=1e-15, rtol=0.0):
        raise AssertionError("Stored repeated-CV Random Forest Macro F1 changed")

    class_mapping = {
        str(model_class): CLASS_NAMES[position]
        for position, model_class in enumerate(model_classes)
    }
    runtime_metadata = {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(),
        "scikit_learn": sklearn.__version__,
        "required_scikit_learn": EXPECTED_SKLEARN_VERSION,
        "exact_version_match": sklearn.__version__ == EXPECTED_SKLEARN_VERSION,
        "joblib": joblib.__version__,
        "numpy": np.__version__,
    }
    model_metadata = {
        "path": project_relative(MODEL_PATH),
        "bytes": MODEL_PATH.stat().st_size,
        "sha256": EXPECTED_MODEL_SHA256,
        "matches_historical_run_manifest": True,
        "bundle_model_name": bundle["model_name"],
        "estimator_type": type(model).__name__,
        "n_features_in": int(model.n_features_in_),
        "classes": model_classes,
        "class_dtype": str(model.classes_.dtype),
        "class_mapping": class_mapping,
        "n_estimators": int(model.n_estimators),
        "max_features": json_scalar(model.max_features),
        "random_state": json_scalar(model.random_state),
        "probabilities_calibrated": False,
    }
    evaluation_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    print(f"Pre-prediction model SHA-256: {EXPECTED_MODEL_SHA256}", flush=True)
    print(f"Pre-prediction scikit-learn: {sklearn.__version__}", flush=True)
    print(f"Pre-prediction n_features_in_: {model.n_features_in_}", flush=True)
    print(f"Pre-prediction model.classes_: {model_classes}", flush=True)
    print(f"Pre-prediction verified class mapping: {class_mapping}", flush=True)
    started_marker = reserve_one_time_evaluation()
    print("All gates passed. Starting the single approved evaluation transaction...", flush=True)

    actual = np.asarray(
        [int(row["model_class_index"]) for row in manifest_rows], dtype=int
    )
    # Exactly one call to each approved inference API in this one evaluation.
    raw_predictions = np.asarray(model.predict(features), dtype=int)
    raw_probabilities = np.asarray(model.predict_proba(features), dtype=np.float64)

    if raw_predictions.shape != (EXPECTED_SAMPLE_COUNT,):
        raise AssertionError("model.predict returned an unexpected shape")
    if raw_probabilities.shape != (EXPECTED_SAMPLE_COUNT, len(model_classes)):
        raise AssertionError("model.predict_proba returned an unexpected shape")
    if not np.isfinite(raw_probabilities).all():
        raise AssertionError("Raw probabilities contain a non-finite value")
    if np.any(raw_probabilities < 0.0) or np.any(raw_probabilities > 1.0):
        raise AssertionError("Raw probabilities fall outside [0, 1]")
    if not np.allclose(raw_probabilities.sum(axis=1), 1.0, atol=1e-12):
        raise AssertionError("Raw probability rows do not sum to one")
    argmax_predictions = np.asarray(model_classes, dtype=int)[
        np.argmax(raw_probabilities, axis=1)
    ]
    if not np.array_equal(raw_predictions, argmax_predictions):
        raise AssertionError("model.predict disagrees with predict_proba argmax/classes_ mapping")
    if not np.isin(raw_predictions, model_classes).all():
        raise AssertionError("A prediction is outside model.classes_")

    metrics, matrix = metric_payload(actual, raw_predictions)
    minimum_recall = min(
        item["recall"] for item in metrics["per_class"].values()
    )
    macro_requirement = metrics["macro_f1"] >= INTEGRATION_MACRO_F1_THRESHOLD
    recall_requirement = minimum_recall >= INTEGRATION_MIN_RECALL_THRESHOLD
    criterion_passed = bool(macro_requirement and recall_requirement)
    delta_reported = metrics["macro_f1"] - CV_MACRO_F1_REPORTED
    delta_stored = metrics["macro_f1"] - CV_MACRO_F1_STORED

    frozen_hashes_after = verify_frozen_holdout_hashes()
    if frozen_hashes_after != frozen_hashes_before:
        raise AssertionError("Frozen holdout fingerprints changed during evaluation")
    model_sha_after = sha256_file(MODEL_PATH)
    if model_sha_after != EXPECTED_MODEL_SHA256:
        raise AssertionError("Selected model bytes changed during evaluation")

    prediction_fields = [
        "holdout_row_index",
        "package",
        "normalized_package",
        "sha256",
        "source_type",
        "positive_feature_count",
        "true_model_class_index",
        "true_class_name",
        "raw_model_prediction",
        "predicted_model_class_index",
        "predicted_class_name",
        "correct",
        *[probability_column_name(name) for name in CLASS_NAMES],
        "raw_max_probability_not_calibrated",
    ]
    prediction_rows: list[dict[str, Any]] = []
    for row_index, manifest in enumerate(manifest_rows):
        predicted_index = int(raw_predictions[row_index])
        row: dict[str, Any] = {
            "holdout_row_index": row_index,
            "package": manifest["package"],
            "normalized_package": manifest["normalized_package"],
            "sha256": manifest["sha256"],
            "source_type": manifest.get("source_type", ""),
            "positive_feature_count": manifest["positive_feature_count"],
            "true_model_class_index": int(actual[row_index]),
            "true_class_name": CLASS_NAMES[int(actual[row_index])],
            "raw_model_prediction": predicted_index,
            "predicted_model_class_index": predicted_index,
            "predicted_class_name": CLASS_NAMES[predicted_index],
            "correct": str(predicted_index == int(actual[row_index])).lower(),
        }
        for class_position, class_name in enumerate(CLASS_NAMES):
            row[probability_column_name(class_name)] = format(
                float(raw_probabilities[row_index, class_position]), ".17g"
            )
        row["raw_max_probability_not_calibrated"] = format(
            float(raw_probabilities[row_index].max()), ".17g"
        )
        prediction_rows.append(row)

    confusion_rows = [
        {
            "actual_class": class_name,
            **{
                predicted_name: int(matrix[actual_index, predicted_index])
                for predicted_index, predicted_name in enumerate(CLASS_NAMES)
            },
        }
        for actual_index, class_name in enumerate(CLASS_NAMES)
    ]

    limitations = [
        (
            "The holdout contains only 49 packages per class; one additional error changes "
            "a class recall by about 2.04 percentage points."
        ),
        (
            "The balanced 49/49/49/49 class distribution is an evaluation design and does "
            "not represent real-world malware-family prevalence."
        ),
        (
            "This is a within-CICMalDroid supplementary holdout with mixed static-source and "
            "Kali APK-extraction provenance, not a fully independent external dataset."
        ),
        (
            "Adware/Riskware labels rely on documented positional alignment; Banking/SMS "
            "labels are inherited from audited source folders rather than independent "
            "multi-engine family adjudication."
        ),
        (
            "Only Banking and SMS samples have linkable APK SHA-256 evidence, covering "
            "98 of 196 holdout samples."
        ),
        (
            "Package-disjoint grouping cannot prove that differently named packages are not "
            "repackaged or closely related variants."
        ),
        (
            "The model uses only 153 static permission-presence features and cannot observe "
            "code behavior, payloads, URLs, runtime actions, or other static structures."
        ),
        (
            "The classifier is closed-set: unsupported malware families are forced into one "
            "of Adware, Banking Malware, SMS Malware, or Riskware."
        ),
        (
            "Raw probabilities are uncalibrated and conditional on the upstream binary "
            "detector already classifying the application as malicious."
        ),
        (
            "This one-time holdout must not be reused for model, threshold, feature, or "
            "hyperparameter selection."
        ),
    ]

    metrics_payload: dict[str, Any] = {
        "status": "completed_one_time_final_supplementary_evaluation",
        "evaluated_at_utc": evaluation_time,
        "evaluation_identity": {
            "model_sha256": EXPECTED_MODEL_SHA256,
            "holdout_manifest_sha256": frozen_hashes_before[HOLDOUT_MANIFEST_NAME][
                "actual_sha256"
            ],
            "holdout_features_sha256": frozen_hashes_before[HOLDOUT_FEATURES_NAME][
                "actual_sha256"
            ],
        },
        "preflight": {
            "all_gates_passed_before_prediction": True,
            "frozen_holdout_artifacts": frozen_hashes_before,
            "runtime": runtime_metadata,
            "feature_contract": {
                "count": len(feature_names),
                "ordered_sha256": ordered_feature_hash(feature_names),
                "required_ordered_sha256": EXPECTED_ORDERED_FEATURE_SHA256,
                "exact_match": ordered_feature_hash(feature_names)
                == EXPECTED_ORDERED_FEATURE_SHA256,
                "feature_header_equals_bundle_feature_names": True,
            },
            "model": model_metadata,
            "holdout": {
                "rows": len(manifest_rows),
                "features": int(features.shape[1]),
                "class_counts": dict(
                    Counter(row["class_name"] for row in manifest_rows)
                ),
                "manifest_indices_are_0_through_195": True,
                "manifest_feature_row_alignment_preserved": True,
                "all_features_binary": True,
                "no_all_zero_vectors": True,
            },
        },
        "inference": {
            "evaluation_transactions": 1,
            "predict_calls": 1,
            "predict_proba_calls": 1,
            "predict_matches_predict_proba_argmax": True,
            "raw_probabilities_saved": True,
            "raw_probabilities_calibrated": False,
            "raw_probability_disclaimer": (
                "Raw four-class research diagnostics only; not calibrated confidence."
            ),
        },
        "metrics": metrics,
        "confusion_matrix": {
            "labels": CLASS_NAMES,
            "orientation": "rows actual; columns predicted",
            "rows_actual_columns_predicted": matrix.astype(int).tolist(),
        },
        "experimental_integration_criterion": {
            "name": "predeclared FYP prototype heuristic",
            "macro_f1_threshold": INTEGRATION_MACRO_F1_THRESHOLD,
            "minimum_recall_each_supported_category": INTEGRATION_MIN_RECALL_THRESHOLD,
            "observed_macro_f1": metrics["macro_f1"],
            "minimum_class_recall": minimum_recall,
            "macro_f1_requirement_passed": bool(macro_requirement),
            "all_class_recall_requirement_passed": bool(recall_requirement),
            "passed": criterion_passed,
            "scope_disclaimer": (
                "Project-specific experimental integration criterion; not a "
                "production-security certification threshold."
            ),
        },
        "repeated_grouped_cv_comparison": {
            "model": "Random Forest",
            "baseline_macro_f1_reported": CV_MACRO_F1_REPORTED,
            "baseline_macro_f1_stored_unrounded": CV_MACRO_F1_STORED,
            "holdout_macro_f1": metrics["macro_f1"],
            "holdout_minus_reported_baseline": delta_reported,
            "holdout_minus_stored_unrounded_baseline": delta_stored,
            "difference_percentage_points": 100.0 * delta_reported,
            "comparison_type": "descriptive only; no significance claim",
        },
        "limitations": limitations,
        "post_inference_integrity": {
            "frozen_holdout_hashes_unchanged": True,
            "selected_model_hash_unchanged": model_sha_after == EXPECTED_MODEL_SHA256,
            "selected_model_sha256_after": model_sha_after,
        },
        "non_actions": {
            "model_retrained": False,
            "model_calibrated": False,
            "hyperparameters_tuned": False,
            "thresholds_changed": False,
            "holdout_modified": False,
            "labels_modified": False,
            "sample_selection_modified": False,
            "fastapi_integrated": False,
        },
    }

    metrics_bytes = (
        json.dumps(metrics_payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    ).encode("utf-8")
    report_bytes = build_markdown_report(metrics_payload).encode("utf-8")
    confusion_bytes = csv_payload(
        ["actual_class", *CLASS_NAMES], confusion_rows
    )
    predictions_bytes = csv_payload(prediction_fields, prediction_rows)
    result_payloads = {
        METRICS_NAME: metrics_bytes,
        REPORT_NAME: report_bytes,
        CONFUSION_NAME: confusion_bytes,
        PREDICTIONS_NAME: predictions_bytes,
    }
    output_hashes = {name: sha256_bytes(payload) for name, payload in result_payloads.items()}
    hashes_bytes = "".join(
        f"{output_hashes[name]}  {name}\n"
        for name in (METRICS_NAME, REPORT_NAME, CONFUSION_NAME, PREDICTIONS_NAME)
    ).encode("utf-8")
    result_payloads[OUTPUT_HASHES_NAME] = hashes_bytes
    write_new_results(result_payloads)

    for name, expected_hash in output_hashes.items():
        actual_hash = sha256_file(OUTPUT_DIR / name)
        if actual_hash != expected_hash:
            raise AssertionError(f"Published result hash mismatch for {name}")
    if (OUTPUT_DIR / OUTPUT_HASHES_NAME).read_bytes() != hashes_bytes:
        raise AssertionError("Published result checksum manifest bytes changed")
    if verify_frozen_holdout_hashes() != frozen_hashes_before:
        raise AssertionError("Frozen holdout changed after publishing results")
    if sha256_file(MODEL_PATH) != EXPECTED_MODEL_SHA256:
        raise AssertionError("Selected model changed after publishing results")
    started_marker.unlink()

    print("One-time evaluation completed and results were frozen.", flush=True)
    print(f"Macro F1: {metrics['macro_f1']:.12f}", flush=True)
    print(f"Banking recall: {metrics['per_class']['Banking Malware']['recall']:.12f}", flush=True)
    print(f"SMS recall: {metrics['per_class']['SMS Malware']['recall']:.12f}", flush=True)
    print(f"Experimental criterion passed: {criterion_passed}", flush=True)
    print(f"Results: {OUTPUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

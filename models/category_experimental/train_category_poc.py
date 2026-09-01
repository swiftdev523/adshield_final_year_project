"""Offline CICMalDroid 2020 malware-category proof of concept.

This experiment is deliberately isolated from the production FastAPI service and
the existing benign/malware detectors.  It reads only:

* ``feature_vectors_static.csv`` for static permission values and package names;
* the ``Class`` column from each accompanying 5-category CSV to validate the
  positional category-label assumption; and
* the existing APK detector's feature names, read-only, to define the permission
  vocabulary that the current APK pipeline can reproduce.

No syscall, Binder, or other dynamic value is used as a model input.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import sys
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedGroupKFold


SCRIPT_PATH = Path(__file__).resolve()
OUTPUT_DIR = SCRIPT_PATH.parent
PROJECT_ROOT = SCRIPT_PATH.parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "datasets"

STATIC_CSV = DATA_DIR / "feature_vectors_static.csv"
SYSCALL_CLASS_CSV = DATA_DIR / "feature_vectors_syscalls_frequency_5_Cat.csv"
BINDER_CLASS_CSV = DATA_DIR / "feature_vectors_syscallsbinders_frequency_5_Cat.csv"
CURRENT_APK_MODEL = PROJECT_ROOT / "models" / "adware_detection_rf_model.pkl"

RANDOM_STATE = 42
INNER_RANDOM_STATE = 43
EXPECTED_STATIC_ROWS = 11_598
EXPECTED_STATIC_COLUMNS = 50_621
EXPECTED_FEATURE_COUNT = 153
EXPECTED_CLASS_RUNS = {1: 1_253, 2: 2_100, 3: 3_904, 4: 2_546, 5: 1_795}
DATASET_CLASS_NAMES = {
    1: "Adware",
    2: "Banking Malware",
    3: "SMS Malware",
    4: "Riskware",
    5: "Benign",
}
MODEL_CLASS_NAMES = ["Adware", "Banking Malware", "SMS Malware", "Riskware"]
DATASET_TO_MODEL_CLASS = {dataset_id: dataset_id - 1 for dataset_id in range(1, 5)}

# The natural data is group-stratified first.  Only then is each already assigned
# partition downsampled to make the requested balanced 1,000-sample-per-class POC.
SPLIT_QUOTAS_PER_CLASS = {"train": 600, "validation": 200, "test": 200}
MAX_ROWS_PER_PACKAGE_GROUP = 8

PERMISSION_HEADER_RE = re.compile(
    r"android\.permission\.([A-Z0-9_]+)", re.IGNORECASE
)


def log(message: str) -> None:
    print(message, flush=True)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def decode_utf7_header(value: str) -> str:
    """Decode the dataset's UTF-7-like header artifacts when possible."""

    try:
        return value.encode("ascii").decode("utf-7")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def load_static_header() -> list[str]:
    with STATIC_CSV.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        header = next(csv.reader(handle))
    if len(header) != EXPECTED_STATIC_COLUMNS:
        raise ValueError(
            f"Unexpected static header width: {len(header):,}; "
            f"expected {EXPECTED_STATIC_COLUMNS:,}."
        )
    return header


def unwrap_model(bundle: Any) -> Any:
    if not isinstance(bundle, dict):
        return bundle
    for key in ("model", "estimator", "clf"):
        if bundle.get(key) is not None:
            return bundle[key]
    raise ValueError("Existing APK model bundle does not contain a supported estimator key.")


def current_pipeline_feature_names() -> list[str]:
    """Read the current binary APK model vocabulary without changing the model."""

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        estimator = unwrap_model(joblib.load(CURRENT_APK_MODEL))
    names = [str(name) for name in getattr(estimator, "feature_names_in_", [])]
    if not names:
        raise ValueError("Existing APK model does not expose feature_names_in_.")
    return names


def build_permission_mapping(
    raw_header: list[str], pipeline_feature_names: Iterable[str]
) -> tuple[list[str], dict[str, list[int]], list[dict[str, Any]]]:
    """Return ordered canonical features and all source columns for each feature."""

    allowed_bare = set(pipeline_feature_names)
    source_by_bare: dict[str, list[int]] = defaultdict(list)
    decoded_header = [decode_utf7_header(value).strip() for value in raw_header]

    for column_index, decoded in enumerate(decoded_header):
        match = PERMISSION_HEADER_RE.fullmatch(decoded)
        if match:
            # Match the production normalizer: permission suffixes are uppercased
            # before feature lookup. This also merges mixed-case source aliases.
            bare = match.group(1).upper()
            if bare in allowed_bare:
                source_by_bare[bare].append(column_index)

    bare_features = sorted(source_by_bare)
    if len(bare_features) != EXPECTED_FEATURE_COUNT:
        raise ValueError(
            f"Permission overlap changed: found {len(bare_features)}, "
            f"expected {EXPECTED_FEATURE_COUNT}."
        )

    canonical_features = [f"android.permission.{name}" for name in bare_features]
    mapping_records: list[dict[str, Any]] = []
    for canonical, bare in zip(canonical_features, bare_features, strict=True):
        columns = source_by_bare[bare]
        mapping_records.append(
            {
                "feature": canonical,
                "bare_name": bare,
                "aggregation": "logical OR after numeric/boolean value > 0",
                "source_columns": [
                    {
                        "zero_based_index": index,
                        "raw_header": raw_header[index],
                        "decoded_header": decoded_header[index],
                    }
                    for index in columns
                ],
            }
        )
    return canonical_features, dict(source_by_bare), mapping_records


def parse_presence_column(series: pd.Series) -> tuple[np.ndarray, int]:
    """Convert one sparse count/boolean permission column to binary presence."""

    text = series.fillna("").astype(str).str.strip()
    lower = text.str.casefold()
    booleans = lower.map({"true": 1.0, "false": 0.0})
    numeric = pd.to_numeric(text, errors="coerce")
    values = numeric.where(numeric.notna(), booleans)
    invalid = int((text.ne("") & values.isna()).sum())
    return (values.fillna(0.0).to_numpy(dtype=np.float64) > 0.0), invalid


def read_static_permission_data(
    source_by_bare: dict[str, list[int]],
    canonical_features: list[str],
    package_column_index: int,
    chunk_rows: int = 2_048,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Stream selected columns and immediately reduce them to compact arrays."""

    selected_indices = sorted(
        {
            0,
            package_column_index,
            *(index for indices in source_by_bare.values() for index in indices),
        }
    )
    log(
        f"Reading {len(selected_indices)} selected columns from the "
        f"{STATIC_CSV.stat().st_size / (1024 ** 2):.1f} MiB static CSV "
        f"in {chunk_rows:,}-row chunks..."
    )
    reader = pd.read_csv(
        STATIC_CSV,
        usecols=selected_indices,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
        chunksize=chunk_rows,
    )
    index_parts: list[np.ndarray] = []
    package_parts: list[np.ndarray] = []
    matrix_parts: list[np.ndarray] = []
    invalid_totals: Counter[str] = Counter()

    for frame in reader:
        # Integer usecols are returned in physical file order. Positional names
        # avoid Pandas' suffixes for the source file's duplicate header strings.
        if frame.shape[1] != len(selected_indices):
            raise ValueError(
                f"Selected-column chunk returned {frame.shape[1]} columns; "
                f"expected {len(selected_indices)}."
            )
        frame.columns = [f"column_{index}" for index in selected_indices]
        index_parts.append(
            pd.to_numeric(frame["column_0"], errors="raise").to_numpy(dtype=np.int64)
        )
        package_parts.append(
            frame[f"column_{package_column_index}"]
            .fillna("")
            .astype(str)
            .str.strip()
            .to_numpy()
        )
        matrix, invalid = build_permission_matrix(
            frame, canonical_features, source_by_bare
        )
        matrix_parts.append(matrix)
        invalid_totals.update(invalid)

    return (
        np.concatenate(index_parts),
        np.concatenate(package_parts),
        np.vstack(matrix_parts),
        dict(invalid_totals),
    )


def build_permission_matrix(
    selected: pd.DataFrame,
    canonical_features: list[str],
    source_by_bare: dict[str, list[int]],
) -> tuple[np.ndarray, dict[str, int]]:
    matrix = np.zeros((len(selected), len(canonical_features)), dtype=np.uint8)
    invalid_by_feature: dict[str, int] = {}

    for feature_index, canonical in enumerate(canonical_features):
        bare = canonical.rsplit(".", 1)[-1]
        aggregate = np.zeros(len(selected), dtype=bool)
        invalid_count = 0
        for source_index in source_by_bare[bare]:
            present, invalid = parse_presence_column(selected[f"column_{source_index}"])
            aggregate |= present
            invalid_count += invalid
        matrix[:, feature_index] = aggregate.astype(np.uint8)
        if invalid_count:
            invalid_by_feature[canonical] = invalid_count
    return matrix, invalid_by_feature


def read_and_verify_labels() -> tuple[np.ndarray, dict[str, Any]]:
    """Read only Class columns and enforce every positional-alignment invariant."""

    syscall = pd.to_numeric(
        pd.read_csv(SYSCALL_CLASS_CSV, usecols=["Class"])["Class"], errors="raise"
    ).astype(int)
    binder = pd.to_numeric(
        pd.read_csv(BINDER_CLASS_CSV, usecols=["Class"])["Class"], errors="raise"
    ).astype(int)

    if len(syscall) != EXPECTED_STATIC_ROWS or len(binder) != EXPECTED_STATIC_ROWS:
        raise ValueError("Class files do not have the expected 11,598 rows.")
    if not np.array_equal(syscall.to_numpy(), binder.to_numpy()):
        raise ValueError("The two accompanying Class columns disagree by row.")

    expected = np.concatenate(
        [np.full(count, class_id, dtype=np.int8) for class_id, count in EXPECTED_CLASS_RUNS.items()]
    )
    actual = syscall.to_numpy(dtype=np.int8)
    if not np.array_equal(actual, expected):
        raise ValueError("Class order/runs do not match the documented CICMalDroid counts.")

    audit = {
        "status": "verified_positional_invariants_with_documented_assumption",
        "static_rows_expected": EXPECTED_STATIC_ROWS,
        "class_vectors_identical": True,
        "expected_and_observed_class_runs": {
            str(class_id): {
                "name": DATASET_CLASS_NAMES[class_id],
                "rows": count,
            }
            for class_id, count in EXPECTED_CLASS_RUNS.items()
        },
        "dynamic_input_features_used": False,
        "class_columns_only": True,
        "assumption": (
            "feature_vectors_static.csv contains no label or hash. Labels are attached by row "
            "position because the static matrix and both accompanying 5-category files have "
            "exactly 11,598 rows, both Class vectors match row-for-row, and their contiguous "
            "class runs exactly match the category counts and order published for "
            "CICMalDroid 2020. This is strong positional evidence, not an independently keyed "
            "hash join."
        ),
        "official_reference": "https://www.unb.ca/cic/datasets/maldroid-2020.html",
    }
    return actual, audit


def identify_cross_label_packages(
    packages: np.ndarray, labels: np.ndarray
) -> tuple[set[str], list[dict[str, Any]]]:
    frame = pd.DataFrame({"package": packages, "class_id": labels})
    frame = frame[frame["package"].ne("")]
    conflicts: list[dict[str, Any]] = []
    for package, group in frame.groupby("package", sort=True):
        counts = group["class_id"].value_counts().sort_index()
        if len(counts) > 1:
            conflicts.append(
                {
                    "package": package,
                    "total_rows": int(len(group)),
                    "class_counts": {
                        DATASET_CLASS_NAMES[int(class_id)]: int(count)
                        for class_id, count in counts.items()
                    },
                }
            )
    return {record["package"] for record in conflicts}, conflicts


def make_group_ids(packages: np.ndarray, source_rows: np.ndarray) -> np.ndarray:
    return np.asarray(
        [package if package else f"__missing_package_row_{row}" for package, row in zip(packages, source_rows, strict=True)],
        dtype=object,
    )


def class_counts(values: np.ndarray) -> dict[str, int]:
    counts = Counter(int(value) for value in values)
    return {DATASET_CLASS_NAMES[class_id]: int(counts.get(class_id, 0)) for class_id in range(1, 5)}


def choose_closest_group_fold(
    splits: Iterable[tuple[np.ndarray, np.ndarray]],
    labels: np.ndarray,
    target_fraction: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    total_by_class = Counter(int(value) for value in labels)
    candidates: list[tuple[float, int, np.ndarray, np.ndarray, dict[str, Any]]] = []
    for fold_index, (remaining, held_out) in enumerate(splits):
        held_counts = Counter(int(value) for value in labels[held_out])
        class_fractions = {
            class_id: held_counts.get(class_id, 0) / total_by_class[class_id]
            for class_id in range(1, 5)
        }
        score = sum(abs(class_fractions[class_id] - target_fraction) for class_id in range(1, 5))
        details = {
            "fold_index": fold_index,
            "target_fraction": target_fraction,
            "score_absolute_class_fraction_error": float(score),
            "held_out_counts": {
                DATASET_CLASS_NAMES[class_id]: int(held_counts.get(class_id, 0))
                for class_id in range(1, 5)
            },
            "held_out_class_fractions": {
                DATASET_CLASS_NAMES[class_id]: float(class_fractions[class_id])
                for class_id in range(1, 5)
            },
        }
        candidates.append((score, fold_index, remaining, held_out, details))
    _, _, remaining, held_out, details = min(candidates, key=lambda item: (item[0], item[1]))
    return remaining, held_out, details


def natural_group_stratified_splits(
    labels: np.ndarray, group_ids: np.ndarray
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    train_validation, test, outer_details = choose_closest_group_fold(
        outer.split(np.zeros(len(labels), dtype=np.uint8), labels, group_ids),
        labels,
        target_fraction=0.20,
    )

    inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=INNER_RANDOM_STATE)
    inner_remaining, inner_validation, inner_details = choose_closest_group_fold(
        inner.split(
            np.zeros(len(train_validation), dtype=np.uint8),
            labels[train_validation],
            group_ids[train_validation],
        ),
        labels[train_validation],
        target_fraction=0.25,
    )
    train = train_validation[inner_remaining]
    validation = train_validation[inner_validation]

    splits = {"train": train, "validation": validation, "test": test}
    group_sets = {name: set(group_ids[indices]) for name, indices in splits.items()}
    if group_sets["train"] & group_sets["validation"]:
        raise AssertionError("Package-group leakage between train and validation.")
    if group_sets["train"] & group_sets["test"]:
        raise AssertionError("Package-group leakage between train and test.")
    if group_sets["validation"] & group_sets["test"]:
        raise AssertionError("Package-group leakage between validation and test.")

    audit = {
        "method": "StratifiedGroupKFold; package is group, missing packages are unique row groups",
        "random_states": {"outer": RANDOM_STATE, "inner": INNER_RANDOM_STATE},
        "target_proportions": {"train": 0.60, "validation": 0.20, "test": 0.20},
        "outer_test_fold_selection": outer_details,
        "inner_validation_fold_selection": inner_details,
        "natural_split_counts": {name: class_counts(labels[indices]) for name, indices in splits.items()},
        "natural_split_sizes": {name: int(len(indices)) for name, indices in splits.items()},
        "package_group_overlap": {
            "train_validation": 0,
            "train_test": 0,
            "validation_test": 0,
        },
    }
    return splits, audit


def stable_downsample(
    candidate_positions: np.ndarray,
    source_rows: np.ndarray,
    quota: int,
    salt: str,
) -> np.ndarray:
    if len(candidate_positions) < quota:
        raise ValueError(f"Only {len(candidate_positions)} candidates for quota {quota} ({salt}).")
    ranked = sorted(
        candidate_positions.tolist(),
        key=lambda position: (
            sha256_bytes(f"{RANDOM_STATE}|{salt}|{int(source_rows[position])}".encode("utf-8")),
            int(source_rows[position]),
        ),
    )
    return np.asarray(ranked[:quota], dtype=np.int64)


def stable_group_capped_downsample(
    candidate_positions: np.ndarray,
    source_rows: np.ndarray,
    group_ids: np.ndarray,
    quota: int,
    salt: str,
    max_rows_per_group: int = MAX_ROWS_PER_PACKAGE_GROUP,
) -> np.ndarray:
    """Round-robin across stable package groups, with a strict per-group cap."""

    positions_by_group: dict[str, list[int]] = defaultdict(list)
    for position in candidate_positions.tolist():
        positions_by_group[str(group_ids[position])].append(position)

    ranked_groups = sorted(
        positions_by_group,
        key=lambda group: (
            sha256_bytes(f"{RANDOM_STATE}|{salt}|group|{group}".encode("utf-8")),
            group,
        ),
    )
    for group in ranked_groups:
        positions_by_group[group].sort(
            key=lambda position: (
                sha256_bytes(
                    f"{RANDOM_STATE}|{salt}|row|{int(source_rows[position])}".encode("utf-8")
                ),
                int(source_rows[position]),
            )
        )

    capped_capacity = sum(
        min(len(positions), max_rows_per_group) for positions in positions_by_group.values()
    )
    if capped_capacity < quota:
        raise ValueError(
            f"Only {capped_capacity} group-capped candidates for quota {quota} ({salt})."
        )

    chosen: list[int] = []
    for round_index in range(max_rows_per_group):
        for group in ranked_groups:
            rows = positions_by_group[group]
            if round_index < len(rows):
                chosen.append(rows[round_index])
                if len(chosen) == quota:
                    return np.asarray(chosen, dtype=np.int64)
    raise AssertionError("Group-capped downsampling ended before reaching its validated quota.")


def build_balanced_cohort(
    natural_splits: dict[str, np.ndarray],
    labels: np.ndarray,
    source_rows: np.ndarray,
    group_ids: np.ndarray,
) -> dict[str, np.ndarray]:
    selected: dict[str, np.ndarray] = {}
    for split_name, split_positions in natural_splits.items():
        chosen: list[np.ndarray] = []
        quota = SPLIT_QUOTAS_PER_CLASS[split_name]
        for class_id in range(1, 5):
            candidates = split_positions[labels[split_positions] == class_id]
            chosen.append(
                stable_group_capped_downsample(
                    candidates,
                    source_rows,
                    group_ids,
                    quota,
                    salt=f"{split_name}|class={class_id}",
                )
            )
        selected[split_name] = np.concatenate(chosen)
    return selected


def model_target(dataset_labels: np.ndarray) -> np.ndarray:
    return np.asarray([DATASET_TO_MODEL_CLASS[int(value)] for value in dataset_labels], dtype=np.int8)


def create_models() -> dict[str, Any]:
    return {
        "Logistic Regression": LogisticRegression(
            solver="lbfgs",
            max_iter=3_000,
            random_state=RANDOM_STATE,
            class_weight=None,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            max_features="sqrt",
            random_state=RANDOM_STATE,
            n_jobs=-1,
            class_weight=None,
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.08,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=RANDOM_STATE,
            class_weight=None,
        ),
    }


def slugify_model_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")


def aligned_probabilities(model: Any, features: np.ndarray) -> np.ndarray:
    raw = np.asarray(model.predict_proba(features), dtype=np.float64)
    aligned = np.zeros((len(features), len(MODEL_CLASS_NAMES)), dtype=np.float64)
    for source_column, class_index in enumerate(model.classes_):
        aligned[:, int(class_index)] = raw[:, source_column]
    if not np.allclose(aligned.sum(axis=1), 1.0, atol=1e-7):
        raise AssertionError("Predicted class probabilities do not sum to one.")
    return aligned


def evaluate_model(model: Any, features: np.ndarray, targets: np.ndarray) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    probabilities = aligned_probabilities(model, features)
    predictions = probabilities.argmax(axis=1).astype(np.int8)
    precision, recall, per_class_f1, support = precision_recall_fscore_support(
        targets,
        predictions,
        labels=np.arange(len(MODEL_CLASS_NAMES)),
        zero_division=0,
    )
    matrix = confusion_matrix(targets, predictions, labels=np.arange(len(MODEL_CLASS_NAMES)))
    confidence = probabilities.max(axis=1)
    true_probability = probabilities[np.arange(len(targets)), targets]
    correct = predictions == targets
    incorrect = ~correct

    per_class = {
        MODEL_CLASS_NAMES[index]: {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(per_class_f1[index]),
            "support": int(support[index]),
        }
        for index in range(len(MODEL_CLASS_NAMES))
    }
    confidence_summary = {
        "warning": "Uncalibrated confidence under an artificially balanced four-class prior.",
        "mean_max_probability": float(confidence.mean()),
        "median_max_probability": float(np.median(confidence)),
        "mean_true_class_probability": float(true_probability.mean()),
        "mean_confidence_correct": float(confidence[correct].mean()) if correct.any() else None,
        "mean_confidence_incorrect": float(confidence[incorrect].mean()) if incorrect.any() else None,
        "errors_at_or_above_0_80": int((incorrect & (confidence >= 0.80)).sum()),
        "errors_at_or_above_0_90": int((incorrect & (confidence >= 0.90)).sum()),
    }
    metrics = {
        "accuracy_context_only": float(accuracy_score(targets, predictions)),
        "macro_f1": float(f1_score(targets, predictions, average="macro")),
        "weighted_f1": float(f1_score(targets, predictions, average="weighted")),
        "balanced_accuracy": float(balanced_accuracy_score(targets, predictions)),
        "worst_class_recall": float(min(item["recall"] for item in per_class.values())),
        "per_class": per_class,
        "confusion_matrix": {
            "labels": MODEL_CLASS_NAMES,
            "rows_actual_columns_predicted": matrix.tolist(),
        },
        "confidence": confidence_summary,
    }
    return metrics, predictions, probabilities


def prediction_frame(
    source_rows: np.ndarray,
    packages: np.ndarray,
    targets: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "source_row_index": source_rows.astype(int),
            "package": packages,
            "actual_class": [MODEL_CLASS_NAMES[int(value)] for value in targets],
            "predicted_class": [MODEL_CLASS_NAMES[int(value)] for value in predictions],
            "confidence": probabilities.max(axis=1),
            "correct": predictions == targets,
        }
    )
    for class_index, class_name in enumerate(MODEL_CLASS_NAMES):
        column = "probability_" + re.sub(r"[^a-z0-9]+", "_", class_name.casefold()).strip("_")
        frame[column] = probabilities[:, class_index]
    return frame


def save_confusion_matrix(path: Path, matrix_payload: dict[str, Any]) -> None:
    labels = matrix_payload["labels"]
    matrix = np.asarray(matrix_payload["rows_actual_columns_predicted"], dtype=int)
    frame = pd.DataFrame(matrix, index=[f"actual_{name}" for name in labels], columns=[f"predicted_{name}" for name in labels])
    frame.to_csv(path, encoding="utf-8")


def confusion_pairs(matrix_payload: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = np.asarray(matrix_payload["rows_actual_columns_predicted"], dtype=int)
    pairs: list[dict[str, Any]] = []
    for left in range(len(MODEL_CLASS_NAMES)):
        for right in range(left + 1, len(MODEL_CLASS_NAMES)):
            left_as_right = int(matrix[left, right])
            right_as_left = int(matrix[right, left])
            pairs.append(
                {
                    "pair": f"{MODEL_CLASS_NAMES[left]} ↔ {MODEL_CLASS_NAMES[right]}",
                    "total_bidirectional_errors": left_as_right + right_as_left,
                    f"{MODEL_CLASS_NAMES[left]}_as_{MODEL_CLASS_NAMES[right]}": left_as_right,
                    f"{MODEL_CLASS_NAMES[right]}_as_{MODEL_CLASS_NAMES[left]}": right_as_left,
                }
            )
    return sorted(pairs, key=lambda item: (-item["total_bidirectional_errors"], item["pair"]))


def fmt(value: float) -> str:
    return f"{value:.4f}"


def report_confusion_table(matrix_payload: dict[str, Any]) -> list[str]:
    labels = matrix_payload["labels"]
    matrix = matrix_payload["rows_actual_columns_predicted"]
    lines = [
        "| Actual \\ Predicted | " + " | ".join(labels) + " |",
        "|---|" + "|".join("---:" for _ in labels) + "|",
    ]
    for actual, row in zip(labels, matrix, strict=True):
        lines.append(f"| {actual} | " + " | ".join(str(value) for value in row) + " |")
    return lines


def write_report(
    preprocessing: dict[str, Any],
    split_audit: dict[str, Any],
    results: dict[str, Any],
    best_model: str,
    feature_count: int,
) -> None:
    test_macro_f1_leader = max(
        results, key=lambda name: results[name]["test"]["macro_f1"]
    )
    lines = [
        "# CICMalDroid 2020 Static-Permission Category Classifier — Offline POC",
        "",
        "## Scope",
        "",
        "This is an isolated secondary classifier experiment. It does not replace or modify the existing benign/malware detectors, and it is not connected to FastAPI.",
        "",
        "Only static Android permission features are model inputs. The syscall/Binder files were read only for their `Class` columns to validate positional labels; no dynamic value entered training or prediction.",
        "",
        "## Dataset preparation",
        "",
        f"- Final ordered permission features: **{feature_count}**",
        f"- Static rows: **{preprocessing['static_rows']:,}**",
        f"- Cross-label packages excluded: **{preprocessing['cross_label_package_count']}** ({preprocessing['cross_label_rows_removed_all_classes']} rows across all five classes)",
        "- Benign samples were excluded before modeling because this classifier is gated behind the existing malicious decision.",
        "- Duplicate encoded/plain permission columns were collapsed with logical OR after converting positive numeric/boolean values to presence.",
        "- Package names were used only for conflict detection and split grouping, never as model features.",
        "",
        "### Clean malicious rows available before cohort capping",
        "",
        "| Category | Rows |",
        "|---|---:|",
    ]
    for name, count in preprocessing["clean_malicious_counts"].items():
        lines.append(f"| {name} | {count:,} |")

    lines += [
        "",
        "### Label-alignment assumption",
        "",
        preprocessing["label_alignment_assumption"],
        "",
        "The assertion is strong but positional: the static CSV has no hash or label field, so it is not an independently keyed join.",
        "",
        "## Splits and balancing",
        "",
        f"The full cleaned malicious dataset was group-stratified by package before downsampling. Missing packages were treated as unique row groups. Each already assigned partition was then sampled round-robin across package groups with a maximum of {MAX_ROWS_PER_PACKAGE_GROUP} rows per package, so balancing could not move a package between splits or let one repeated package dominate a category.",
        "",
        "| Split | Adware | Banking Malware | SMS Malware | Riskware | Total |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for split_name in ("train", "validation", "test"):
        counts = split_audit["balanced_cohort_counts"][split_name]
        total = sum(counts.values())
        lines.append(
            f"| {split_name.title()} | {counts['Adware']} | {counts['Banking Malware']} | "
            f"{counts['SMS Malware']} | {counts['Riskware']} | {total:,} |"
        )

    lines += [
        "",
        "No oversampling or SMOTE was used.",
        "",
        "## Model comparison",
        "",
        "The winner was selected on **validation macro-F1**, with balanced accuracy and worst-class recall as tie-breakers. Accuracy was not a selection criterion.",
        "",
        "### Validation",
        "",
        "| Model | Macro F1 | Weighted F1 | Balanced Accuracy | Accuracy (context only) | Worst-class Recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, payload in results.items():
        metrics = payload["validation"]
        lines.append(
            f"| {name} | {fmt(metrics['macro_f1'])} | {fmt(metrics['weighted_f1'])} | "
            f"{fmt(metrics['balanced_accuracy'])} | {fmt(metrics['accuracy_context_only'])} | "
            f"{fmt(metrics['worst_class_recall'])} |"
        )

    lines += [
        "",
        "### Held-out test",
        "",
        "| Model | Macro F1 | Weighted F1 | Balanced Accuracy | Accuracy (context only) | Worst-class Recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, payload in results.items():
        metrics = payload["test"]
        lines.append(
            f"| {name} | {fmt(metrics['macro_f1'])} | {fmt(metrics['weighted_f1'])} | "
            f"{fmt(metrics['balanced_accuracy'])} | {fmt(metrics['accuracy_context_only'])} | "
            f"{fmt(metrics['worst_class_recall'])} |"
        )

    best_validation = results[best_model]["validation"]
    best_test = results[best_model]["test"]
    lines += [
        "",
        "## Selected baseline",
        "",
        f"**{best_model}** was selected because it had the strongest validation macro-F1 ({fmt(best_validation['macro_f1'])}). Its validation balanced accuracy was {fmt(best_validation['balanced_accuracy'])}, and its held-out test macro-F1 was {fmt(best_test['macro_f1'])}.",
    ]
    if test_macro_f1_leader != best_model:
        leader_test = results[test_macro_f1_leader]["test"]
        lines += [
            "",
            f"**Important holdout note:** {test_macro_f1_leader} produced the highest held-out test macro-F1 ({fmt(leader_test['macro_f1'])}), above the formal validation-selected model. The test set was not used to change the winner after observation. This disagreement indicates single-split model-selection uncertainty and is a reason to require repeated package-grouped cross-validation before integration.",
        ]
    lines += [
        "",
        "## Per-class held-out test results — selected model",
        "",
        "| Category | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for class_name in MODEL_CLASS_NAMES:
        item = best_test["per_class"][class_name]
        lines.append(
            f"| {class_name} | {fmt(item['precision'])} | {fmt(item['recall'])} | "
            f"{fmt(item['f1'])} | {item['support']} |"
        )

    lines += [
        "",
        "## Confusion matrix — selected model, held-out test",
        "",
    ]
    lines.extend(report_confusion_table(best_test["confusion_matrix"]))

    pairs = confusion_pairs(best_test["confusion_matrix"])
    lines += [
        "",
        "## Most frequent category confusions",
        "",
    ]
    for item in pairs[:3]:
        lines.append(f"- {item['pair']}: **{item['total_bidirectional_errors']}** total errors")

    lines += [
        "",
        "## Probability/confidence summary — selected model, held-out test",
        "",
        f"- Mean maximum predicted probability: **{fmt(best_test['confidence']['mean_max_probability'])}**",
        f"- Median maximum predicted probability: **{fmt(best_test['confidence']['median_max_probability'])}**",
        f"- Mean probability assigned to the true class: **{fmt(best_test['confidence']['mean_true_class_probability'])}**",
        f"- Errors with confidence ≥ 0.80: **{best_test['confidence']['errors_at_or_above_0_80']}**",
        f"- Errors with confidence ≥ 0.90: **{best_test['confidence']['errors_at_or_above_0_90']}**",
        "",
        "These are uncalibrated model confidence values under a balanced experimental prior; they must not be presented as real-world malware-category prevalence probabilities.",
        "",
        "## Limitations",
        "",
        "1. Static-to-label linkage is positional, not a hash-keyed join.",
        "2. The experiment uses only manifest-reproducible permission features, discarding richer static CICMalDroid signals.",
        "3. Package grouping reduces leakage but cannot prove that different packages are not repackaged copies; hashes are absent from the static CSV.",
        "4. Two known cross-labelled raw-APK hashes cannot be mapped back to static rows and therefore cannot be explicitly removed here.",
        "5. CICMalDroid samples are historical and cover only Adware, Banking Malware, SMS Malware, and Riskware for this secondary task.",
        "6. A balanced cohort changes the class prior, so predicted probabilities are not calibrated for deployment.",
        f"7. This run used scikit-learn {sklearn.__version__}, while the backend currently pins 1.6.1; retraining or compatibility verification under the pinned environment is required before integration.",
        "",
        "## Technical integration assessment",
        "",
        "The feature interface is technically compatible with `ExtractionResult.raw_permissions`: inference can build a binary row by checking each ordered `android.permission.*` feature against the extractor's returned permission set. The saved feature-list hash guards ordering.",
        "",
        "The model is **proof-of-concept suitable at the interface level, but not production-ready** because of the positional-label assumption, historical dataset, uncalibrated balanced probabilities, and scikit-learn patch-version mismatch. No FastAPI integration was performed.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        "python models/category_experimental/train_category_poc.py",
        "```",
        "",
    ]
    (OUTPUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    started = time.perf_counter()
    for required in (STATIC_CSV, SYSCALL_CLASS_CSV, BINDER_CLASS_CSV, CURRENT_APK_MODEL):
        if not required.exists():
            raise FileNotFoundError(required)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions_dir = OUTPUT_DIR / "predictions"
    confusion_dir = OUTPUT_DIR / "confusion_matrices"
    predictions_dir.mkdir(exist_ok=True)
    confusion_dir.mkdir(exist_ok=True)

    log("Inspecting header and deriving the current-pipeline permission overlap...")
    raw_header = load_static_header()
    canonical_features, source_by_bare, mapping_records = build_permission_mapping(
        raw_header, current_pipeline_feature_names()
    )
    package_indices = [index for index, value in enumerate(raw_header) if value == "package"]
    if package_indices != [30_246]:
        raise ValueError(f"Unexpected package columns: {package_indices}")
    package_index = package_indices[0]

    exported_index, packages, permission_matrix, invalid_permission_values = (
        read_static_permission_data(source_by_bare, canonical_features, package_index)
    )
    if len(exported_index) != EXPECTED_STATIC_ROWS:
        raise ValueError(
            f"Static data has {len(exported_index):,} rows; expected {EXPECTED_STATIC_ROWS:,}."
        )
    if not np.array_equal(exported_index, np.arange(EXPECTED_STATIC_ROWS, dtype=np.int64)):
        raise ValueError("Exported static row-index column is not exactly 0..11597.")

    labels, alignment_audit = read_and_verify_labels()
    log("Encoded/plain duplicate permission columns were collapsed with logical OR.")
    if invalid_permission_values:
        raise ValueError(
            "Selected permission columns contain unexpected nonnumeric values: "
            + json.dumps(invalid_permission_values, sort_keys=True)
        )

    conflict_packages, conflict_records = identify_cross_label_packages(packages, labels)
    conflict_mask = np.isin(packages, list(conflict_packages))
    malicious_mask = np.isin(labels, [1, 2, 3, 4])
    keep_mask = malicious_mask & ~conflict_mask
    source_rows = exported_index[keep_mask]
    clean_labels = labels[keep_mask]
    clean_packages = packages[keep_mask]
    clean_matrix = permission_matrix[keep_mask]
    group_ids = make_group_ids(clean_packages, source_rows)

    # After conflict removal, every non-missing package must have a single class.
    group_frame = pd.DataFrame({"group": group_ids, "class_id": clean_labels})
    if int(group_frame.groupby("group")["class_id"].nunique().max()) != 1:
        raise AssertionError("A package group still crosses labels after conflict exclusion.")

    log("Creating package-grouped natural splits before any cohort balancing...")
    natural_splits, split_audit = natural_group_stratified_splits(clean_labels, group_ids)
    balanced_splits = build_balanced_cohort(
        natural_splits, clean_labels, source_rows, group_ids
    )
    split_audit["balancing_method"] = (
        "Deterministic within-split round-robin package-group downsampling after natural "
        f"package-group assignment, capped at {MAX_ROWS_PER_PACKAGE_GROUP} rows per package; "
        "no oversampling and no SMOTE."
    )
    split_audit["maximum_rows_per_package_group"] = MAX_ROWS_PER_PACKAGE_GROUP
    split_audit["balanced_cohort_counts"] = {
        name: class_counts(clean_labels[positions]) for name, positions in balanced_splits.items()
    }
    split_audit["balanced_cohort_sizes"] = {
        name: int(len(positions)) for name, positions in balanced_splits.items()
    }

    # Final leakage and support assertions.
    final_group_sets = {name: set(group_ids[pos]) for name, pos in balanced_splits.items()}
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if final_group_sets[left] & final_group_sets[right]:
            raise AssertionError(f"Final cohort has package overlap: {left}/{right}.")
    for split_name, positions in balanced_splits.items():
        expected = SPLIT_QUOTAS_PER_CLASS[split_name]
        actual = Counter(int(value) for value in clean_labels[positions])
        if any(actual[class_id] != expected for class_id in range(1, 5)):
            raise AssertionError(f"Unexpected balanced support in {split_name}: {actual}")
        for class_id in range(1, 5):
            class_positions = positions[clean_labels[positions] == class_id]
            largest_group = max(Counter(group_ids[class_positions]).values())
            if largest_group > MAX_ROWS_PER_PACKAGE_GROUP:
                raise AssertionError(
                    f"Package cap exceeded in {split_name}/{class_id}: {largest_group}"
                )

    feature_list_bytes = json.dumps(
        canonical_features, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    feature_list_sha256 = sha256_bytes(feature_list_bytes)
    write_json(OUTPUT_DIR / "permission_features.json", canonical_features)
    (OUTPUT_DIR / "permission_features.txt").write_text(
        "\n".join(canonical_features) + "\n", encoding="utf-8"
    )
    write_json(
        OUTPUT_DIR / "permission_source_mapping.json",
        {
            "feature_count": len(canonical_features),
            "ordered_feature_list_sha256": feature_list_sha256,
            "source_permission_columns": sum(len(indices) for indices in source_by_bare.values()),
            "single_source_features": sum(len(indices) == 1 for indices in source_by_bare.values()),
            "multi_source_features": sum(len(indices) > 1 for indices in source_by_bare.values()),
            "features": mapping_records,
        },
    )
    write_json(
        OUTPUT_DIR / "label_mapping.json",
        {
            "dataset_class_id_to_name": {str(key): value for key, value in DATASET_CLASS_NAMES.items()},
            "model_class_index_to_name": {
                str(index): name for index, name in enumerate(MODEL_CLASS_NAMES)
            },
            "benign_dataset_class_excluded": 5,
        },
    )
    alignment_audit["exported_static_index_exact_0_to_11597"] = True
    alignment_audit["raw_apk_hash_conflicts_not_linkable_to_static_rows"] = [
        "00847524ec1e69b2cdd53205cd9725295e87094eeed1567b3efb12191ded24d2",
        "97bfb35785c155686de96095e3c87e243e0fdcd37976e7c7254e48f66c75d1c5",
    ]
    write_json(OUTPUT_DIR / "alignment_audit.json", alignment_audit)
    write_json(
        OUTPUT_DIR / "excluded_cross_label_packages.json",
        {
            "package_count": len(conflict_records),
            "rows_removed_all_classes": int(conflict_mask.sum()),
            "records": conflict_records,
        },
    )

    # Save natural and selected split manifests for auditability.
    natural_assignment = np.full(len(clean_labels), "", dtype=object)
    for split_name, positions in natural_splits.items():
        natural_assignment[positions] = split_name
    natural_manifest = pd.DataFrame(
        {
            "source_row_index": source_rows,
            "package": clean_packages,
            "group_id": group_ids,
            "dataset_class_id": clean_labels,
            "class_name": [DATASET_CLASS_NAMES[int(value)] for value in clean_labels],
            "natural_split": natural_assignment,
        }
    ).sort_values("source_row_index")
    natural_manifest.to_csv(OUTPUT_DIR / "natural_split_manifest.csv", index=False, encoding="utf-8")

    selected_manifest_parts: list[pd.DataFrame] = []
    for split_name, positions in balanced_splits.items():
        selected_manifest_parts.append(
            pd.DataFrame(
                {
                    "source_row_index": source_rows[positions],
                    "package": clean_packages[positions],
                    "group_id": group_ids[positions],
                    "dataset_class_id": clean_labels[positions],
                    "model_class_index": model_target(clean_labels[positions]),
                    "class_name": [DATASET_CLASS_NAMES[int(value)] for value in clean_labels[positions]],
                    "split": split_name,
                }
            )
        )
    split_manifest = pd.concat(selected_manifest_parts, ignore_index=True).sort_values(
        ["split", "dataset_class_id", "source_row_index"]
    )
    split_manifest.to_csv(OUTPUT_DIR / "split_manifest.csv", index=False, encoding="utf-8")

    np.savez_compressed(
        OUTPUT_DIR / "prepared_balanced_subset.npz",
        feature_names=np.asarray(canonical_features, dtype=str),
        X_train=clean_matrix[balanced_splits["train"]],
        y_train=model_target(clean_labels[balanced_splits["train"]]),
        source_rows_train=source_rows[balanced_splits["train"]],
        X_validation=clean_matrix[balanced_splits["validation"]],
        y_validation=model_target(clean_labels[balanced_splits["validation"]]),
        source_rows_validation=source_rows[balanced_splits["validation"]],
        X_test=clean_matrix[balanced_splits["test"]],
        y_test=model_target(clean_labels[balanced_splits["test"]]),
        source_rows_test=source_rows[balanced_splits["test"]],
    )

    preprocessing_summary = {
        "static_rows": EXPECTED_STATIC_ROWS,
        "static_columns": EXPECTED_STATIC_COLUMNS,
        "exported_row_index_removed": True,
        "final_feature_count": len(canonical_features),
        "source_permission_columns_before_or": sum(len(indices) for indices in source_by_bare.values()),
        "single_source_features": sum(len(indices) == 1 for indices in source_by_bare.values()),
        "multi_source_features": sum(len(indices) > 1 for indices in source_by_bare.values()),
        "ordered_feature_list_sha256": feature_list_sha256,
        "cross_label_package_count": len(conflict_records),
        "cross_label_rows_removed_all_classes": int(conflict_mask.sum()),
        "clean_malicious_rows": int(keep_mask.sum()),
        "clean_malicious_counts": class_counts(clean_labels),
        "benign_samples_used": 0,
        "dynamic_input_features_used": False,
        "label_alignment_assumption": alignment_audit["assumption"],
        "package_is_model_feature": False,
    }
    write_json(OUTPUT_DIR / "preprocessing_summary.json", preprocessing_summary)
    write_json(OUTPUT_DIR / "split_audit.json", split_audit)

    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "scikit_learn": sklearn.__version__,
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
        "backend_pinned_scikit_learn": "1.6.1",
        "version_match_with_backend_pin": sklearn.__version__ == "1.6.1",
    }
    write_json(OUTPUT_DIR / "environment.json", environment)

    config = {
        "random_state": RANDOM_STATE,
        "inner_random_state": INNER_RANDOM_STATE,
        "classes": MODEL_CLASS_NAMES,
        "natural_split_target": {"train": 0.60, "validation": 0.20, "test": 0.20},
        "balanced_quota_per_class": SPLIT_QUOTAS_PER_CLASS,
        "maximum_rows_per_package_group": MAX_ROWS_PER_PACKAGE_GROUP,
        "selection_primary": "validation macro_f1",
        "selection_tiebreakers": ["validation balanced_accuracy", "validation worst_class_recall"],
        "accuracy_used_for_selection": False,
        "hist_gradient_boosting_representation": "dense uint8 binary matrix",
        "models": {
            name: model.get_params(deep=False) for name, model in create_models().items()
        },
    }
    write_json(OUTPUT_DIR / "experiment_config.json", config)

    log("Computing source-file fingerprints...")
    source_fingerprints = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in (STATIC_CSV, SYSCALL_CLASS_CSV, BINDER_CLASS_CSV)
    }
    write_json(OUTPUT_DIR / "source_data_fingerprints.json", source_fingerprints)

    split_arrays: dict[str, dict[str, Any]] = {}
    for split_name, positions in balanced_splits.items():
        split_arrays[split_name] = {
            "X": clean_matrix[positions],
            "y": model_target(clean_labels[positions]),
            "source_rows": source_rows[positions],
            "packages": clean_packages[positions],
        }

    log("Training and evaluating multiclass baselines...")
    results: dict[str, Any] = {}
    fitted_models: dict[str, Any] = {}
    for model_name, model in create_models().items():
        slug = slugify_model_name(model_name)
        log(f"  {model_name}")
        train_started = time.perf_counter()
        model.fit(split_arrays["train"]["X"], split_arrays["train"]["y"])
        training_seconds = time.perf_counter() - train_started
        fitted_models[model_name] = model
        results[model_name] = {"training_seconds": float(training_seconds)}

        for split_name in ("validation", "test"):
            data = split_arrays[split_name]
            metrics, predictions, probabilities = evaluate_model(model, data["X"], data["y"])
            results[model_name][split_name] = metrics
            prediction_frame(
                data["source_rows"],
                data["packages"],
                data["y"],
                predictions,
                probabilities,
            ).to_csv(
                predictions_dir / f"{slug}_{split_name}.csv",
                index=False,
                encoding="utf-8",
                float_format="%.8f",
            )
            save_confusion_matrix(
                confusion_dir / f"{slug}_{split_name}.csv", metrics["confusion_matrix"]
            )

        model_bundle = {
            "experimental": True,
            "integrated_with_fastapi": False,
            "model": model,
            "model_name": model_name,
            "class_names_in_probability_order": MODEL_CLASS_NAMES,
            "feature_names": canonical_features,
            "feature_list_sha256": feature_list_sha256,
            "input_contract": {
                "source": "ExtractionResult.raw_permissions",
                "representation": "binary presence in saved feature order",
                "normalization": "exact canonical android.permission.* string after strip",
            },
            "training_split_rows": int(len(split_arrays["train"]["y"])),
            "random_state": RANDOM_STATE,
            "scikit_learn_version": sklearn.__version__,
        }
        joblib.dump(model_bundle, OUTPUT_DIR / f"{slug}.joblib")

    ranked = sorted(
        results,
        key=lambda name: (
            -results[name]["validation"]["macro_f1"],
            -results[name]["validation"]["balanced_accuracy"],
            -results[name]["validation"]["worst_class_recall"],
            name,
        ),
    )
    best_model_name = ranked[0]
    best_slug = slugify_model_name(best_model_name)
    best_bundle = joblib.load(OUTPUT_DIR / f"{best_slug}.joblib")
    best_bundle["selection"] = {
        "selected_on": "validation only",
        "primary": "macro_f1",
        "tiebreakers": ["balanced_accuracy", "worst_class_recall"],
        "ranking": ranked,
    }
    joblib.dump(best_bundle, OUTPUT_DIR / "best_category_model.joblib")

    comparison_rows: list[dict[str, Any]] = []
    for model_name, payload in results.items():
        for split_name in ("validation", "test"):
            metrics = payload[split_name]
            comparison_rows.append(
                {
                    "model": model_name,
                    "split": split_name,
                    "macro_f1": metrics["macro_f1"],
                    "weighted_f1": metrics["weighted_f1"],
                    "balanced_accuracy": metrics["balanced_accuracy"],
                    "accuracy_context_only": metrics["accuracy_context_only"],
                    "worst_class_recall": metrics["worst_class_recall"],
                    "training_seconds": payload["training_seconds"],
                }
            )
    pd.DataFrame(comparison_rows).to_csv(
        OUTPUT_DIR / "model_comparison.csv", index=False, encoding="utf-8", float_format="%.8f"
    )

    metrics_payload = {
        "experimental": True,
        "integrated_with_fastapi": False,
        "selection": {
            "best_model": best_model_name,
            "selected_on": "validation only",
            "primary_metric": "macro_f1",
            "tiebreakers": ["balanced_accuracy", "worst_class_recall"],
            "accuracy_used_for_selection": False,
            "ranking": ranked,
            "held_out_test_macro_f1_leader_for_reporting_only": max(
                results, key=lambda name: results[name]["test"]["macro_f1"]
            ),
            "held_out_test_used_to_change_selection": False,
        },
        "dataset": preprocessing_summary,
        "splits": split_audit,
        "models": results,
        "best_model_test_confusion_pairs": confusion_pairs(
            results[best_model_name]["test"]["confusion_matrix"]
        ),
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    write_json(OUTPUT_DIR / "metrics.json", metrics_payload)
    write_report(
        preprocessing_summary,
        split_audit,
        results,
        best_model_name,
        len(canonical_features),
    )

    log(
        f"Done in {time.perf_counter() - started:.1f}s. "
        f"Selected baseline: {best_model_name}. Outputs: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()

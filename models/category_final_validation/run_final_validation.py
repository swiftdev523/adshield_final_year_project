"""Final offline model-family selection for the CICMalDroid category POC.

This script deliberately does not import or modify FastAPI and does not touch the
existing binary malware detectors.  It treats ``models/category_experimental``
as immutable historical evidence, quarantines every package used by the old test
split, and writes only under ``models/category_final_validation/artifacts``.

The current corpus cannot supply a fresh four-class package-unseen holdout:
Banking Malware and SMS Malware have no package groups that were absent from the
historical POC.  The script therefore completes grouped model selection and a
separate nested grouped calibration study, exports a clearly provisional model
candidate, and records the final-holdout evaluation as unavailable rather than
substituting repeated packages.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedGroupKFold


SCRIPT_PATH = Path(__file__).resolve()
OUTPUT_ROOT = SCRIPT_PATH.parent
ARTIFACTS_DIR = OUTPUT_ROOT / "artifacts"
PROJECT_ROOT = SCRIPT_PATH.parents[2]
HISTORICAL_DIR = PROJECT_ROOT / "models" / "category_experimental"

# Import only the already-audited data-decoding helpers.  Its main() is guarded
# and is never invoked, so the historical output directory is not written.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from models.category_experimental import train_category_poc as poc  # noqa: E402


EXPECTED_SKLEARN_VERSION = "1.6.1"
EXPECTED_FEATURE_COUNT = 153
EXPECTED_FEATURE_SHA256 = (
    "7aecf3b202c88d707e458a3705b4e3a326a9ee062c9b1e0f209a6b9a5c087c34"
)
MODEL_CLASS_NAMES = ["Adware", "Banking Malware", "SMS Malware", "Riskware"]
CLASS_IDS = [1, 2, 3, 4]
CLASS_TO_MODEL_INDEX = {class_id: class_id - 1 for class_id in CLASS_IDS}

HISTORICAL_ARTIFACT_HASHES = {
    "metrics.json": "cb5e1334ff22f2c8d1736b125ee5286dc8a4880b7cb6a373166649e49e86e4fa",
    "model_comparison.csv": "b00b2af2a484832f3eff252e17a48ea83ac7e8510680b175160951a71c6b9d2e",
    "split_manifest.csv": "d14dd5eaece6b4772981aab800f17d919ee3dfb45abe00adb440b062ffa4cced",
    "natural_split_manifest.csv": "f884942ddd45909697b4fc749dcba68b5293945652c3b524d342c87595f1c5b2",
    "permission_features.json": "9bbbdbf826db7957a0335baefa93eb8bc3440c4edcf7f5825cccf949a105a4fd",
    "experiment_config.json": "d977bd896a2dc99fad576f48c9c424db41b1a07cfe04ec789d42aae8978d5b3c",
    "permission_source_mapping.json": "59cfec267197b4c7efc075b47999401a9d702d245ac1a44fe0de4f7532340811",
    "source_data_fingerprints.json": "71ff81753e0758185f515f821e482fa9c2cbe484121a9d1021900cde726c28bc",
    "train_category_poc.py": "8736de3f5241193f451538de5488edbec385a3424ad019f62e83e10e4107fd3f",
}

CV_REPEATS = 5
CV_FOLDS = 5
CV_SEEDS = [6201, 6202, 6203, 6204, 6205]
CALIBRATION_OUTER_SEED = 6201
CALIBRATION_INNER_SEED_BASE = 7300
MAX_ROWS_PER_PACKAGE = 8
DEVELOPMENT_ROWS_PER_CLASS = 879
EXPECTED_HISTORICAL_NAMED_ROWS = {
    "Adware": 797,
    "Banking Malware": 631,
    "SMS Malware": 800,
    "Riskware": 780,
}
MODEL_RANDOM_STATE = 42
ECE_BINS = 10


def log(message: str) -> None:
    print(message, flush=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def normalized_group_id(package: str, source_row: int) -> str:
    """Conservatively co-group case variants; missing packages stay row-unique."""

    normalized = str(package).strip().casefold()
    return normalized if normalized else f"__missing_package_row_{int(source_row)}"


def create_models() -> dict[str, Any]:
    """The fixed POC family configurations; no test-driven tuning is performed."""

    return {
        "Logistic Regression": LogisticRegression(
            solver="lbfgs",
            max_iter=3_000,
            random_state=MODEL_RANDOM_STATE,
            class_weight=None,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=400,
            max_features="sqrt",
            random_state=MODEL_RANDOM_STATE,
            n_jobs=-1,
            class_weight=None,
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.08,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=MODEL_RANDOM_STATE,
            class_weight=None,
        ),
    }


def class_counts(values: np.ndarray) -> dict[str, int]:
    counts = Counter(int(value) for value in values)
    return {
        MODEL_CLASS_NAMES[index]: int(counts.get(index, 0))
        for index in range(len(MODEL_CLASS_NAMES))
    }


def aligned_probabilities(model: Any, features: np.ndarray) -> np.ndarray:
    raw = np.asarray(model.predict_proba(features), dtype=np.float64)
    aligned = np.zeros((len(features), len(MODEL_CLASS_NAMES)), dtype=np.float64)
    for source_column, class_index in enumerate(model.classes_):
        aligned[:, int(class_index)] = raw[:, source_column]
    if not np.allclose(aligned.sum(axis=1), 1.0, atol=1e-7):
        raise AssertionError("Predicted class probabilities do not sum to one.")
    return aligned


def classification_metrics(
    targets: np.ndarray, predictions: np.ndarray
) -> dict[str, Any]:
    precision, recall, per_class_f1, support = precision_recall_fscore_support(
        targets,
        predictions,
        labels=np.arange(len(MODEL_CLASS_NAMES)),
        zero_division=0,
    )
    matrix = confusion_matrix(
        targets, predictions, labels=np.arange(len(MODEL_CLASS_NAMES))
    )
    per_class = {
        MODEL_CLASS_NAMES[index]: {
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(per_class_f1[index]),
            "support": int(support[index]),
        }
        for index in range(len(MODEL_CLASS_NAMES))
    }
    return {
        "macro_f1": float(f1_score(targets, predictions, average="macro")),
        "balanced_accuracy": float(balanced_accuracy_score(targets, predictions)),
        "worst_class_recall": float(min(item["recall"] for item in per_class.values())),
        "per_class": per_class,
        "confusion_matrix": {
            "labels": MODEL_CLASS_NAMES,
            "rows_actual_columns_predicted": matrix.tolist(),
        },
    }


def ece_binary(targets: np.ndarray, probabilities: np.ndarray) -> tuple[float, list[dict[str, Any]]]:
    edges = np.linspace(0.0, 1.0, ECE_BINS + 1)
    total = len(targets)
    ece = 0.0
    records: list[dict[str, Any]] = []
    for index in range(ECE_BINS):
        lower = float(edges[index])
        upper = float(edges[index + 1])
        if index == ECE_BINS - 1:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        support = int(mask.sum())
        if support:
            mean_probability = float(probabilities[mask].mean())
            observed_rate = float(targets[mask].mean())
            absolute_gap = abs(mean_probability - observed_rate)
            ece += support / total * absolute_gap
        else:
            mean_probability = None
            observed_rate = None
            absolute_gap = None
        records.append(
            {
                "bin": index + 1,
                "lower_inclusive": lower,
                "upper_inclusive_only_for_last_bin": upper,
                "support": support,
                "mean_probability": mean_probability,
                "observed_rate": observed_rate,
                "absolute_gap": absolute_gap,
            }
        )
    return float(ece), records


def probability_metrics(
    targets: np.ndarray, probabilities: np.ndarray
) -> dict[str, Any]:
    predictions = probabilities.argmax(axis=1).astype(np.int8)
    one_hot = np.eye(len(MODEL_CLASS_NAMES), dtype=np.float64)[targets]
    top_probability = probabilities.max(axis=1)
    top_correct = (predictions == targets).astype(np.int8)
    top_ece, top_reliability = ece_binary(top_correct, top_probability)
    per_class: dict[str, Any] = {}
    for index, name in enumerate(MODEL_CLASS_NAMES):
        binary_target = (targets == index).astype(np.int8)
        class_probability = probabilities[:, index]
        class_ece, reliability = ece_binary(binary_target, class_probability)
        per_class[name] = {
            "one_vs_rest_brier": float(np.mean((class_probability - binary_target) ** 2)),
            "ece_10_equal_width_bins": class_ece,
            "reliability_bins": reliability,
        }
    return {
        **classification_metrics(targets, predictions),
        "multiclass_log_loss": float(
            log_loss(targets, probabilities, labels=np.arange(len(MODEL_CLASS_NAMES)))
        ),
        "multiclass_brier_mean_sum_squared_error": float(
            np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))
        ),
        "top_label_ece_10_equal_width_bins": top_ece,
        "top_label_reliability_bins": top_reliability,
        "per_class_probability_metrics": per_class,
    }


def verify_historical_artifacts() -> dict[str, Any]:
    observed: dict[str, Any] = {}
    for name, expected in HISTORICAL_ARTIFACT_HASHES.items():
        path = HISTORICAL_DIR / name
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"Historical artifact changed: {path}; expected {expected}, got {actual}."
            )
        observed[name] = {"sha256": actual, "bytes": path.stat().st_size}
    return observed


def historical_snapshot(hashes: dict[str, Any]) -> dict[str, Any]:
    comparison_path = HISTORICAL_DIR / "model_comparison.csv"
    frame = pd.read_csv(comparison_path)
    historical_rows = frame.to_dict(orient="records")
    return {
        "status": "immutable_historical_poc_evidence",
        "source_directory": str(HISTORICAL_DIR),
        "artifacts": hashes,
        "verbatim_model_comparison_csv": comparison_path.read_text(encoding="utf-8"),
        "results": historical_rows,
        "historical_test_used_for_current_selection": False,
        "historical_selection_remains": {
            "selected_model": "HistGradientBoosting",
            "basis": "historical validation Macro F1 only",
            "not_retroactively_changed_to_test_leader": True,
        },
    }


def verify_source_data_fingerprints() -> dict[str, Any]:
    expected = json.loads(
        (HISTORICAL_DIR / "source_data_fingerprints.json").read_text(encoding="utf-8")
    )
    paths = {
        poc.STATIC_CSV.name: poc.STATIC_CSV,
        poc.SYSCALL_CLASS_CSV.name: poc.SYSCALL_CLASS_CSV,
        poc.BINDER_CLASS_CSV.name: poc.BINDER_CLASS_CSV,
    }
    observed: dict[str, Any] = {}
    for name, path in paths.items():
        actual = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        if actual != expected[name]:
            raise ValueError(
                f"Source data fingerprint changed for {path}: "
                f"expected {expected[name]}, got {actual}."
            )
        observed[name] = actual
    return observed


def load_full_clean_permission_data() -> dict[str, Any]:
    feature_names = json.loads(
        (HISTORICAL_DIR / "permission_features.json").read_text(encoding="utf-8")
    )
    if len(feature_names) != EXPECTED_FEATURE_COUNT:
        raise ValueError("Historical feature count changed.")
    feature_sha = sha256_bytes(
        json.dumps(feature_names, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    if feature_sha != EXPECTED_FEATURE_SHA256:
        raise ValueError("Historical feature ordering/hash changed.")

    mapping_payload = json.loads(
        (HISTORICAL_DIR / "permission_source_mapping.json").read_text(encoding="utf-8")
    )
    source_by_bare = {
        record["bare_name"]: [
            int(item["zero_based_index"]) for item in record["source_columns"]
        ]
        for record in mapping_payload["features"]
    }
    raw_header = poc.load_static_header()
    package_indices = [index for index, value in enumerate(raw_header) if value == "package"]
    if package_indices != [30_246]:
        raise ValueError(f"Unexpected package column indices: {package_indices}")

    exported_index, packages, permission_matrix, invalid = poc.read_static_permission_data(
        source_by_bare,
        feature_names,
        package_indices[0],
    )
    if len(exported_index) != poc.EXPECTED_STATIC_ROWS:
        raise ValueError(
            f"Static row count changed: {len(exported_index)}; "
            f"expected {poc.EXPECTED_STATIC_ROWS}."
        )
    if not np.array_equal(
        exported_index, np.arange(poc.EXPECTED_STATIC_ROWS, dtype=np.int64)
    ):
        raise ValueError("Exported static row index is not exactly 0..11597.")
    if invalid:
        raise ValueError(f"Invalid selected permission values: {invalid}")
    labels, alignment_audit = poc.read_and_verify_labels()
    conflict_packages, conflict_records = poc.identify_cross_label_packages(packages, labels)
    keep = np.isin(labels, CLASS_IDS) & ~np.isin(packages, list(conflict_packages))

    source_rows = exported_index[keep]
    clean_packages = packages[keep]
    dataset_labels = labels[keep]
    model_targets = np.asarray(
        [CLASS_TO_MODEL_INDEX[int(value)] for value in dataset_labels], dtype=np.int8
    )
    groups = np.asarray(
        [
            normalized_group_id(package, row)
            for package, row in zip(clean_packages, source_rows, strict=True)
        ],
        dtype=object,
    )
    clean_matrix = permission_matrix[keep]

    group_label_counts = pd.DataFrame(
        {"group": groups, "target": model_targets}
    ).groupby("group")["target"].nunique()
    if int(group_label_counts.max()) != 1:
        raise AssertionError("A normalized package group crosses category labels.")

    return {
        "X": clean_matrix,
        "y": model_targets,
        "dataset_labels": dataset_labels,
        "source_rows": source_rows,
        "packages": clean_packages,
        "groups": groups,
        "feature_names": feature_names,
        "feature_sha256": feature_sha,
        "alignment_audit": alignment_audit,
        "cross_label_conflicts": conflict_records,
    }


def manifest_group_ids(frame: pd.DataFrame) -> np.ndarray:
    return np.asarray(
        [
            normalized_group_id(package, row)
            for package, row in zip(
                frame["package"].fillna(""), frame["source_row_index"], strict=True
            )
        ],
        dtype=object,
    )


def build_partition_inventory(data: dict[str, Any]) -> dict[str, Any]:
    historical = pd.read_csv(
        HISTORICAL_DIR / "split_manifest.csv", keep_default_na=False
    )
    historical["normalized_group_id"] = manifest_group_ids(historical)
    split_group_sets = {
        split: set(historical.loc[historical["split"] == split, "normalized_group_id"])
        for split in ("train", "validation", "test")
    }
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if split_group_sets[left] & split_group_sets[right]:
            raise AssertionError(f"Historical normalized package overlap: {left}/{right}")

    development_groups = split_group_sets["train"] | split_group_sets["validation"]
    quarantined_test_groups = split_group_sets["test"]
    if development_groups & quarantined_test_groups:
        raise AssertionError("Historical test groups leaked into development groups.")

    groups = data["groups"]
    y = data["y"]
    packages = np.asarray(data["packages"], dtype=object)
    named_package_mask = np.asarray(
        [bool(str(package).strip()) for package in packages], dtype=bool
    )
    all_development_positions = np.flatnonzero(
        np.isin(groups, list(development_groups))
    )
    development_positions = all_development_positions[
        named_package_mask[all_development_positions]
    ]
    excluded_missing_package_positions = all_development_positions[
        ~named_package_mask[all_development_positions]
    ]
    quarantined_positions = np.flatnonzero(np.isin(groups, list(quarantined_test_groups)))
    if set(groups[development_positions]) & set(groups[quarantined_positions]):
        raise AssertionError("Full-row package quarantine failed.")

    expected_development = {
        "Adware": {"rows": 885, "groups": 800},
        "Banking Malware": {"rows": 1_629, "groups": 763},
        "SMS Malware": {"rows": 2_995, "groups": 241},
        "Riskware": {"rows": 1_015, "groups": 800},
    }
    observed_development: dict[str, Any] = {}
    observed_named_development: dict[str, Any] = {}
    excluded_missing_package_rows: dict[str, int] = {}
    for class_index, name in enumerate(MODEL_CLASS_NAMES):
        positions = all_development_positions[
            y[all_development_positions] == class_index
        ]
        observed_development[name] = {
            "rows": int(len(positions)),
            "groups": int(len(set(groups[positions]))),
        }
        named_positions = development_positions[
            y[development_positions] == class_index
        ]
        observed_named_development[name] = {
            "rows": int(len(named_positions)),
            "groups": int(len(set(groups[named_positions]))),
        }
        excluded_missing_package_rows[name] = int(
            (y[excluded_missing_package_positions] == class_index).sum()
        )
    if observed_development != expected_development:
        raise AssertionError(
            f"Development inventory changed: {observed_development}"
        )
    expected_named_development = {
        "Adware": {"rows": 882, "groups": 797},
        "Banking Malware": {"rows": 1_460, "groups": 594},
        "SMS Malware": {"rows": 2_995, "groups": 241},
        "Riskware": {"rows": 995, "groups": 780},
    }
    if observed_named_development != expected_named_development:
        raise AssertionError(
            f"Named development inventory changed: {observed_named_development}"
        )

    all_historical_groups = set().union(*split_group_sets.values())
    never_seen_positions = np.flatnonzero(~np.isin(groups, list(all_historical_groups)))
    never_seen_inventory: dict[str, Any] = {}
    for class_index, name in enumerate(MODEL_CLASS_NAMES):
        positions = never_seen_positions[y[never_seen_positions] == class_index]
        named_mask = np.asarray(
            [bool(str(data["packages"][position]).strip()) for position in positions],
            dtype=bool,
        )
        named_positions = positions[named_mask]
        never_seen_inventory[name] = {
            "rows": int(len(positions)),
            "normalized_groups": int(len(set(groups[positions]))),
            "verifiably_named_rows": int(len(named_positions)),
            "verifiably_named_groups": int(len(set(groups[named_positions]))),
        }

    holdout_possible = all(
        never_seen_inventory[name]["verifiably_named_groups"] > 0
        for name in MODEL_CLASS_NAMES
    )
    if holdout_possible:
        raise AssertionError(
            "Corpus inventory changed: a strict four-class holdout may now be possible; "
            "freeze it under a newly reviewed protocol before evaluating it."
        )

    return {
        "historical_manifest": historical,
        "historical_split_group_sets": split_group_sets,
        "development_groups": development_groups,
        "quarantined_test_groups": quarantined_test_groups,
        "development_positions": development_positions,
        "excluded_missing_package_positions": excluded_missing_package_positions,
        "quarantined_positions": quarantined_positions,
        "observed_development": observed_development,
        "observed_named_development": observed_named_development,
        "excluded_missing_package_rows": excluded_missing_package_rows,
        "never_seen_inventory": never_seen_inventory,
        "holdout_possible": holdout_possible,
    }


def choose_additional_rows(
    candidate_positions: np.ndarray,
    existing_positions: np.ndarray,
    groups: np.ndarray,
    source_rows: np.ndarray,
    quota: int,
    class_name: str,
) -> np.ndarray:
    counts = Counter(str(group) for group in groups[existing_positions])
    candidates_by_group: dict[str, list[int]] = defaultdict(list)
    for position in candidate_positions.tolist():
        group = str(groups[position])
        if counts[group] < MAX_ROWS_PER_PACKAGE:
            candidates_by_group[group].append(position)

    ranked_groups = sorted(
        candidates_by_group,
        key=lambda group: (stable_hash(f"extra|{class_name}|group|{group}"), group),
    )
    for group in ranked_groups:
        candidates_by_group[group].sort(
            key=lambda position: (
                stable_hash(
                    f"extra|{class_name}|row|{int(source_rows[position])}"
                ),
                int(source_rows[position]),
            )
        )

    chosen: list[int] = []
    while len(chosen) < quota:
        progressed = False
        for group in ranked_groups:
            if counts[group] >= MAX_ROWS_PER_PACKAGE or not candidates_by_group[group]:
                continue
            chosen.append(candidates_by_group[group].pop(0))
            counts[group] += 1
            progressed = True
            if len(chosen) == quota:
                break
        if not progressed:
            raise ValueError(
                f"Insufficient group-capped unused rows for {class_name}: "
                f"needed {quota}, selected {len(chosen)}."
            )
    return np.asarray(chosen, dtype=np.int64)


def build_balanced_development_cohort(
    data: dict[str, Any], inventory: dict[str, Any]
) -> tuple[np.ndarray, pd.DataFrame, dict[str, Any]]:
    historical = inventory["historical_manifest"]
    historical_development_rows = set(
        int(value)
        for value in historical.loc[
            historical["split"].isin(["train", "validation"])
            & historical["package"].astype(str).str.strip().ne(""),
            "source_row_index",
        ]
    )
    source_rows = data["source_rows"]
    y = data["y"]
    groups = data["groups"]
    development_positions = inventory["development_positions"]
    source_to_position = {
        int(source_row): position for position, source_row in enumerate(source_rows)
    }
    historical_positions = np.asarray(
        [source_to_position[row] for row in sorted(historical_development_rows)],
        dtype=np.int64,
    )

    chosen_by_class: list[np.ndarray] = []
    origin_by_position: dict[int, str] = {
        int(position): "historical_train_or_validation_row"
        for position in historical_positions
    }
    for class_index, name in enumerate(MODEL_CLASS_NAMES):
        existing = historical_positions[y[historical_positions] == class_index]
        expected_existing = EXPECTED_HISTORICAL_NAMED_ROWS[name]
        if len(existing) != expected_existing:
            raise AssertionError(f"Historical development support changed for {name}.")
        existing_set = set(existing.tolist())
        unused = np.asarray(
            [
                position
                for position in development_positions[y[development_positions] == class_index]
                if int(position) not in existing_set
            ],
            dtype=np.int64,
        )
        additional = choose_additional_rows(
            unused,
            existing,
            groups,
            source_rows,
            DEVELOPMENT_ROWS_PER_CLASS - expected_existing,
            name,
        )
        for position in additional:
            origin_by_position[int(position)] = "additional_unused_row_from_development_group"
        chosen = np.concatenate([existing, additional])
        if len(chosen) != DEVELOPMENT_ROWS_PER_CLASS:
            raise AssertionError(f"Unexpected cohort support for {name}.")
        largest_group = max(Counter(groups[chosen]).values())
        if largest_group > MAX_ROWS_PER_PACKAGE:
            raise AssertionError(f"Package row cap exceeded for {name}: {largest_group}")
        chosen_by_class.append(chosen)

    positions = np.concatenate(chosen_by_class)
    positions = np.asarray(
        sorted(
            positions.tolist(),
            key=lambda position: (int(y[position]), int(source_rows[position])),
        ),
        dtype=np.int64,
    )
    if len(set(source_rows[positions].tolist())) != len(positions):
        raise AssertionError("A source row was selected more than once.")
    if any(not str(package).strip() for package in data["packages"][positions]):
        raise AssertionError("A blank-package row entered the development cohort.")
    if set(groups[positions]) & inventory["quarantined_test_groups"]:
        raise AssertionError("Historical test package entered the development cohort.")

    frame = pd.DataFrame(
        {
            "source_row_index": source_rows[positions].astype(int),
            "package": data["packages"][positions],
            "normalized_group_id": groups[positions],
            "model_class_index": y[positions].astype(int),
            "class_name": [MODEL_CLASS_NAMES[int(value)] for value in y[positions]],
            "origin": [origin_by_position[int(position)] for position in positions],
        }
    )
    summary = {
        "rows": int(len(frame)),
        "rows_per_class": DEVELOPMENT_ROWS_PER_CLASS,
        "class_counts": frame["class_name"].value_counts().sort_index().to_dict(),
        "groups_per_class": frame.groupby("class_name")["normalized_group_id"].nunique().to_dict(),
        "origin_counts_per_class": (
            frame.groupby(["class_name", "origin"]).size().unstack(fill_value=0).to_dict(orient="index")
        ),
        "maximum_rows_per_package": MAX_ROWS_PER_PACKAGE,
        "blank_package_rows_excluded": int(
            len(inventory["excluded_missing_package_positions"])
        ),
        "blank_package_rows_excluded_per_class": inventory[
            "excluded_missing_package_rows"
        ],
        "historical_test_packages_quarantined": True,
        "casefolded_package_grouping": True,
        "balancing_timing": "fixed development cohort before CV; no fold-specific oversampling or SMOTE",
    }
    return positions, frame, summary


def build_repeated_group_splits(
    y: np.ndarray, groups: np.ndarray
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    splits: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    for repeat_index, seed in enumerate(CV_SEEDS, start=1):
        splitter = StratifiedGroupKFold(
            n_splits=CV_FOLDS, shuffle=True, random_state=seed
        )
        validation_seen = np.zeros(len(y), dtype=np.int8)
        for fold_index, (train, validation) in enumerate(
            splitter.split(np.zeros(len(y), dtype=np.uint8), y, groups), start=1
        ):
            if set(groups[train]) & set(groups[validation]):
                raise AssertionError("Package group crosses a CV fold.")
            if set(np.unique(y[train])) != set(range(len(MODEL_CLASS_NAMES))):
                raise AssertionError("A CV training fold is missing a class.")
            if set(np.unique(y[validation])) != set(range(len(MODEL_CLASS_NAMES))):
                raise AssertionError("A CV validation fold is missing a class.")
            validation_seen[validation] += 1
            splits.append(
                {
                    "repeat": repeat_index,
                    "fold": fold_index,
                    "seed": seed,
                    "train": train,
                    "validation": validation,
                }
            )
            for position in validation:
                assignment_rows.append(
                    {
                        "cohort_position": int(position),
                        "repeat": repeat_index,
                        "validation_fold": fold_index,
                        "seed": seed,
                        "normalized_group_id": str(groups[position]),
                        "model_class_index": int(y[position]),
                        "class_name": MODEL_CLASS_NAMES[int(y[position])],
                    }
                )
        if not np.array_equal(validation_seen, np.ones(len(y), dtype=np.int8)):
            raise AssertionError(f"Repeat {repeat_index} is not complete OOF coverage.")
    return splits, pd.DataFrame(assignment_rows)


def metric_row(
    model_name: str,
    repeat: int,
    fold: int | None,
    metrics: dict[str, Any],
    training_seconds: float | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "model": model_name,
        "repeat": repeat,
        "fold": fold,
        "macro_f1": metrics["macro_f1"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "worst_class_recall": metrics["worst_class_recall"],
    }
    if training_seconds is not None:
        row["training_seconds"] = training_seconds
    for name in MODEL_CLASS_NAMES:
        slug = name.casefold().replace(" ", "_")
        row[f"recall_{slug}"] = metrics["per_class"][name]["recall"]
        row[f"precision_{slug}"] = metrics["per_class"][name]["precision"]
        row[f"support_{slug}"] = metrics["per_class"][name]["support"]
    return row


def summarize_repeated_cv(repeat_frame: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for model_name, group in repeat_frame.groupby("model", sort=False):
        per_class_recall: dict[str, Any] = {}
        per_class_precision: dict[str, Any] = {}
        for name in MODEL_CLASS_NAMES:
            slug = name.casefold().replace(" ", "_")
            column = f"recall_{slug}"
            per_class_recall[name] = {
                "mean": float(group[column].mean()),
                "sample_standard_deviation": float(group[column].std(ddof=1)),
            }
            precision_column = f"precision_{slug}"
            per_class_precision[name] = {
                "mean": float(group[precision_column].mean()),
                "sample_standard_deviation": float(
                    group[precision_column].std(ddof=1)
                ),
            }
        summary[model_name] = {
            "repeat_count": int(len(group)),
            "mean_macro_f1": float(group["macro_f1"].mean()),
            "macro_f1_sample_standard_deviation": float(group["macro_f1"].std(ddof=1)),
            "macro_f1_standard_error_for_one_se_rule": float(
                group["macro_f1"].std(ddof=1) / math.sqrt(len(group))
            ),
            "mean_balanced_accuracy": float(group["balanced_accuracy"].mean()),
            "balanced_accuracy_sample_standard_deviation": float(
                group["balanced_accuracy"].std(ddof=1)
            ),
            "mean_worst_class_recall": float(group["worst_class_recall"].mean()),
            "per_class_precision": per_class_precision,
            "per_class_recall": per_class_recall,
        }
    return summary


def select_model_family(
    summary: dict[str, Any], repeat_frame: pd.DataFrame
) -> dict[str, Any]:
    leader = max(summary, key=lambda name: summary[name]["mean_macro_f1"])
    leader_mean = summary[leader]["mean_macro_f1"]
    leader_se = summary[leader]["macro_f1_standard_error_for_one_se_rule"]
    threshold = leader_mean - leader_se
    eligible = [
        name for name in summary if summary[name]["mean_macro_f1"] >= threshold
    ]
    simplicity = {
        "Logistic Regression": 0,
        "Random Forest": 1,
        "HistGradientBoosting": 2,
    }
    selected = min(
        eligible,
        key=lambda name: (
            summary[name]["macro_f1_sample_standard_deviation"],
            -summary[name]["mean_balanced_accuracy"],
            -summary[name]["mean_worst_class_recall"],
            simplicity[name],
        ),
    )

    pivot = repeat_frame.pivot(index="repeat", columns="model", values="macro_f1")
    pairwise: list[dict[str, Any]] = []
    names = list(summary)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            differences = pivot[left] - pivot[right]
            pairwise.append(
                {
                    "left_model": left,
                    "right_model": right,
                    "mean_paired_repeat_macro_f1_difference_left_minus_right": float(
                        differences.mean()
                    ),
                    "sample_standard_deviation_of_difference": float(
                        differences.std(ddof=1)
                    ),
                    "left_repeat_wins": int((differences > 0).sum()),
                    "ties": int((differences == 0).sum()),
                    "right_repeat_wins": int((differences < 0).sum()),
                    "note": "Descriptive only; repeated CV folds are dependent, so no p-value is claimed.",
                }
            )

    return {
        "selected_model": selected,
        "raw_mean_macro_f1_leader": leader,
        "rule": (
            "Highest mean repeat-level OOF Macro F1 defines the leader. Models within one "
            "leader standard error are eligible; among them choose the lowest repeat-level "
            "Macro-F1 standard deviation, then higher mean balanced accuracy, higher mean "
            "worst-class recall, then the simpler family."
        ),
        "statistical_caveat": (
            "This is a precommitted stability heuristic, not a formal confidence interval: "
            "repeat OOF scores are dependent and five repeats provide a noisy SD estimate."
        ),
        "leader_mean_macro_f1": leader_mean,
        "leader_standard_error": leader_se,
        "one_standard_error_threshold": threshold,
        "eligible_models": eligible,
        "historical_test_metrics_consulted_by_rule": False,
        "pairwise_repeat_differences": pairwise,
    }


def run_model_comparison(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    source_rows: np.ndarray,
    packages: np.ndarray,
    splits: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    fold_rows: list[dict[str, Any]] = []
    repeat_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    repeated_confusions: dict[str, Any] = {}

    for model_name in create_models():
        log(f"Cross-validating {model_name}...")
        all_repeat_targets: list[np.ndarray] = []
        all_repeat_predictions: list[np.ndarray] = []
        for repeat in range(1, CV_REPEATS + 1):
            oof_predictions = np.full(len(y), -1, dtype=np.int8)
            oof_probabilities = np.full(
                (len(y), len(MODEL_CLASS_NAMES)), np.nan, dtype=np.float64
            )
            repeat_splits = [item for item in splits if item["repeat"] == repeat]
            for split in repeat_splits:
                model = create_models()[model_name]
                started = time.perf_counter()
                model.fit(X[split["train"]], y[split["train"]])
                training_seconds = time.perf_counter() - started
                probabilities = aligned_probabilities(model, X[split["validation"]])
                predictions = probabilities.argmax(axis=1).astype(np.int8)
                oof_predictions[split["validation"]] = predictions
                oof_probabilities[split["validation"]] = probabilities
                fold_metrics = classification_metrics(
                    y[split["validation"]], predictions
                )
                fold_rows.append(
                    metric_row(
                        model_name,
                        repeat,
                        split["fold"],
                        fold_metrics,
                        training_seconds,
                    )
                )
            if (oof_predictions < 0).any() or np.isnan(oof_probabilities).any():
                raise AssertionError(f"Incomplete OOF predictions for {model_name}/{repeat}.")
            metrics = classification_metrics(y, oof_predictions)
            repeat_rows.append(metric_row(model_name, repeat, None, metrics))
            all_repeat_targets.append(y.copy())
            all_repeat_predictions.append(oof_predictions.copy())
            for position in range(len(y)):
                record: dict[str, Any] = {
                    "model": model_name,
                    "repeat": repeat,
                    "source_row_index": int(source_rows[position]),
                    "package": str(packages[position]),
                    "normalized_group_id": str(groups[position]),
                    "actual_class": MODEL_CLASS_NAMES[int(y[position])],
                    "predicted_class": MODEL_CLASS_NAMES[int(oof_predictions[position])],
                    "correct": bool(oof_predictions[position] == y[position]),
                    "raw_max_probability_not_calibrated": float(
                        oof_probabilities[position].max()
                    ),
                }
                for class_index, class_name in enumerate(MODEL_CLASS_NAMES):
                    slug = class_name.casefold().replace(" ", "_")
                    record[f"raw_probability_{slug}"] = float(
                        oof_probabilities[position, class_index]
                    )
                prediction_rows.append(record)
        repeated_confusions[model_name] = classification_metrics(
            np.concatenate(all_repeat_targets), np.concatenate(all_repeat_predictions)
        )["confusion_matrix"]

    fold_frame = pd.DataFrame(fold_rows)
    repeat_frame = pd.DataFrame(repeat_rows)
    prediction_frame = pd.DataFrame(prediction_rows)
    summary = summarize_repeated_cv(repeat_frame)
    selection = select_model_family(summary, repeat_frame)
    return fold_frame, repeat_frame, prediction_frame, summary, {
        "selection": selection,
        "repeated_oof_confusion_matrices": repeated_confusions,
    }


def run_calibration_study(
    selected_model_name: str,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    source_rows: np.ndarray,
    packages: np.ndarray,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    log(f"Running nested grouped calibration study for {selected_model_name}...")
    outer = StratifiedGroupKFold(
        n_splits=5, shuffle=True, random_state=CALIBRATION_OUTER_SEED
    )
    methods = ["raw", "sigmoid", "isotonic"]
    aggregate_probabilities = {
        method: np.full((len(y), len(MODEL_CLASS_NAMES)), np.nan, dtype=np.float64)
        for method in methods
    }
    fold_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []

    for outer_fold, (outer_train, outer_validation) in enumerate(
        outer.split(np.zeros(len(y), dtype=np.uint8), y, groups), start=1
    ):
        if set(groups[outer_train]) & set(groups[outer_validation]):
            raise AssertionError("Calibration outer fold has package leakage.")

        raw_model = create_models()[selected_model_name]
        raw_model.fit(X[outer_train], y[outer_train])
        raw_probabilities = aligned_probabilities(raw_model, X[outer_validation])
        aggregate_probabilities["raw"][outer_validation] = raw_probabilities

        inner_splitter = StratifiedGroupKFold(
            n_splits=4,
            shuffle=True,
            random_state=CALIBRATION_INNER_SEED_BASE + outer_fold,
        )
        inner_splits = list(
            inner_splitter.split(
                np.zeros(len(outer_train), dtype=np.uint8),
                y[outer_train],
                groups[outer_train],
            )
        )
        for inner_train, inner_validation in inner_splits:
            if set(groups[outer_train][inner_train]) & set(
                groups[outer_train][inner_validation]
            ):
                raise AssertionError("Calibration inner fold has package leakage.")
            if set(np.unique(y[outer_train][inner_train])) != set(
                range(len(MODEL_CLASS_NAMES))
            ):
                raise AssertionError("Calibration inner training fold is missing a class.")
            if set(np.unique(y[outer_train][inner_validation])) != set(
                range(len(MODEL_CLASS_NAMES))
            ):
                raise AssertionError("Calibration inner validation fold is missing a class.")

        for method in ("sigmoid", "isotonic"):
            calibrator = CalibratedClassifierCV(
                estimator=create_models()[selected_model_name],
                method=method,
                cv=inner_splits,
                n_jobs=1,
                ensemble=True,
            )
            calibrator.fit(X[outer_train], y[outer_train])
            aggregate_probabilities[method][outer_validation] = aligned_probabilities(
                calibrator, X[outer_validation]
            )

        for method in methods:
            fold_metrics = probability_metrics(
                y[outer_validation],
                aggregate_probabilities[method][outer_validation],
            )
            fold_rows.append(
                {
                    "method": method,
                    "outer_fold": outer_fold,
                    "macro_f1": fold_metrics["macro_f1"],
                    "balanced_accuracy": fold_metrics["balanced_accuracy"],
                    "multiclass_log_loss": fold_metrics["multiclass_log_loss"],
                    "multiclass_brier": fold_metrics[
                        "multiclass_brier_mean_sum_squared_error"
                    ],
                    "top_label_ece": fold_metrics[
                        "top_label_ece_10_equal_width_bins"
                    ],
                }
            )
            probabilities = aggregate_probabilities[method][outer_validation]
            predictions = probabilities.argmax(axis=1)
            for local_index, position in enumerate(outer_validation):
                record: dict[str, Any] = {
                    "method": method,
                    "outer_fold": outer_fold,
                    "source_row_index": int(source_rows[position]),
                    "package": str(packages[position]),
                    "normalized_group_id": str(groups[position]),
                    "actual_class": MODEL_CLASS_NAMES[int(y[position])],
                    "predicted_class": MODEL_CLASS_NAMES[int(predictions[local_index])],
                }
                for class_index, class_name in enumerate(MODEL_CLASS_NAMES):
                    slug = class_name.casefold().replace(" ", "_")
                    record[f"probability_{slug}"] = float(
                        probabilities[local_index, class_index]
                    )
                prediction_rows.append(record)

    aggregate_metrics: dict[str, Any] = {}
    for method in methods:
        if np.isnan(aggregate_probabilities[method]).any():
            raise AssertionError(f"Incomplete calibration OOF probabilities: {method}")
        aggregate_metrics[method] = probability_metrics(
            y, aggregate_probabilities[method]
        )

    fold_frame = pd.DataFrame(fold_rows)
    raw = aggregate_metrics["raw"]
    sigmoid = aggregate_metrics["sigmoid"]
    isotonic = aggregate_metrics["isotonic"]
    macro_tolerance = 0.005
    ece_tolerance = 0.005
    sigmoid_eligible = (
        sigmoid["multiclass_log_loss"] < raw["multiclass_log_loss"]
        and sigmoid["multiclass_brier_mean_sum_squared_error"]
        < raw["multiclass_brier_mean_sum_squared_error"]
        and sigmoid["top_label_ece_10_equal_width_bins"]
        <= raw["top_label_ece_10_equal_width_bins"] + ece_tolerance
        and sigmoid["macro_f1"] >= raw["macro_f1"] - macro_tolerance
    )
    isotonic_logloss_wins = int(
        (
            fold_frame.loc[fold_frame["method"] == "isotonic", "multiclass_log_loss"].to_numpy()
            < fold_frame.loc[fold_frame["method"] == "sigmoid", "multiclass_log_loss"].to_numpy()
        ).sum()
    )
    isotonic_eligible = (
        sigmoid_eligible
        and isotonic["multiclass_log_loss"] < sigmoid["multiclass_log_loss"]
        and isotonic["multiclass_brier_mean_sum_squared_error"]
        < sigmoid["multiclass_brier_mean_sum_squared_error"]
        and isotonic["top_label_ece_10_equal_width_bins"]
        <= sigmoid["top_label_ece_10_equal_width_bins"]
        and isotonic["macro_f1"] >= raw["macro_f1"] - macro_tolerance
        and isotonic_logloss_wins >= 4
    )
    if isotonic_eligible:
        calibration_candidate = "isotonic"
    elif sigmoid_eligible:
        calibration_candidate = "sigmoid"
    else:
        calibration_candidate = None

    study = {
        "selected_model_family": selected_model_name,
        "protocol": {
            "outer": "5-fold StratifiedGroupKFold, package-disjoint",
            "outer_seed": CALIBRATION_OUTER_SEED,
            "inner": "explicit 4-fold StratifiedGroupKFold passed to CalibratedClassifierCV",
            "inner_seed_base": CALIBRATION_INNER_SEED_BASE,
            "calibrated_ensemble": True,
            "methods": methods,
            "evaluation_data": "outer held-out package groups only",
        },
        "metrics": aggregate_metrics,
        "candidate_rule": {
            "sigmoid": (
                "Must improve aggregate log loss and multiclass Brier over raw, keep top-label "
                "ECE within +0.005, and keep Macro F1 within -0.005."
            ),
            "isotonic": (
                "Must first satisfy sigmoid eligibility, then beat sigmoid aggregate log loss "
                "and Brier, not worsen ECE, keep Macro F1 within -0.005 of raw, and beat "
                "sigmoid log loss in at least four of five outer folds."
            ),
            "isotonic_outer_fold_logloss_wins_over_sigmoid": isotonic_logloss_wins,
        },
        "calibration_candidate_method": calibration_candidate,
        "independent_validation": False,
        "post_selection_caveat": (
            "Model-family selection and calibration exploration reuse the same development "
            "cohort. Nested grouping prevents direct fit/evaluation leakage, but the comparison "
            "can still be post-selection optimistic."
        ),
        "user_facing_confidence_allowed": False,
        "reason_user_facing_confidence_disallowed": (
            "Nested grouped CV describes the capped historical CICMalDroid study distribution, "
            "not current deployment prevalence, and no fresh package-unseen four-class holdout "
            "is available. Probabilities are conditional on an upstream malicious decision and "
            "on the true type being one of the four supported classes."
        ),
    }
    return study, fold_frame, pd.DataFrame(prediction_rows)


def save_confusion_csv(path: Path, matrix_payload: dict[str, Any]) -> None:
    labels = matrix_payload["labels"]
    matrix = matrix_payload["rows_actual_columns_predicted"]
    frame = pd.DataFrame(matrix, index=labels, columns=labels)
    frame.index.name = "actual_class"
    frame.to_csv(path, encoding="utf-8")


def export_selected_candidate(
    selected_model_name: str,
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    feature_sha256: str,
    development_manifest_sha256: str,
    selection: dict[str, Any],
    calibration_study: dict[str, Any],
) -> Path:
    if sklearn.__version__ != EXPECTED_SKLEARN_VERSION:
        raise RuntimeError("Refusing to export under the wrong scikit-learn version.")
    model = create_models()[selected_model_name]
    model.fit(X, y)
    bundle = {
        "experimental": True,
        "provisional_validation_candidate": True,
        "integrated_with_fastapi": False,
        "binary_detectors_modified": False,
        "fresh_four_class_holdout_evaluated": False,
        "integration_justified": False,
        "model": model,
        "model_name": selected_model_name,
        "class_names_in_probability_order": MODEL_CLASS_NAMES,
        "feature_names": feature_names,
        "feature_list_sha256": feature_sha256,
        "training_rows": int(len(y)),
        "training_class_counts": class_counts(y),
        "development_manifest_sha256": development_manifest_sha256,
        "selection": selection,
        "probabilities_calibrated": False,
        "calibration_candidate_method_not_exported": calibration_study[
            "calibration_candidate_method"
        ],
        "user_facing_confidence_allowed": False,
        "probability_semantics": (
            "Raw four-class model output, conditional on upstream malicious classification and "
            "the true category being one of the four supported classes; not deployment-calibrated."
        ),
        "input_contract": {
            "source": "static APK permission extractor",
            "representation": "binary presence in saved feature order",
            "dynamic_syscall_or_binder_features": False,
        },
        "scikit_learn_version": sklearn.__version__,
    }
    output_path = ARTIFACTS_DIR / "selected_category_model_provisional.joblib"
    joblib.dump(bundle, output_path)
    return output_path


def report_markdown(
    historical: dict[str, Any],
    development_summary: dict[str, Any],
    cv_summary: dict[str, Any],
    selection: dict[str, Any],
    calibration: dict[str, Any],
    holdout_status: dict[str, Any],
    environment: dict[str, Any],
    selected_confusion: dict[str, Any],
) -> str:
    historical_named_rows = sum(EXPECTED_HISTORICAL_NAMED_ROWS.values())
    additional_named_rows = development_summary["rows"] - historical_named_rows
    lines = [
        "# CICMalDroid final model-selection and validation report",
        "",
        "## Outcome",
        "",
        f"Repeated grouped CV selected **{selection['selected_model']}** using the precommitted one-standard-error stability rule. The historical test results were not used to select or change the family.",
        "",
        "A strict fresh four-class package-unseen holdout could not be created: the current corpus contains zero never-used Banking Malware packages and zero never-used SMS Malware packages. No replacement holdout was manufactured, and no fresh-holdout score or confusion matrix is reported.",
        "",
        "**Integration is not yet justified**, regardless of the CV result. New independently labelled Banking and SMS packages compatible with the 153-permission schema are required.",
        "",
        "## Historical POC preserved",
        "",
        "The existing POC files were hash-verified before and after this run. Its selection remains HistGradientBoosting on validation Macro F1. Random Forest's higher old test score remains reporting-only and did not retroactively alter that decision.",
        "",
        "| Model | Historical validation Macro F1 | Historical test Macro F1 |",
        "|---|---:|---:|",
    ]
    historical_frame = pd.DataFrame(historical["results"])
    for model_name in create_models():
        validation = historical_frame[
            (historical_frame["model"] == model_name)
            & (historical_frame["split"] == "validation")
        ].iloc[0]
        test = historical_frame[
            (historical_frame["model"] == model_name)
            & (historical_frame["split"] == "test")
        ].iloc[0]
        lines.append(
            f"| {model_name} | {validation['macro_f1']:.8f} | {test['macro_f1']:.8f} |"
        )

    lines.extend(
        [
            "",
            "## Development protocol",
            "",
            f"- scikit-learn: `{environment['scikit_learn']}` (exact backend pin matched)",
            f"- Ordered static permission features: {EXPECTED_FEATURE_COUNT}",
            f"- Cohort: {development_summary['rows']:,} rows ({DEVELOPMENT_ROWS_PER_CLASS} per class)",
            f"- Composition: {historical_named_rows:,} named historical train/validation rows plus {additional_named_rows:,} unused named rows from the same development package universe",
            f"- Blank-package rows excluded because package isolation cannot be verified: {development_summary['blank_package_rows_excluded']}",
            f"- Package cap: {MAX_ROWS_PER_PACKAGE} rows per normalized package",
            f"- Cross-validation: {CV_REPEATS} repeats x {CV_FOLDS} folds of StratifiedGroupKFold",
            "- Package identifiers were stripped and case-folded for conservative grouping; package is not a model feature",
            "- Every historical test package was quarantined in full, including its unused rows",
            "- No SMOTE, no oversampling, no syscall features, and no Binder features",
            "",
            "## Repeated grouped cross-validation",
            "",
            "Metrics below are the mean and sample standard deviation across five complete repeat-level OOF predictions; each row is scored exactly once per repeat.",
            "",
            "| Model | Mean Macro F1 | SD | Mean balanced accuracy | SD | Mean worst-class recall |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for model_name, metrics in cv_summary.items():
        lines.append(
            "| "
            + model_name
            + f" | {metrics['mean_macro_f1']:.6f} | {metrics['macro_f1_sample_standard_deviation']:.6f}"
            + f" | {metrics['mean_balanced_accuracy']:.6f} | {metrics['balanced_accuracy_sample_standard_deviation']:.6f}"
            + f" | {metrics['mean_worst_class_recall']:.6f} |"
        )

    lines.extend(
        [
            "",
            "### Per-class precision and recall across repeats",
            "",
            "These are repeated-CV diagnostics, not fresh-holdout estimates.",
            "",
            "| Model / class | Precision mean +/- SD | Recall mean +/- SD |",
            "|---|---:|---:|",
        ]
    )
    for model_name, metrics in cv_summary.items():
        for name in MODEL_CLASS_NAMES:
            precision = metrics["per_class_precision"][name]
            recall = metrics["per_class_recall"][name]
            lines.append(
                f"| {model_name} / {name} | "
                f"{precision['mean']:.6f} +/- {precision['sample_standard_deviation']:.6f} | "
                f"{recall['mean']:.6f} +/- {recall['sample_standard_deviation']:.6f} |"
            )

    selected = cv_summary[selection["selected_model"]]
    lines.extend(
        [
            "",
            "## Selection decision",
            "",
            f"- Raw mean-Macro-F1 leader: **{selection['raw_mean_macro_f1_leader']}**",
            f"- One-standard-error threshold: {selection['one_standard_error_threshold']:.6f}",
            f"- Eligible families: {', '.join(selection['eligible_models'])}",
            f"- Selected family: **{selection['selected_model']}**",
            f"- Selected mean Macro F1: {selected['mean_macro_f1']:.6f}",
            f"- Selected Macro-F1 SD: {selected['macro_f1_sample_standard_deviation']:.6f}",
            "",
            selection["rule"],
            "This one-standard-error rule is a precommitted stability heuristic, not a formal independent-sample confidence interval; repeat OOF scores are dependent and five repeats give a noisy SD estimate.",
            "",
            "## Selected-family repeated-OOF confusion matrix",
            "",
            "This matrix aggregates five repeat-level OOF prediction vectors. It is a CV diagnostic, not a fresh-holdout matrix.",
            "",
            "| Actual / predicted | " + " | ".join(MODEL_CLASS_NAMES) + " |",
            "|---|" + "---:|" * len(MODEL_CLASS_NAMES),
        ]
    )
    for name, row in zip(
        selected_confusion["labels"],
        selected_confusion["rows_actual_columns_predicted"],
        strict=True,
    ):
        lines.append(f"| {name} | " + " | ".join(str(value) for value in row) + " |")

    lines.extend(
        [
            "",
            "## Calibration findings",
            "",
            "Calibration was studied separately with nested package-grouped CV. Values remain conditional on the capped historical four-class study distribution.",
            "Because model-family selection and calibration exploration reuse the same development cohort, the calibration comparison may be post-selection optimistic and is not independent validation.",
            "",
            "| Method | Macro F1 | Log loss | Multiclass Brier | Top-label ECE |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for method in ("raw", "sigmoid", "isotonic"):
        metrics = calibration["metrics"][method]
        lines.append(
            f"| {method} | {metrics['macro_f1']:.6f} | {metrics['multiclass_log_loss']:.6f}"
            + f" | {metrics['multiclass_brier_mean_sum_squared_error']:.6f}"
            + f" | {metrics['top_label_ece_10_equal_width_bins']:.6f} |"
        )
    candidate = calibration["calibration_candidate_method"] or "none"
    lines.extend(
        [
            "",
            f"Rule-qualified calibration candidate: **{candidate}**.",
            "",
            "No probability is approved as user-facing confidence. Even a calibrated value here is not a current real-world likelihood: it assumes the binary detector already said malicious and the true type is one of these four classes. Other malware families would be forced into a known class.",
            "",
            "## Fresh holdout status",
            "",
            f"- Status: **{holdout_status['status']}**",
            "- Fresh holdout Macro F1: not computed",
            "- Fresh holdout per-class precision/recall: not computed",
            "- Fresh holdout confusion matrix: not computed",
            "",
            "| Class | Never-used rows | Never-used normalized groups | Verifiably named groups |",
            "|---|---:|---:|---:|",
        ]
    )
    for name, item in holdout_status["never_seen_inventory"].items():
        lines.append(
            f"| {name} | {item['rows']} | {item['normalized_groups']} | {item['verifiably_named_groups']} |"
        )

    lines.extend(
        [
            "",
            "## Final recommendation",
            "",
            "Do not integrate the category model into FastAPI yet. Obtain a frozen, independently labelled, schema-compatible holdout with new package groups in all four classes (especially Banking and SMS), ideally with APK hashes for duplicate/repackaging checks. Lock the family and calibration method first, then evaluate that holdout exactly once.",
            "",
            "The exported joblib is deliberately named `selected_category_model_provisional.joblib`. It was fitted under scikit-learn 1.6.1, but metadata marks it uncalibrated, not integrated, and not justified for production use.",
            "",
            "## Material limitations retained from the POC",
            "",
            f"- Category labels remain positionally aligned rather than hash-joined: {development_summary['label_alignment_assumption']}",
            f"- Cross-label package conflicts excluded before cohort construction: {development_summary['cross_label_conflict_package_count']} packages / {development_summary['cross_label_conflict_rows_removed']} rows.",
            "- Package grouping cannot prove that different package names are repackaged copies because the static table has no APK hash join.",
            "- CICMalDroid is historical and the permission-only representation omits richer static signals.",
            "- The classifier is closed-set: unsupported malware types are forced into one of four known categories.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    started = time.perf_counter()
    if sklearn.__version__ != EXPECTED_SKLEARN_VERSION:
        raise RuntimeError(
            f"This run requires scikit-learn {EXPECTED_SKLEARN_VERSION}; "
            f"found {sklearn.__version__}."
        )
    if ARTIFACTS_DIR.exists() and any(ARTIFACTS_DIR.iterdir()):
        raise RuntimeError(
            f"Refusing to mix a new run with existing artifacts in {ARTIFACTS_DIR}. "
            "Archive the directory before rerunning."
        )
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    log("Verifying immutable historical POC artifacts...")
    historical_hashes_before = verify_historical_artifacts()
    historical = historical_snapshot(historical_hashes_before)
    write_json(ARTIFACTS_DIR / "historical_poc_results.json", historical)

    log("Verifying source-data fingerprints...")
    source_fingerprints = verify_source_data_fingerprints()

    log("Reconstructing the 153 static-permission feature matrix...")
    data = load_full_clean_permission_data()
    inventory = build_partition_inventory(data)

    holdout_status = {
        "status": "unavailable_current_corpus",
        "strict_requirement": (
            "Fresh samples must have normalized package groups absent from historical train, "
            "validation, and test, and all four classes must be represented."
        ),
        "never_seen_inventory": inventory["never_seen_inventory"],
        "blocking_classes": [
            name
            for name, item in inventory["never_seen_inventory"].items()
            if item["verifiably_named_groups"] == 0
        ],
        "fresh_holdout_created": False,
        "fresh_holdout_evaluated": False,
        "fresh_holdout_macro_f1": None,
        "fresh_holdout_per_class_precision_recall": None,
        "fresh_holdout_confusion_matrix": None,
        "substitution_with_unused_rows_from_seen_packages": False,
        "required_next_data": (
            "Independently labelled, schema-compatible new Banking Malware and SMS Malware "
            "packages (and preferably new packages for all classes), with hashes."
        ),
    }
    write_json(ARTIFACTS_DIR / "fresh_holdout_status.json", holdout_status)
    pd.DataFrame.from_dict(
        inventory["never_seen_inventory"], orient="index"
    ).rename_axis("class_name").reset_index().to_csv(
        ARTIFACTS_DIR / "fresh_holdout_feasibility.csv", index=False, encoding="utf-8"
    )

    log("Building the frozen balanced development cohort...")
    cohort_positions, development_manifest, development_summary = (
        build_balanced_development_cohort(data, inventory)
    )
    development_manifest_path = ARTIFACTS_DIR / "development_manifest.csv"
    development_manifest.to_csv(
        development_manifest_path, index=False, encoding="utf-8"
    )
    development_manifest_sha256 = sha256_file(development_manifest_path)
    development_summary["manifest_sha256"] = development_manifest_sha256
    development_summary["available_development_inventory_before_blank_exclusion"] = inventory[
        "observed_development"
    ]
    development_summary["eligible_named_development_inventory_before_balancing"] = inventory[
        "observed_named_development"
    ]
    development_summary["label_alignment_assumption"] = data["alignment_audit"][
        "assumption"
    ]
    development_summary["cross_label_conflict_package_count"] = len(
        data["cross_label_conflicts"]
    )
    development_summary["cross_label_conflict_rows_removed"] = sum(
        int(record["total_rows"]) for record in data["cross_label_conflicts"]
    )
    write_json(ARTIFACTS_DIR / "development_summary.json", development_summary)

    X = data["X"][cohort_positions]
    y = data["y"][cohort_positions]
    groups = data["groups"][cohort_positions]
    source_rows = data["source_rows"][cohort_positions]
    packages = data["packages"][cohort_positions]

    splits, fold_assignments = build_repeated_group_splits(y, groups)
    fold_assignments["source_row_index"] = source_rows[
        fold_assignments["cohort_position"].to_numpy(dtype=int)
    ]
    fold_assignments.to_csv(
        ARTIFACTS_DIR / "cv_fold_assignments.csv", index=False, encoding="utf-8"
    )

    fold_metrics, repeat_metrics, predictions, cv_summary, selection_payload = (
        run_model_comparison(X, y, groups, source_rows, packages, splits)
    )
    fold_metrics.to_csv(
        ARTIFACTS_DIR / "cv_fold_metrics.csv",
        index=False,
        encoding="utf-8",
        float_format="%.10f",
    )
    repeat_metrics.to_csv(
        ARTIFACTS_DIR / "cv_repeat_metrics.csv",
        index=False,
        encoding="utf-8",
        float_format="%.10f",
    )
    predictions.to_csv(
        ARTIFACTS_DIR / "cv_oof_predictions.csv",
        index=False,
        encoding="utf-8",
        float_format="%.10f",
    )
    selection = selection_payload["selection"]
    cv_payload = {
        "protocol": {
            "repeats": CV_REPEATS,
            "folds": CV_FOLDS,
            "seeds": CV_SEEDS,
            "splitter": "StratifiedGroupKFold",
            "group": "normalized package (strip + casefold); missing package is unique row group",
            "same_splits_for_all_models": True,
            "repeat_metric": "concatenated complete OOF vector; each row once per repeat",
            "historical_test_packages_excluded_in_full": True,
        },
        "models": cv_summary,
        **selection_payload,
    }
    write_json(ARTIFACTS_DIR / "cv_results.json", cv_payload)
    selected_confusion = selection_payload["repeated_oof_confusion_matrices"][
        selection["selected_model"]
    ]
    save_confusion_csv(
        ARTIFACTS_DIR / "selected_model_repeated_oof_confusion_matrix.csv",
        selected_confusion,
    )

    calibration, calibration_folds, calibration_predictions = run_calibration_study(
        selection["selected_model"], X, y, groups, source_rows, packages
    )
    write_json(ARTIFACTS_DIR / "calibration_results.json", calibration)
    calibration_folds.to_csv(
        ARTIFACTS_DIR / "calibration_fold_metrics.csv",
        index=False,
        encoding="utf-8",
        float_format="%.10f",
    )
    calibration_predictions.to_csv(
        ARTIFACTS_DIR / "calibration_oof_predictions.csv",
        index=False,
        encoding="utf-8",
        float_format="%.10f",
    )

    model_path = export_selected_candidate(
        selection["selected_model"],
        X,
        y,
        data["feature_names"],
        data["feature_sha256"],
        development_manifest_sha256,
        selection,
        calibration,
    )

    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "scikit_learn": sklearn.__version__,
        "scipy": scipy.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "joblib": joblib.__version__,
        "required_scikit_learn": EXPECTED_SKLEARN_VERSION,
        "exact_version_match": sklearn.__version__ == EXPECTED_SKLEARN_VERSION,
    }
    write_json(ARTIFACTS_DIR / "environment.json", environment)

    run_manifest = {
        "experimental": True,
        "integrated_with_fastapi": False,
        "binary_detectors_modified": False,
        "feature_count": len(data["feature_names"]),
        "feature_sha256": data["feature_sha256"],
        "classes": MODEL_CLASS_NAMES,
        "label_alignment_audit": data["alignment_audit"],
        "cross_label_conflict_package_count": len(data["cross_label_conflicts"]),
        "cross_label_conflict_rows_removed": sum(
            int(record["total_rows"]) for record in data["cross_label_conflicts"]
        ),
        "source_data_fingerprints_verified_current_run": source_fingerprints,
        "historical_artifact_hashes_before": historical_hashes_before,
        "development_manifest_sha256": development_manifest_sha256,
        "selected_model_artifact": model_path.name,
        "selected_model_artifact_sha256": sha256_file(model_path),
        "selected_model": selection["selected_model"],
        "fresh_holdout_evaluated": False,
        "calibration_candidate_method": calibration["calibration_candidate_method"],
        "probabilities_approved_for_user_facing_confidence": False,
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    historical_hashes_after = verify_historical_artifacts()
    if historical_hashes_after != historical_hashes_before:
        raise AssertionError("Historical POC artifact hashes changed during this run.")
    run_manifest["historical_artifact_hashes_after"] = historical_hashes_after
    run_manifest["historical_artifacts_unchanged"] = True
    write_json(ARTIFACTS_DIR / "run_manifest.json", run_manifest)

    report = report_markdown(
        historical,
        development_summary,
        cv_summary,
        selection,
        calibration,
        holdout_status,
        environment,
        selected_confusion,
    )
    (OUTPUT_ROOT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json(
        ARTIFACTS_DIR / "COMPLETED.json",
        {
            "status": "completed",
            "run_manifest_sha256": sha256_file(ARTIFACTS_DIR / "run_manifest.json"),
            "report_sha256": sha256_file(OUTPUT_ROOT / "REPORT.md"),
            "historical_artifacts_unchanged": True,
            "fresh_four_class_holdout_evaluated": False,
        },
    )
    log(
        f"Completed in {time.perf_counter() - started:.1f}s. "
        f"Selected family: {selection['selected_model']}. "
        "Fresh holdout not evaluated because the current corpus cannot satisfy it."
    )


if __name__ == "__main__":
    main()

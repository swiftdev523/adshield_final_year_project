"""Describe the already-consumed supplementary holdout after rule locking.

This script performs no threshold search.  It refuses to run unless the
development-selected abstention rule has already been written and locked.  Its
outputs are descriptive diagnostics, not a clean V2 evaluation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_DIR = (
    ROOT / "models" / "category_final_validation" / "abstention_analysis"
)
LOCKED_RULE = ANALYSIS_DIR / "locked_abstention_rule.json"
HOLDOUT_PREDICTIONS = (
    ROOT
    / "models"
    / "category_final_validation"
    / "category_validation"
    / "final_evaluation"
    / "final_predictions.csv"
)

CLASS_NAMES = ["Adware", "Banking Malware", "SMS Malware", "Riskware"]
SOURCE_SCORE_COLUMNS = [
    "raw_uncalibrated_probability_adware",
    "raw_uncalibrated_probability_banking_malware",
    "raw_uncalibrated_probability_sms_malware",
    "raw_uncalibrated_probability_riskware",
]
OUTPUT_SCORE_COLUMNS = [
    "score_adware",
    "score_banking_malware",
    "score_sms_malware",
    "score_riskware",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_locked_margin() -> float:
    with LOCKED_RULE.open("r", encoding="utf-8") as handle:
        lock = json.load(handle)
    if lock["status"] != "locked_for_future_untouched_v2_validation":
        raise AssertionError("Abstention rule is not locked")
    if lock["selection_evidence"]["supplementary_196_sample_holdout_used_for_selection"]:
        raise AssertionError("Lock metadata improperly claims holdout selection")
    if lock["rule"]["accept_when"] != "top_two_margin >= 0.70":
        raise AssertionError("Unexpected locked rule")
    return 0.70


def load_predictions() -> pd.DataFrame:
    source = pd.read_csv(HOLDOUT_PREDICTIONS)
    if len(source) != 196:
        raise AssertionError(f"Expected 196 holdout rows, found {len(source)}")
    scores = source[SOURCE_SCORE_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(scores).all() or not np.allclose(
        scores.sum(axis=1), 1.0, atol=2e-8
    ):
        raise AssertionError("Invalid saved holdout class scores")

    descending_order = np.argsort(-scores, axis=1, kind="stable")
    row_index = np.arange(len(source))
    top_index = descending_order[:, 0]
    second_index = descending_order[:, 1]
    top_score = scores[row_index, top_index]
    second_score = scores[row_index, second_index]
    top_class = np.asarray(CLASS_NAMES, dtype=object)[top_index]
    second_class = np.asarray(CLASS_NAMES, dtype=object)[second_index]
    actual = source["true_class_name"].to_numpy(dtype=object)
    correct = top_class == actual

    if not np.array_equal(
        top_class, source["predicted_class_name"].to_numpy(dtype=object)
    ):
        raise AssertionError("Holdout argmax does not match saved prediction")
    if not np.array_equal(correct, source["correct"].astype(bool).to_numpy()):
        raise AssertionError("Holdout correctness flag mismatch")
    if not np.allclose(
        top_score,
        source["raw_max_probability_not_calibrated"].to_numpy(dtype=float),
        atol=2e-8,
    ):
        raise AssertionError("Holdout saved maximum score mismatch")

    result = source[
        [
            "holdout_row_index",
            "package",
            "normalized_package",
            "sha256",
            "source_type",
            "true_class_name",
        ]
    ].rename(columns={"true_class_name": "actual_class"})
    result["top_predicted_class"] = top_class
    result["top_score"] = top_score
    result["second_highest_class"] = second_class
    result["second_highest_score"] = second_score
    result["top_two_margin"] = top_score - second_score
    result["correct"] = correct
    for source_column, output_column in zip(
        SOURCE_SCORE_COLUMNS, OUTPUT_SCORE_COLUMNS, strict=True
    ):
        result[output_column] = source[source_column].to_numpy(dtype=float)
    return result


def distribution(frame: pd.DataFrame, group: str) -> dict[str, object]:
    result: dict[str, object] = {
        "group": group,
        "samples": int(len(frame)),
        "accuracy": float(frame["correct"].mean()),
    }
    for column in ["top_score", "second_highest_score", "top_two_margin"]:
        values = frame[column].to_numpy(dtype=float)
        result.update(
            {
                f"{column}_mean": float(values.mean()),
                f"{column}_p25": float(np.quantile(values, 0.25)),
                f"{column}_median": float(np.median(values)),
                f"{column}_p75": float(np.quantile(values, 0.75)),
            }
        )
    return result


def safe_rate(numerator: np.ndarray, denominator: np.ndarray) -> float | None:
    count = int(denominator.sum())
    if not count:
        return None
    return float(np.logical_and(numerator, denominator).sum() / count)


def main() -> None:
    locked_margin = load_locked_margin()
    frame = load_predictions()
    accepted = frame["top_two_margin"].to_numpy(dtype=float) >= locked_margin
    actual = frame["actual_class"].to_numpy(dtype=object)
    predicted = frame["top_predicted_class"].to_numpy(dtype=object)
    correct = frame["correct"].to_numpy(dtype=bool)

    per_class = []
    accepted_precisions = []
    for class_name in CLASS_NAMES:
        actual_class = actual == class_name
        predicted_class = predicted == class_name
        actual_accepted = actual_class & accepted
        predicted_accepted = predicted_class & accepted
        accepted_precision = safe_rate(correct, predicted_accepted)
        if accepted_precision is None:
            raise AssertionError(f"No accepted {class_name} predictions")
        accepted_precisions.append(accepted_precision)
        per_class.append(
            {
                "class": class_name,
                "actual_count": int(actual_class.sum()),
                "actual_accepted_count": int(actual_accepted.sum()),
                "true_class_coverage": safe_rate(accepted, actual_class),
                "actual_class_accepted_accuracy": safe_rate(
                    correct, actual_accepted
                ),
                "accepted_predicted_count": int(predicted_accepted.sum()),
                "accepted_precision": accepted_precision,
            }
        )

    overall = {
        "status": "descriptive_only_not_clean_v2_evaluation",
        "threshold_search_on_holdout": False,
        "locked_margin_applied": locked_margin,
        "sample_count": int(len(frame)),
        "accepted_count": int(accepted.sum()),
        "rejected_count": int((~accepted).sum()),
        "coverage": float(accepted.mean()),
        "accepted_accuracy": float(correct[accepted].mean()),
        "accepted_macro_precision": float(np.mean(accepted_precisions)),
        "input_path": str(HOLDOUT_PREDICTIONS.relative_to(ROOT)).replace("\\", "/"),
        "input_sha256": sha256_file(HOLDOUT_PREDICTIONS),
        "warning": (
            "This 196-sample holdout was consumed previously and did not influence "
            "the threshold or locked rule. Results are descriptive only."
        ),
    }

    correctness_diagnostics = pd.DataFrame(
        [
            distribution(frame.loc[frame["correct"]], "correct"),
            distribution(frame.loc[~frame["correct"]], "incorrect"),
        ]
    )
    banking = frame.loc[frame["actual_class"].eq("Banking Malware")]
    banking_diagnostics = pd.DataFrame(
        [
            distribution(
                banking.loc[banking["top_predicted_class"].eq(class_name)],
                f"Banking actual -> {class_name}",
            )
            for class_name in CLASS_NAMES
            if banking["top_predicted_class"].eq(class_name).any()
        ]
    )

    frame.to_csv(
        ANALYSIS_DIR / "supplementary_holdout_prediction_scores_descriptive.csv",
        index=False,
    )
    pd.DataFrame(per_class).to_csv(
        ANALYSIS_DIR / "supplementary_holdout_locked_rule_per_class_descriptive.csv",
        index=False,
    )
    correctness_diagnostics.to_csv(
        ANALYSIS_DIR / "supplementary_holdout_diagnostic_by_correctness.csv",
        index=False,
    )
    banking_diagnostics.to_csv(
        ANALYSIS_DIR / "supplementary_holdout_banking_diagnostics.csv",
        index=False,
    )
    with (
        ANALYSIS_DIR / "supplementary_holdout_locked_rule_descriptive.json"
    ).open("w", encoding="utf-8") as handle:
        json.dump(overall, handle, indent=2)
        handle.write("\n")

    print(json.dumps(overall, indent=2))


if __name__ == "__main__":
    main()

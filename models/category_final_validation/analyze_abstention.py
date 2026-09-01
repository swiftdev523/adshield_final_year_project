"""Analyze selective classification for the saved four-class Random Forest.

This script is deliberately post-hoc and read-only with respect to the fitted
model.  It consumes saved out-of-fold predictions; it never fits, tunes,
calibrates, or serializes a classifier and it does not touch FastAPI.

The primary analysis cohort is the five-repeat StratifiedGroupKFold prediction
artifact.  Each development row appears once per repeat, so pooled counts are
prediction events rather than independent applications.  Repeat-level metrics
are exported separately to make that dependence visible.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
CV_PREDICTIONS = (
    ROOT
    / "models"
    / "category_final_validation"
    / "artifacts"
    / "cv_oof_predictions.csv"
)
OUTPUT_DIR = (
    ROOT / "models" / "category_final_validation" / "abstention_analysis"
)

MODEL_NAME = "Random Forest"
CLASS_NAMES = ["Adware", "Banking Malware", "SMS Malware", "Riskware"]
SOURCE_SCORE_COLUMNS = [
    "raw_probability_adware",
    "raw_probability_banking_malware",
    "raw_probability_sms_malware",
    "raw_probability_riskware",
]
OUTPUT_SCORE_COLUMNS = [
    "score_adware",
    "score_banking_malware",
    "score_sms_malware",
    "score_riskware",
]

TOP_SCORE_THRESHOLDS = np.round(np.arange(0.50, 0.901, 0.05), 2)
MARGIN_THRESHOLDS = np.round(np.arange(0.00, 0.901, 0.05), 2)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fmt_threshold(value: float | None) -> str:
    return "none" if value is None else f"{value:.2f}"


def load_random_forest_predictions() -> pd.DataFrame:
    source = pd.read_csv(CV_PREDICTIONS)
    frame = source.loc[source["model"].eq(MODEL_NAME)].copy()

    required = {
        "repeat",
        "source_row_index",
        "package",
        "normalized_group_id",
        "actual_class",
        "predicted_class",
        "correct",
        "raw_max_probability_not_calibrated",
        *SOURCE_SCORE_COLUMNS,
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required OOF columns: {sorted(missing)}")

    if len(frame) != 17_580:
        raise AssertionError(f"Expected 17,580 Random Forest rows, found {len(frame):,}")
    if sorted(frame["repeat"].unique().tolist()) != [1, 2, 3, 4, 5]:
        raise AssertionError("Expected repeats 1 through 5")
    repeat_sizes = frame.groupby("repeat", observed=True).size()
    if not repeat_sizes.eq(3_516).all():
        raise AssertionError(f"Each repeat must contain 3,516 rows: {repeat_sizes.to_dict()}")
    if set(frame["actual_class"]) != set(CLASS_NAMES):
        raise AssertionError("Unexpected actual class labels")

    scores = frame[SOURCE_SCORE_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(scores).all():
        raise AssertionError("Non-finite class score found")
    if ((scores < -1e-12) | (scores > 1 + 1e-12)).any():
        raise AssertionError("Class score outside [0, 1]")
    if not np.allclose(scores.sum(axis=1), 1.0, atol=2e-8):
        raise AssertionError("Four class scores do not sum to one")

    # Stable ordering mirrors sklearn's ordered numeric classes for exact ties.
    descending_order = np.argsort(-scores, axis=1, kind="stable")
    top_index = descending_order[:, 0]
    second_index = descending_order[:, 1]
    row_index = np.arange(len(frame))
    top_score = scores[row_index, top_index]
    second_score = scores[row_index, second_index]
    top_class = np.asarray(CLASS_NAMES, dtype=object)[top_index]
    second_class = np.asarray(CLASS_NAMES, dtype=object)[second_index]
    correct = top_class == frame["actual_class"].to_numpy(dtype=object)

    if not np.array_equal(top_class, frame["predicted_class"].to_numpy(dtype=object)):
        raise AssertionError("Stored prediction does not match four-score argmax")
    if not np.array_equal(correct, frame["correct"].astype(bool).to_numpy()):
        raise AssertionError("Stored correctness flag does not match derived correctness")
    if not np.allclose(
        top_score,
        frame["raw_max_probability_not_calibrated"].to_numpy(dtype=float),
        atol=2e-8,
    ):
        raise AssertionError("Stored maximum score does not match derived top score")

    result = frame[
        [
            "repeat",
            "source_row_index",
            "package",
            "normalized_group_id",
            "actual_class",
        ]
    ].copy()
    result["top_predicted_class"] = top_class
    result["top_score"] = top_score
    result["second_highest_class"] = second_class
    result["second_highest_score"] = second_score
    result["top_two_margin"] = top_score - second_score
    result["correct"] = correct
    for source_column, output_column in zip(
        SOURCE_SCORE_COLUMNS, OUTPUT_SCORE_COLUMNS, strict=True
    ):
        result[output_column] = frame[source_column].to_numpy(dtype=float)

    # Sensitivity weight: each normalized package contributes total weight one
    # within a repeat, regardless of how many rows it contains.
    group_sizes = result.groupby(
        ["repeat", "normalized_group_id"], observed=True
    )["source_row_index"].transform("size")
    result["package_equal_weight"] = 1.0 / group_sizes.to_numpy(dtype=float)

    return result.sort_values(["repeat", "source_row_index"], kind="stable").reset_index(
        drop=True
    )


def distribution_record(frame: pd.DataFrame, label: str) -> dict[str, object]:
    record: dict[str, object] = {
        "group": label,
        "prediction_events": int(len(frame)),
        "accuracy": float(frame["correct"].mean()) if len(frame) else np.nan,
    }
    for column in ["top_score", "second_highest_score", "top_two_margin"]:
        values = frame[column].to_numpy(dtype=float)
        record.update(
            {
                f"{column}_mean": float(np.mean(values)),
                f"{column}_sd": float(np.std(values, ddof=1)) if len(values) > 1 else np.nan,
                f"{column}_p05": float(np.quantile(values, 0.05)),
                f"{column}_p10": float(np.quantile(values, 0.10)),
                f"{column}_p25": float(np.quantile(values, 0.25)),
                f"{column}_median": float(np.quantile(values, 0.50)),
                f"{column}_p75": float(np.quantile(values, 0.75)),
                f"{column}_p90": float(np.quantile(values, 0.90)),
                f"{column}_p95": float(np.quantile(values, 0.95)),
            }
        )
    return record


def build_diagnostics(predictions: pd.DataFrame) -> tuple[pd.DataFrame, ...]:
    correctness_rows = []
    for correct_value, subset in predictions.groupby("correct", sort=False):
        correctness_rows.append(
            distribution_record(subset, "correct" if correct_value else "incorrect")
        )

    actual_class_rows = []
    class_correctness_rows = []
    for class_name in CLASS_NAMES:
        class_subset = predictions.loc[predictions["actual_class"].eq(class_name)]
        actual_class_rows.append(distribution_record(class_subset, class_name))
        for correct_value in [True, False]:
            subset = class_subset.loc[class_subset["correct"].eq(correct_value)]
            class_correctness_rows.append(
                distribution_record(
                    subset,
                    f"{class_name} | {'correct' if correct_value else 'incorrect'}",
                )
            )

    banking = predictions.loc[predictions["actual_class"].eq("Banking Malware")]
    banking_rows = []
    for predicted_class in CLASS_NAMES:
        subset = banking.loc[banking["top_predicted_class"].eq(predicted_class)]
        if len(subset):
            banking_rows.append(
                distribution_record(subset, f"Banking actual -> {predicted_class}")
            )

    banking_repeat_rows = []
    for repeat, repeat_frame in banking.groupby("repeat", sort=True):
        for outcome in ["Banking Malware", "Adware", "Riskware", "SMS Malware"]:
            subset = repeat_frame.loc[repeat_frame["top_predicted_class"].eq(outcome)]
            if not len(subset):
                continue
            banking_repeat_rows.append(
                {
                    "repeat": int(repeat),
                    "predicted_class": outcome,
                    "prediction_events": int(len(subset)),
                    "top_score_mean": float(subset["top_score"].mean()),
                    "top_score_median": float(subset["top_score"].median()),
                    "top_two_margin_mean": float(subset["top_two_margin"].mean()),
                    "top_two_margin_median": float(subset["top_two_margin"].median()),
                }
            )

    return (
        pd.DataFrame(correctness_rows),
        pd.DataFrame(actual_class_rows),
        pd.DataFrame(class_correctness_rows),
        pd.DataFrame(banking_rows),
        pd.DataFrame(banking_repeat_rows),
    )


def rule_mask(
    frame: pd.DataFrame,
    top_score_threshold: float | None,
    margin_threshold: float | None,
    class_specific_margins: dict[str, float] | None = None,
) -> np.ndarray:
    mask = np.ones(len(frame), dtype=bool)
    if top_score_threshold is not None:
        mask &= frame["top_score"].to_numpy() >= top_score_threshold
    if margin_threshold is not None:
        mask &= frame["top_two_margin"].to_numpy() >= margin_threshold
    if class_specific_margins is not None:
        per_row_threshold = frame["top_predicted_class"].map(
            class_specific_margins
        )
        if per_row_threshold.isna().any():
            raise AssertionError("Class-specific rule lacks a top-class threshold")
        mask &= (
            frame["top_two_margin"].to_numpy(dtype=float)
            >= per_row_threshold.to_numpy(dtype=float)
        )
    return mask


def evaluate_rule(
    frame: pd.DataFrame,
    accepted: np.ndarray,
    rule_id: str,
    rule_type: str,
    top_score_threshold: float | None,
    margin_threshold: float | None,
    class_specific_margins: dict[str, float] | None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    actual = frame["actual_class"].to_numpy(dtype=object)
    predicted = frame["top_predicted_class"].to_numpy(dtype=object)
    correct = frame["correct"].to_numpy(dtype=bool)
    weights = frame["package_equal_weight"].to_numpy(dtype=float)
    total = len(frame)
    accepted_count = int(accepted.sum())
    rejected_count = total - accepted_count

    if accepted_count == 0:
        accepted_accuracy = np.nan
        macro_precision = np.nan
    else:
        accepted_accuracy = float(correct[accepted].mean())
        accepted_precisions = []
        for class_name in CLASS_NAMES:
            accepted_predicted_class = accepted & (predicted == class_name)
            if not accepted_predicted_class.any():
                accepted_precisions = []
                break
            accepted_precisions.append(float(correct[accepted_predicted_class].mean()))
        macro_precision = (
            float(np.mean(accepted_precisions)) if accepted_precisions else np.nan
        )

    banking_actual = actual == "Banking Malware"
    banking_errors = banking_actual & ~correct
    banking_to_adware = banking_actual & (predicted == "Adware")
    banking_to_riskware = banking_actual & (predicted == "Riskware")
    banking_to_sms = banking_actual & (predicted == "SMS Malware")
    predicted_banking = predicted == "Banking Malware"

    def safe_fraction(numerator: np.ndarray, denominator: np.ndarray) -> float:
        denominator_count = int(denominator.sum())
        return (
            float(np.logical_and(numerator, denominator).sum() / denominator_count)
            if denominator_count
            else np.nan
        )

    bank_accepted = banking_actual & accepted
    accepted_predicted_banking = predicted_banking & accepted

    def weighted_rate(numerator: np.ndarray, denominator: np.ndarray) -> float:
        denominator_weight = float(weights[denominator].sum())
        return (
            float(weights[numerator & denominator].sum() / denominator_weight)
            if denominator_weight
            else np.nan
        )

    package_equal_precisions = []
    for class_name in CLASS_NAMES:
        accepted_predicted_class = accepted & (predicted == class_name)
        if not accepted_predicted_class.any():
            package_equal_precisions = []
            break
        package_equal_precisions.append(
            weighted_rate(correct, accepted_predicted_class)
        )
    overall = {
        "rule_id": rule_id,
        "rule_type": rule_type,
        "top_score_threshold": top_score_threshold,
        "margin_threshold": margin_threshold,
        "class_specific_margins": (
            json.dumps(class_specific_margins, sort_keys=True)
            if class_specific_margins is not None
            else None
        ),
        "prediction_events": total,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "coverage": accepted_count / total,
        "rejected_rate": rejected_count / total,
        "accepted_accuracy": accepted_accuracy,
        "accepted_macro_precision": macro_precision,
        "package_equal_coverage": weighted_rate(accepted, np.ones(total, dtype=bool)),
        "package_equal_accepted_accuracy": weighted_rate(correct, accepted),
        "package_equal_accepted_macro_precision": (
            float(np.mean(package_equal_precisions))
            if package_equal_precisions
            else np.nan
        ),
        "accepted_errors": int((accepted & ~correct).sum()),
        "errors_rejected": int((~accepted & ~correct).sum()),
        "error_rejection_rate": safe_fraction(~accepted, ~correct),
        "banking_actual_count": int(banking_actual.sum()),
        "banking_actual_accepted_count": int(bank_accepted.sum()),
        "banking_actual_coverage": safe_fraction(accepted, banking_actual),
        "banking_actual_accepted_accuracy": safe_fraction(correct, bank_accepted),
        "package_equal_banking_actual_coverage": weighted_rate(
            accepted, banking_actual
        ),
        "package_equal_banking_actual_accepted_accuracy": weighted_rate(
            correct, bank_accepted
        ),
        "banking_correct_retained_rate": safe_fraction(accepted & correct, banking_actual),
        "accepted_banking_label_count": int(accepted_predicted_banking.sum()),
        "accepted_banking_label_precision": safe_fraction(
            correct, accepted_predicted_banking
        ),
        "banking_error_rejection_rate": safe_fraction(~accepted, banking_errors),
        "banking_to_adware_count": int(banking_to_adware.sum()),
        "banking_to_adware_rejection_rate": safe_fraction(~accepted, banking_to_adware),
        "banking_to_riskware_count": int(banking_to_riskware.sum()),
        "banking_to_riskware_rejection_rate": safe_fraction(~accepted, banking_to_riskware),
        "banking_to_sms_count": int(banking_to_sms.sum()),
        "banking_to_sms_rejection_rate": safe_fraction(~accepted, banking_to_sms),
    }

    per_class_rows: list[dict[str, object]] = []
    for class_name in CLASS_NAMES:
        actual_class = actual == class_name
        predicted_class = predicted == class_name
        actual_accepted = actual_class & accepted
        predicted_accepted = predicted_class & accepted
        per_class_rows.append(
            {
                "rule_id": rule_id,
                "rule_type": rule_type,
                "top_score_threshold": top_score_threshold,
                "margin_threshold": margin_threshold,
                "class_specific_margins": (
                    json.dumps(class_specific_margins, sort_keys=True)
                    if class_specific_margins is not None
                    else None
                ),
                "class": class_name,
                "actual_count": int(actual_class.sum()),
                "actual_accepted_count": int(actual_accepted.sum()),
                "per_class_coverage": safe_fraction(accepted, actual_class),
                "actual_class_accepted_accuracy": safe_fraction(
                    correct, actual_accepted
                ),
                "correct_retained_rate": safe_fraction(
                    accepted & correct, actual_class
                ),
                "accepted_predicted_count": int(predicted_accepted.sum()),
                "predicted_label_retention": safe_fraction(
                    accepted, predicted_class
                ),
                "accepted_precision": safe_fraction(correct, predicted_accepted),
            }
        )
    return overall, per_class_rows


def candidate_definitions() -> Iterable[
    tuple[str, str, float | None, float | None, dict[str, float] | None]
]:
    yield ("none", "none", None, None, None)
    for top_score_threshold in TOP_SCORE_THRESHOLDS:
        yield (
            f"score_T={top_score_threshold:.2f}",
            "score_only",
            float(top_score_threshold),
            None,
            None,
        )
    for margin_threshold in MARGIN_THRESHOLDS[1:]:
        yield (
            f"margin_M={margin_threshold:.2f}",
            "margin_only",
            None,
            float(margin_threshold),
            None,
        )
    for top_score_threshold in TOP_SCORE_THRESHOLDS:
        for margin_threshold in MARGIN_THRESHOLDS[1:]:
            yield (
                f"and_T={top_score_threshold:.2f}_M={margin_threshold:.2f}",
                "score_and_margin",
                float(top_score_threshold),
                float(margin_threshold),
                None,
            )

    # Small, interpretable sensitivity set rather than a tuned class-specific
    # grid. Thresholds are indexed by the observable predicted top class.
    yield (
        "class_margin_AR=0.70_BS=0.60",
        "class_specific_margin",
        None,
        None,
        {
            "Adware": 0.70,
            "Riskware": 0.70,
            "Banking Malware": 0.60,
            "SMS Malware": 0.60,
        },
    )
    yield (
        "class_margin_AR=0.80_BS=0.70",
        "class_specific_margin",
        None,
        None,
        {
            "Adware": 0.80,
            "Riskware": 0.80,
            "Banking Malware": 0.70,
            "SMS Malware": 0.70,
        },
    )
    yield (
        "class_margin_B=0.80_else=0.70",
        "class_specific_margin",
        None,
        None,
        {
            "Adware": 0.70,
            "Riskware": 0.70,
            "Banking Malware": 0.80,
            "SMS Malware": 0.70,
        },
    )


def evaluate_candidates(
    predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    overall_rows: list[dict[str, object]] = []
    per_class_rows: list[dict[str, object]] = []
    repeat_rows: list[dict[str, object]] = []

    for (
        rule_id,
        rule_type,
        top_threshold,
        margin_threshold,
        class_specific_margins,
    ) in candidate_definitions():
        accepted = rule_mask(
            predictions, top_threshold, margin_threshold, class_specific_margins
        )
        overall, per_class = evaluate_rule(
            predictions,
            accepted,
            rule_id,
            rule_type,
            top_threshold,
            margin_threshold,
            class_specific_margins,
        )
        overall_rows.append(overall)
        per_class_rows.extend(per_class)

        for repeat, repeat_frame in predictions.groupby("repeat", sort=True):
            repeat_accepted = rule_mask(
                repeat_frame,
                top_threshold,
                margin_threshold,
                class_specific_margins,
            )
            repeat_overall, _ = evaluate_rule(
                repeat_frame,
                repeat_accepted,
                rule_id,
                rule_type,
                top_threshold,
                margin_threshold,
                class_specific_margins,
            )
            repeat_rows.append(
                {
                    "rule_id": rule_id,
                    "rule_type": rule_type,
                    "top_score_threshold": top_threshold,
                    "margin_threshold": margin_threshold,
                    "class_specific_margins": (
                        json.dumps(class_specific_margins, sort_keys=True)
                        if class_specific_margins is not None
                        else None
                    ),
                    "repeat": int(repeat),
                    "coverage": repeat_overall["coverage"],
                    "accepted_accuracy": repeat_overall["accepted_accuracy"],
                    "accepted_macro_precision": repeat_overall[
                        "accepted_macro_precision"
                    ],
                    "package_equal_coverage": repeat_overall[
                        "package_equal_coverage"
                    ],
                    "package_equal_accepted_accuracy": repeat_overall[
                        "package_equal_accepted_accuracy"
                    ],
                    "package_equal_accepted_macro_precision": repeat_overall[
                        "package_equal_accepted_macro_precision"
                    ],
                    "rejected_count": repeat_overall["rejected_count"],
                    "banking_actual_coverage": repeat_overall[
                        "banking_actual_coverage"
                    ],
                    "banking_actual_accepted_accuracy": repeat_overall[
                        "banking_actual_accepted_accuracy"
                    ],
                    "package_equal_banking_actual_coverage": repeat_overall[
                        "package_equal_banking_actual_coverage"
                    ],
                    "package_equal_banking_actual_accepted_accuracy": repeat_overall[
                        "package_equal_banking_actual_accepted_accuracy"
                    ],
                    "accepted_banking_label_precision": repeat_overall[
                        "accepted_banking_label_precision"
                    ],
                    "banking_error_rejection_rate": repeat_overall[
                        "banking_error_rejection_rate"
                    ],
                    "banking_to_adware_rejection_rate": repeat_overall[
                        "banking_to_adware_rejection_rate"
                    ],
                    "banking_to_riskware_rejection_rate": repeat_overall[
                        "banking_to_riskware_rejection_rate"
                    ],
                }
            )

    return (
        pd.DataFrame(overall_rows),
        pd.DataFrame(per_class_rows),
        pd.DataFrame(repeat_rows),
    )


def write_outputs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions = load_random_forest_predictions()
    diagnostics = build_diagnostics(predictions)
    candidates, per_class, repeat_metrics = evaluate_candidates(predictions)

    predictions.to_csv(OUTPUT_DIR / "development_prediction_scores.csv", index=False)
    diagnostics[0].to_csv(OUTPUT_DIR / "diagnostic_by_correctness.csv", index=False)
    diagnostics[1].to_csv(OUTPUT_DIR / "diagnostic_by_actual_class.csv", index=False)
    diagnostics[2].to_csv(
        OUTPUT_DIR / "diagnostic_by_class_and_correctness.csv", index=False
    )
    diagnostics[3].to_csv(OUTPUT_DIR / "banking_outcome_diagnostics.csv", index=False)
    diagnostics[4].to_csv(
        OUTPUT_DIR / "banking_outcome_by_repeat.csv", index=False
    )
    candidates.to_csv(OUTPUT_DIR / "candidate_rules_all.csv", index=False)
    per_class.to_csv(OUTPUT_DIR / "candidate_rules_per_class.csv", index=False)
    repeat_metrics.to_csv(OUTPUT_DIR / "candidate_rules_by_repeat.csv", index=False)

    repeat_summary = (
        repeat_metrics.groupby("rule_id", sort=False)[
            [
                "coverage",
                "accepted_accuracy",
                "accepted_macro_precision",
                "package_equal_coverage",
                "package_equal_accepted_accuracy",
                "package_equal_accepted_macro_precision",
                "rejected_count",
                "banking_actual_coverage",
                "banking_actual_accepted_accuracy",
                "package_equal_banking_actual_coverage",
                "package_equal_banking_actual_accepted_accuracy",
                "accepted_banking_label_precision",
                "banking_error_rejection_rate",
                "banking_to_adware_rejection_rate",
                "banking_to_riskware_rejection_rate",
            ]
        ]
        .agg(["mean", "std", "min", "max"])
    )
    repeat_summary.columns = ["_".join(column) for column in repeat_summary.columns]
    repeat_summary.reset_index().to_csv(
        OUTPUT_DIR / "candidate_rules_repeat_summary.csv", index=False
    )

    manifest = {
        "analysis": "four-class Random Forest selective-classification diagnostics",
        "primary_evidence": "saved repeated package-grouped CV out-of-fold predictions",
        "input_path": str(CV_PREDICTIONS.relative_to(ROOT)).replace("\\", "/"),
        "input_sha256": sha256_file(CV_PREDICTIONS),
        "model_filter": MODEL_NAME,
        "class_score_semantics": (
            "raw Random Forest class scores; not calibrated probabilities or confidence"
        ),
        "prediction_events": int(len(predictions)),
        "development_rows_per_repeat": 3_516,
        "repeats": 5,
        "independence_warning": (
            "Each development row appears once in each of five repeats. Pooled rows are "
            "dependent prediction events, not 17,580 independent applications."
        ),
        "threshold_comparison_source": "development/repeated-CV only",
        "supplementary_holdout_used_for_threshold_selection": False,
        "model_retrained_or_tuned": False,
        "model_calibrated": False,
        "fastapi_modified": False,
        "outputs": sorted(
            path.name for path in OUTPUT_DIR.iterdir() if path.is_file()
        ),
    }
    with (OUTPUT_DIR / "analysis_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")

    print(f"Wrote abstention diagnostics to {OUTPUT_DIR}")
    print(f"Random Forest prediction events: {len(predictions):,}")
    print(f"Baseline accuracy: {predictions['correct'].mean():.6f}")
    print(f"Candidate rules evaluated: {len(candidates):,}")


if __name__ == "__main__":
    write_outputs()

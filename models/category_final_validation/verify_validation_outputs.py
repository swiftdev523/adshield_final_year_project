"""Read-only integrity checks for the completed category-validation artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
ARTIFACTS = ROOT / "artifacts"
HISTORICAL = PROJECT_ROOT / "models" / "category_experimental"
CLASSES = ["Adware", "Banking Malware", "SMS Malware", "Riskware"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def group_id(package: str, source_row: int) -> str:
    package = str(package).strip().casefold()
    return package if package else f"__missing_package_row_{int(source_row)}"


def main() -> None:
    completed = json.loads((ARTIFACTS / "COMPLETED.json").read_text(encoding="utf-8"))
    run_manifest = json.loads(
        (ARTIFACTS / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert completed["status"] == "completed"
    assert completed["run_manifest_sha256"] == sha256_file(
        ARTIFACTS / "run_manifest.json"
    )
    assert completed["report_sha256"] == sha256_file(ROOT / "REPORT.md")
    assert run_manifest["historical_artifacts_unchanged"] is True
    assert run_manifest["fresh_holdout_evaluated"] is False
    assert run_manifest["probabilities_approved_for_user_facing_confidence"] is False

    for name, record in run_manifest["historical_artifact_hashes_after"].items():
        assert sha256_file(HISTORICAL / name) == record["sha256"]

    development = pd.read_csv(
        ARTIFACTS / "development_manifest.csv", keep_default_na=False
    )
    assert len(development) == 3_516
    assert not development["package"].astype(str).str.strip().eq("").any()
    assert development.groupby("class_name").size().to_dict() == {
        name: 879 for name in CLASSES
    }
    assert int(development.groupby("normalized_group_id").size().max()) <= 8
    assert development["source_row_index"].is_unique

    historical = pd.read_csv(
        HISTORICAL / "split_manifest.csv", keep_default_na=False
    )
    historical["normalized_group_id"] = [
        group_id(package, row)
        for package, row in zip(
            historical["package"], historical["source_row_index"], strict=True
        )
    ]
    test_groups = set(
        historical.loc[historical["split"] == "test", "normalized_group_id"]
    )
    assert not (set(development["normalized_group_id"]) & test_groups)

    assignments = pd.read_csv(ARTIFACTS / "cv_fold_assignments.csv")
    assert len(assignments) == len(development) * 5
    for repeat, repeat_frame in assignments.groupby("repeat"):
        assert len(repeat_frame) == len(development), repeat
        assert repeat_frame["cohort_position"].is_unique
        assert (
            repeat_frame.groupby("normalized_group_id")["validation_fold"].nunique().max()
            == 1
        )

    cv_predictions = pd.read_csv(ARTIFACTS / "cv_oof_predictions.csv")
    probability_columns = [
        column for column in cv_predictions if column.startswith("raw_probability_")
    ]
    assert len(cv_predictions) == len(development) * 5 * 3
    assert np.allclose(cv_predictions[probability_columns].sum(axis=1), 1.0)
    assert (
        cv_predictions.groupby(["model", "repeat"])["source_row_index"].nunique().min()
        == len(development)
    )

    calibration_predictions = pd.read_csv(
        ARTIFACTS / "calibration_oof_predictions.csv"
    )
    calibration_probability_columns = [
        column for column in calibration_predictions if column.startswith("probability_")
    ]
    assert set(calibration_predictions["method"]) == {"raw", "sigmoid", "isotonic"}
    assert np.allclose(
        calibration_predictions[calibration_probability_columns].sum(axis=1), 1.0
    )
    assert (
        calibration_predictions.groupby("method")["source_row_index"].nunique().min()
        == len(development)
    )

    bundle_path = ARTIFACTS / run_manifest["selected_model_artifact"]
    assert sha256_file(bundle_path) == run_manifest["selected_model_artifact_sha256"]
    bundle = joblib.load(bundle_path)
    assert sklearn.__version__ == "1.6.1"
    assert bundle["scikit_learn_version"] == "1.6.1"
    assert bundle["model_name"] == "Random Forest"
    assert len(bundle["feature_names"]) == 153
    assert bundle["fresh_four_class_holdout_evaluated"] is False
    assert bundle["probabilities_calibrated"] is False
    assert bundle["user_facing_confidence_allowed"] is False
    assert bundle["integrated_with_fastapi"] is False
    assert bundle["binary_detectors_modified"] is False

    holdout = json.loads(
        (ARTIFACTS / "fresh_holdout_status.json").read_text(encoding="utf-8")
    )
    assert holdout["fresh_holdout_created"] is False
    assert holdout["fresh_holdout_evaluated"] is False
    assert holdout["blocking_classes"] == ["Banking Malware", "SMS Malware"]
    assert holdout["fresh_holdout_macro_f1"] is None
    assert holdout["fresh_holdout_confusion_matrix"] is None

    print("All category-validation artifact checks passed.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build deterministic, package-unique candidate pools from an APK audit CSV."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
AUDIT_CSV = OUTPUT_DIR / "apk_audit.csv"
SUMMARY_JSON = OUTPUT_DIR / "unique_candidate_summary.json"
OUTPUTS = {
    "banking": OUTPUT_DIR / "banking_unique_candidates.csv",
    "sms": OUTPUT_DIR / "sms_unique_candidates.csv",
}
FEATURE_PREFIX = "android.permission."
EXPECTED_FEATURE_COUNT = 153
TRUE = "true"
FALSE = "false"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CandidatePoolError(RuntimeError):
    """Raised when the audit CSV does not satisfy the candidate contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_identity(row: dict[str, str]) -> str:
    return row["package"].strip().casefold()


def load_audit() -> tuple[list[str], list[str], list[dict[str, str]]]:
    with AUDIT_CSV.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise CandidatePoolError("audit CSV has no header")
        rows = list(reader)

    required = {
        "sha256",
        "package",
        "normalized_package",
        "category",
        "parse_success",
        "manifest_present",
        "zip_readable",
        "feature_vector_generated",
        "eligible_holdout",
        "historical_package_overlap",
        "duplicate_sha256",
        "cross_category_hash_conflict",
        "cross_category_package_conflict",
        "failure_reason",
        "eligibility_reasons",
        "matched_schema_permission_count",
    }
    missing = sorted(required.difference(fieldnames))
    if missing:
        raise CandidatePoolError(f"audit CSV is missing columns: {missing}")

    features = [name for name in fieldnames if name.startswith(FEATURE_PREFIX)]
    if len(features) != EXPECTED_FEATURE_COUNT:
        raise CandidatePoolError(
            f"expected {EXPECTED_FEATURE_COUNT} permission features, found {len(features)}"
        )
    if fieldnames[-EXPECTED_FEATURE_COUNT:] != features:
        raise CandidatePoolError(
            "the 153 permission features are not a contiguous ordered CSV suffix"
        )
    if len(set(features)) != EXPECTED_FEATURE_COUNT:
        raise CandidatePoolError("permission feature names are not unique")

    return fieldnames, features, rows


def choose_unique_rows(
    rows: Iterable[dict[str, str]], category: str
) -> tuple[list[dict[str, str]], int, dict[str, str]]:
    eligible = [
        row
        for row in rows
        if row["category"] == category and row["eligible_holdout"] == TRUE
    ]
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        identity = package_identity(row)
        if not identity:
            raise CandidatePoolError(
                f"eligible {category} row has a blank normalized package identity"
            )
        groups[identity].append(row)

    selected: list[dict[str, str]] = []
    minimum_sha_by_identity: dict[str, str] = {}
    for identity, group in groups.items():
        retained = min(group, key=lambda row: row["sha256"])
        minimum_sha_by_identity[identity] = retained["sha256"]
        copied = dict(retained)
        copied["normalized_package"] = identity
        selected.append(copied)

    selected.sort(key=lambda row: (row["normalized_package"], row["sha256"]))
    return selected, len(eligible), minimum_sha_by_identity


def validate_pool(
    rows: list[dict[str, str]],
    features: list[str],
    minimum_sha_by_identity: dict[str, str],
    category: str,
) -> dict[str, int | bool]:
    expected_packages = len(minimum_sha_by_identity)
    identities = [package_identity(row) for row in rows]
    hashes = [row["sha256"] for row in rows]
    duplicate_identities = sum(
        count - 1 for count in Counter(identities).values() if count > 1
    )
    duplicate_hashes = sum(count - 1 for count in Counter(hashes).values() if count > 1)
    invalid_sha256_values = sum(
        SHA256_PATTERN.fullmatch(value) is None for value in hashes
    )
    historical_overlaps = sum(
        row["historical_package_overlap"] != FALSE for row in rows
    )
    cross_category_conflicts = sum(
        row["cross_category_package_conflict"] != FALSE for row in rows
    )
    noneligible_rows = sum(row["eligible_holdout"] != TRUE for row in rows)
    wrong_category_rows = sum(row["category"] != category for row in rows)
    incomplete_static_parse_rows = sum(
        row["parse_success"] != TRUE
        or row["manifest_present"] != TRUE
        or row["zip_readable"] != TRUE
        or row["feature_vector_generated"] != TRUE
        for row in rows
    )
    duplicate_sha256_flag_rows = sum(row["duplicate_sha256"] != FALSE for row in rows)
    cross_category_hash_conflict_rows = sum(
        row["cross_category_hash_conflict"] != FALSE for row in rows
    )
    nonblank_failure_or_eligibility_reasons = sum(
        bool(row["failure_reason"]) or bool(row["eligibility_reasons"])
        for row in rows
    )
    normalized_package_mismatches = sum(
        row["normalized_package"] != identity
        for row, identity in zip(rows, identities)
    )
    nonminimum_sha_selections = sum(
        row["sha256"] != minimum_sha_by_identity[identity]
        for row, identity in zip(rows, identities)
    )
    invalid_feature_rows = 0
    feature_sum_mismatch_rows = 0
    for row in rows:
        values = [row[feature] for feature in features]
        if len(values) != EXPECTED_FEATURE_COUNT or any(
            value not in {"0", "1"} for value in values
        ):
            invalid_feature_rows += 1
            continue
        if sum(int(value) for value in values) != int(
            row["matched_schema_permission_count"]
        ):
            feature_sum_mismatch_rows += 1

    checks = {
        "row_count_matches_expected_distinct_packages": len(rows) == expected_packages,
        "zero_duplicate_normalized_packages": duplicate_identities == 0,
        "zero_duplicate_sha256_values": duplicate_hashes == 0,
        "all_sha256_values_are_lowercase_64_hex": invalid_sha256_values == 0,
        "zero_historical_package_overlap": historical_overlaps == 0,
        "zero_cross_category_package_conflicts": cross_category_conflicts == 0,
        "zero_cross_category_hash_conflicts": cross_category_hash_conflict_rows == 0,
        "zero_duplicate_sha256_audit_flags": duplicate_sha256_flag_rows == 0,
        "all_rows_eligible": noneligible_rows == 0,
        "all_rows_match_output_category": wrong_category_rows == 0,
        "all_static_parse_evidence_successful": incomplete_static_parse_rows == 0,
        "failure_and_eligibility_reasons_are_blank": (
            nonblank_failure_or_eligibility_reasons == 0
        ),
        "normalized_package_uses_strip_casefold": normalized_package_mismatches == 0,
        "lexicographically_smallest_sha256_retained": nonminimum_sha_selections == 0,
        "all_rows_have_153_ordered_binary_features": invalid_feature_rows == 0,
        "feature_sums_match_matched_schema_permission_count": (
            feature_sum_mismatch_rows == 0
        ),
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise CandidatePoolError(f"candidate pool validation failed: {failed}")

    return {
        "candidate_rows": len(rows),
        "distinct_normalized_packages": len(set(identities)),
        "duplicate_normalized_package_values": duplicate_identities,
        "duplicate_sha256_values": duplicate_hashes,
        "invalid_sha256_values": invalid_sha256_values,
        "historical_package_overlap_rows": historical_overlaps,
        "cross_category_package_conflict_rows": cross_category_conflicts,
        "cross_category_hash_conflict_rows": cross_category_hash_conflict_rows,
        "duplicate_sha256_flag_rows": duplicate_sha256_flag_rows,
        "nonminimum_sha256_selections": nonminimum_sha_selections,
        "invalid_feature_rows": invalid_feature_rows,
        "feature_sum_mismatch_rows": feature_sum_mismatch_rows,
        **checks,
    }


def write_csv_atomic(
    path: Path, fieldnames: list[str], rows: list[dict[str, str]]
) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
                extrasaction="raise",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    fieldnames, features, audit_rows = load_audit()
    category_rows: dict[str, list[dict[str, str]]] = {}
    input_eligible_counts: dict[str, int] = {}
    minimum_shas: dict[str, dict[str, str]] = {}

    for category in OUTPUTS:
        selected, eligible_count, minimum_sha_by_identity = choose_unique_rows(
            audit_rows, category
        )
        category_rows[category] = selected
        input_eligible_counts[category] = eligible_count
        minimum_shas[category] = minimum_sha_by_identity

    package_sets = {
        category: {row["normalized_package"] for row in rows}
        for category, rows in category_rows.items()
    }
    cross_category_package_intersection = sorted(
        package_sets["banking"].intersection(package_sets["sms"])
    )
    all_hashes = [
        row["sha256"] for rows in category_rows.values() for row in rows
    ]
    cross_output_duplicate_hashes = sum(
        count - 1 for count in Counter(all_hashes).values() if count > 1
    )
    if cross_category_package_intersection:
        raise CandidatePoolError(
            "case-folded package identities overlap across category outputs"
        )
    if cross_output_duplicate_hashes:
        raise CandidatePoolError("SHA-256 values are duplicated across category outputs")

    for category, path in OUTPUTS.items():
        write_csv_atomic(path, fieldnames, category_rows[category])

    category_summary: dict[str, object] = {}
    for category, path in OUTPUTS.items():
        expected_packages = len(minimum_shas[category])
        validation = validate_pool(
            category_rows[category], features, minimum_shas[category], category
        )
        category_summary[category] = {
            "audit_eligible_input_rows": input_eligible_counts[category],
            "rows_removed_by_package_deduplication": (
                input_eligible_counts[category] - len(category_rows[category])
            ),
            "expected_distinct_eligible_packages": expected_packages,
            "output": path.relative_to(PROJECT_ROOT).as_posix(),
            "output_sha256": sha256_file(path),
            **validation,
        }

    summary = {
        "audit_source": AUDIT_CSV.relative_to(PROJECT_ROOT).as_posix(),
        "audit_source_sha256": sha256_file(AUDIT_CSV),
        "categories": category_summary,
        "feature_contract": {
            "count": len(features),
            "ordered_columns": features,
            "preserved_as_final_csv_columns": True,
        },
        "global_verification": {
            "cross_category_casefolded_package_intersection_count": len(
                cross_category_package_intersection
            ),
            "duplicate_sha256_values_across_outputs": cross_output_duplicate_hashes,
        },
        "package_identity_normalization": "package.strip().casefold()",
        "row_selection": (
            "one eligible_holdout row per normalized package; retain the "
            "lexicographically smallest SHA-256"
        ),
        "safety": {
            "audit_csv_only": True,
            "raw_apks_accessed": False,
            "category_model_loaded": False,
            "category_predictions_generated": False,
            "final_holdout_selected": False,
        },
    }
    write_json_atomic(SUMMARY_JSON, summary)

    for category in OUTPUTS:
        details = category_summary[category]
        print(
            f"{category}: eligible_rows={details['audit_eligible_input_rows']} "
            f"unique_candidates={details['candidate_rows']}"
        )
    print(f"wrote: {SUMMARY_JSON.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

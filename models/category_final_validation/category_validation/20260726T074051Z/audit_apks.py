#!/usr/bin/env python3
"""Manifest-only, read-only audit for Banking and SMS APK collections.

Safety boundary
---------------
This program never installs or executes APKs, never invokes Android tooling or
an emulator, never extracts archive members to disk, and never reads DEX,
resources, native libraries, or model artifacts. It hashes each selected file,
reads the ZIP central directory, and decompresses only the exact root member
``AndroidManifest.xml`` into memory for static metadata parsing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import logging
import multiprocessing
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# This is the supplied project's pure canonicalization function. Importing this
# module does not load the malware-category model or its feature artifact.
from permission_mapping import normalize_permission  # noqa: E402


EXPECTED_FEATURE_COUNT = 153
ANDROID_NS = "http://schemas.android.com/apk/res/android"
ANDROID_NAME = f"{{{ANDROID_NS}}}name"
PERMISSION_TAGS = {
    "uses-permission",
    "uses-permission-sdk-23",
    "uses-permission-sdk-m",
}
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_PACKAGE_CHARS = 4096
MAX_PERMISSION_CHARS = 4096
MAX_PERMISSION_ELEMENTS = 10_000
MAX_PERMISSION_PAYLOAD_CHARS = 1_000_000
HASH_CHUNK_BYTES = 1024 * 1024
DEFAULT_PARSE_TIMEOUT_SECONDS = 15.0
LEGACY_SMS_NAME = re.compile(r"^[0-9a-fA-F]{64}\.[0-9a-fA-F]{32}$")


BASE_FIELDS = [
    "sha256",
    "package",
    "normalized_package",
    "category",
    "parse_success",
    "manifest_present",
    "permission_count",
    "matched_schema_permission_count",
    "historical_package_overlap",
    "duplicate_sha256",
    "duplicate_package",
    "cross_category_hash_conflict",
    "cross_category_package_conflict",
    "eligible_holdout",
    "failure_reason",
    "source_path",
    "zip_readable",
    "manifest_format",
    "feature_vector_generated",
    "unmatched_permission_count",
    "declared_permissions_json",
    "normalized_permission_keys_json",
    "eligibility_reasons",
]


class AuditConfigurationError(RuntimeError):
    """Raised when a trusted reference or required input is invalid."""


class ManifestAuditError(RuntimeError):
    """Raised for one-file ZIP or manifest failures."""


@dataclass(frozen=True)
class SchemaContract:
    path: Path
    features: tuple[str, ...]
    normalized_keys: tuple[str, ...]
    key_to_index: dict[str, int]


@dataclass(frozen=True)
class HistoricalPackages:
    path: Path
    column: str
    packages: frozenset[str]
    row_count: int
    nonblank_count: int
    split_counts: dict[str, int]


@dataclass(frozen=True)
class InputRoot:
    category: str
    path: Path
    requested_path: Path
    used_legacy_fallback: bool


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit APK ZIPs using only static AndroidManifest.xml metadata."
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=None,
        help="process at most N deterministically selected files per category",
    )
    parser.add_argument(
        "--banking-dir",
        type=Path,
        default=None,
        help="override the default raw/banking input directory",
    )
    parser.add_argument(
        "--sms-dir",
        type=Path,
        default=None,
        help="override the default raw/sms input directory",
    )
    parser.add_argument(
        "--permission-features",
        type=Path,
        default=None,
        help="override reference/permission_features.json",
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=None,
        help="override reference/split_manifest.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="directory for the four audit outputs",
    )
    parser.add_argument(
        "--parse-timeout",
        type=positive_float,
        default=DEFAULT_PARSE_TIMEOUT_SECONDS,
        help="maximum seconds allowed for one isolated manifest parse",
    )
    return parser.parse_args(argv)


def resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def resolve_reference(explicit: Path | None, required_relative: Path) -> Path:
    if explicit is not None:
        candidate = resolve_project_path(explicit)
        if not candidate.is_file():
            raise AuditConfigurationError(f"reference file not found: {candidate}")
        return candidate

    required = PROJECT_ROOT / required_relative
    if required.is_file():
        return required

    # The supplied files may be placed at the project root. Supporting this
    # layout does not move or rewrite the trusted references.
    root_fallback = PROJECT_ROOT / required_relative.name
    if root_fallback.is_file():
        return root_fallback
    raise AuditConfigurationError(
        f"reference file not found at {required} or {root_fallback}"
    )


def normalize_package(package: str | None) -> str:
    """Match split_manifest.csv's existing package convention.

    The supplied manifest's ``package`` column is already whitespace-stripped
    and preserves Java package-name case. The same strip-only rule is applied
    to newly parsed packages; case is deliberately not folded.
    """

    return (package or "").strip()


def load_schema(path: Path) -> SchemaContract:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditConfigurationError(f"cannot read permission schema: {exc}") from exc

    if not isinstance(payload, list):
        raise AuditConfigurationError("permission_features.json must be a JSON array")
    if len(payload) != EXPECTED_FEATURE_COUNT:
        raise AuditConfigurationError(
            f"permission schema has {len(payload)} entries; expected {EXPECTED_FEATURE_COUNT}"
        )
    if any(not isinstance(item, str) or not item for item in payload):
        raise AuditConfigurationError("every permission schema entry must be a nonblank string")
    if len(set(payload)) != EXPECTED_FEATURE_COUNT:
        raise AuditConfigurationError("permission schema contains duplicate feature names")

    normalized_keys = tuple(normalize_permission(item) for item in payload)
    if any(not key for key in normalized_keys):
        raise AuditConfigurationError("permission schema produced a blank normalized key")
    if len(set(normalized_keys)) != EXPECTED_FEATURE_COUNT:
        raise AuditConfigurationError(
            "permission schema has collisions under the supplied normalization rule"
        )

    features = tuple(payload)
    return SchemaContract(
        path=path,
        features=features,
        normalized_keys=normalized_keys,
        key_to_index={key: index for index, key in enumerate(normalized_keys)},
    )


def load_historical_packages(path: Path) -> HistoricalPackages:
    packages: set[str] = set()
    row_count = 0
    nonblank_count = 0
    split_counts: Counter[str] = Counter()
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "package" not in reader.fieldnames:
                raise AuditConfigurationError(
                    "split_manifest.csv must contain the normalized 'package' column"
                )
            for row in reader:
                row_count += 1
                package = normalize_package(row.get("package"))
                if package:
                    nonblank_count += 1
                    packages.add(package)
                split_counts[(row.get("split") or "").strip()] += 1
    except AuditConfigurationError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise AuditConfigurationError(f"cannot read split manifest: {exc}") from exc

    return HistoricalPackages(
        path=path,
        column="package",
        packages=frozenset(packages),
        row_count=row_count,
        nonblank_count=nonblank_count,
        split_counts=dict(sorted(split_counts.items())),
    )


def resolve_input_root(
    category: str,
    explicit: Path | None,
    required_relative: Path,
    legacy_relative: Path,
) -> InputRoot:
    requested = PROJECT_ROOT / required_relative
    if explicit is not None:
        selected = resolve_project_path(explicit)
        used_fallback = selected != requested
    elif requested.is_dir():
        selected = requested
        used_fallback = False
    else:
        selected = PROJECT_ROOT / legacy_relative
        used_fallback = True

    if not selected.is_dir():
        raise AuditConfigurationError(f"{category} input directory not found: {selected}")
    if selected.is_symlink():
        raise AuditConfigurationError(f"refusing symlinked input root: {selected}")
    return InputRoot(category, selected, requested, used_fallback)


def is_apk_candidate(category: str, path: Path) -> bool:
    if path.name.casefold().endswith(".apk"):
        return True
    return category == "sms" and LEGACY_SMS_NAME.fullmatch(path.name) is not None


def discover_candidates(root: InputRoot) -> list[Path]:
    candidates: list[Path] = []
    for current, directory_names, file_names in os.walk(root.path, followlinks=False):
        current_path = Path(current)
        directory_names[:] = sorted(
            (
                name
                for name in directory_names
                if not (current_path / name).is_symlink()
            ),
            key=lambda value: (value.casefold(), value),
        )
        for name in sorted(file_names, key=lambda value: (value.casefold(), value)):
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                continue
            if is_apk_candidate(root.category, path):
                candidates.append(path)

    return sorted(
        candidates,
        key=lambda path: (
            path.relative_to(root.path).as_posix().casefold(),
            path.relative_to(root.path).as_posix(),
        ),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest_only(path: Path) -> tuple[bytes, bool, bool]:
    """Return exact AndroidManifest.xml bytes plus ZIP/manifest flags.

    Opening the ZIP reads only its central directory. This function never uses
    ``testzip``, ``extract``, or ``extractall`` and reads no other member.
    """

    zip_readable = False
    manifest_present = False
    try:
        with zipfile.ZipFile(path, mode="r", allowZip64=True) as archive:
            infos = archive.infolist()
            zip_readable = True
            manifest_infos = [info for info in infos if info.filename == "AndroidManifest.xml"]
            manifest_present = bool(manifest_infos)
            if not manifest_infos:
                raise ManifestAuditError("AndroidManifest.xml is missing")
            if len(manifest_infos) != 1:
                raise ManifestAuditError("multiple root AndroidManifest.xml entries")

            info = manifest_infos[0]
            if info.is_dir():
                raise ManifestAuditError("AndroidManifest.xml entry is a directory")
            if info.flag_bits & 0x1:
                raise ManifestAuditError("AndroidManifest.xml entry is encrypted")
            if info.file_size > MAX_MANIFEST_BYTES:
                raise ManifestAuditError(
                    f"AndroidManifest.xml exceeds {MAX_MANIFEST_BYTES} byte safety cap"
                )

            with archive.open(info, mode="r") as member:
                data = member.read(MAX_MANIFEST_BYTES + 1)
            if len(data) > MAX_MANIFEST_BYTES:
                raise ManifestAuditError(
                    f"AndroidManifest.xml exceeds {MAX_MANIFEST_BYTES} byte safety cap"
                )
            if len(data) != info.file_size:
                raise ManifestAuditError("AndroidManifest.xml size mismatch")
            if not data:
                raise ManifestAuditError("AndroidManifest.xml is empty")
            return data, zip_readable, manifest_present
    except ManifestAuditError as exc:
        setattr(exc, "zip_readable", zip_readable)
        setattr(exc, "manifest_present", manifest_present)
        raise
    except Exception as exc:
        wrapped = ManifestAuditError(f"unreadable APK/ZIP: {clean_error(exc)}")
        setattr(wrapped, "zip_readable", zip_readable)
        setattr(wrapped, "manifest_present", manifest_present)
        raise wrapped from exc


def _local_name(tag: Any) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _apply_worker_limits(timeout_seconds: float) -> None:
    try:
        import resource

        cpu_seconds = max(1, int(timeout_seconds) + 1)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    except (ImportError, OSError, ValueError):
        # The parent-enforced wall timeout remains active if a platform does
        # not provide Unix resource limits.
        pass


def _manifest_worker(
    manifest_bytes: bytes,
    timeout_seconds: float,
    connection: Any,
) -> None:
    """Decode one in-memory manifest in an isolated, resource-limited child."""

    try:
        logging.disable(logging.CRITICAL)
        _apply_worker_limits(timeout_seconds)
        from lxml import etree

        if manifest_bytes.lstrip().startswith(b"<"):
            parser = etree.XMLParser(
                resolve_entities=False,
                load_dtd=False,
                no_network=True,
                recover=False,
                huge_tree=False,
            )
            root = etree.fromstring(manifest_bytes, parser=parser)
            manifest_format = "text_xml"
        else:
            from axml.axml import AXMLPrinter

            printer = AXMLPrinter(manifest_bytes)
            if not printer.is_valid():
                raise ValueError("invalid binary AndroidManifest.xml")
            root = printer.get_xml_obj()
            manifest_format = "binary_axml"

        if root is None or _local_name(root.tag) != "manifest":
            raise ValueError("decoded XML has no manifest root")

        package = (root.attrib.get("package") or "").strip()
        if len(package) > MAX_PACKAGE_CHARS:
            raise ValueError("manifest package exceeds safety length limit")

        permissions: list[str] = []
        permission_element_count = 0
        permission_payload_chars = 0
        for child in root:
            if _local_name(child.tag) not in PERMISSION_TAGS:
                continue
            permission_element_count += 1
            if permission_element_count > MAX_PERMISSION_ELEMENTS:
                raise ValueError("too many declared permission elements")
            value = child.attrib.get(ANDROID_NAME)
            if value is None:
                continue
            if len(value) > MAX_PERMISSION_CHARS:
                raise ValueError("declared permission exceeds safety length limit")
            if value.strip():
                permission_payload_chars += len(value)
                if permission_payload_chars > MAX_PERMISSION_PAYLOAD_CHARS:
                    raise ValueError("declared permission payload exceeds safety limit")
                permissions.append(value)

        connection.send(
            {
                "ok": True,
                "package": package,
                "permissions": sorted(set(permissions)),
                "manifest_format": manifest_format,
            }
        )
    except BaseException as exc:  # child must report malformed-input failures
        try:
            connection.send({"ok": False, "error": clean_error(exc)})
        except BaseException:
            pass
    finally:
        connection.close()


def parse_manifest_isolated(
    manifest_bytes: bytes,
    timeout_seconds: float,
) -> tuple[str, list[str], str]:
    context = multiprocessing.get_context("fork")
    receive_connection, send_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_manifest_worker,
        args=(manifest_bytes, timeout_seconds, send_connection),
        daemon=True,
    )
    try:
        process.start()
    except Exception:
        receive_connection.close()
        send_connection.close()
        raise
    send_connection.close()

    payload: dict[str, Any] | None = None
    timed_out = False
    try:
        if receive_connection.poll(timeout_seconds):
            try:
                payload = receive_connection.recv()
            except EOFError:
                payload = None
        else:
            timed_out = True
    finally:
        receive_connection.close()

    if timed_out and process.is_alive():
        process.terminate()
    process.join(timeout=1.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=1.0)
    if process.is_alive() and hasattr(process, "kill"):
        process.kill()
        process.join(timeout=1.0)

    if timed_out:
        raise ManifestAuditError(
            f"manifest parser timed out after {timeout_seconds:g} seconds"
        )
    if payload is None:
        raise ManifestAuditError(f"manifest parser exited without a result ({process.exitcode})")
    if not payload.get("ok"):
        raise ManifestAuditError(f"manifest parser failure: {payload.get('error', 'unknown error')}")
    return (
        str(payload.get("package") or ""),
        list(payload.get("permissions") or []),
        str(payload.get("manifest_format") or ""),
    )


def clean_error(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    text = " ".join(text.replace("\x00", "").split())
    return text[:500]


def console_text(value: Any) -> str:
    """Render untrusted metadata without emitting terminal control bytes."""

    return ascii(str(value))


def empty_row(category: str, source_path: str, feature_names: Sequence[str]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "sha256": "",
        "package": "",
        "normalized_package": "",
        "category": category,
        "parse_success": False,
        "manifest_present": False,
        "permission_count": None,
        "matched_schema_permission_count": None,
        "historical_package_overlap": False,
        "duplicate_sha256": False,
        "duplicate_package": False,
        "cross_category_hash_conflict": False,
        "cross_category_package_conflict": False,
        "eligible_holdout": False,
        "failure_reason": "",
        "source_path": source_path,
        "zip_readable": False,
        "manifest_format": "",
        "feature_vector_generated": False,
        "unmatched_permission_count": None,
        "declared_permissions_json": "",
        "normalized_permission_keys_json": "",
        "eligibility_reasons": "",
    }
    row.update({feature: None for feature in feature_names})
    return row


def process_one(
    path: Path,
    root: InputRoot,
    schema: SchemaContract,
    historical: HistoricalPackages,
    timeout_seconds: float,
) -> dict[str, Any]:
    source_path = (Path(root.path.name) / path.relative_to(root.path)).as_posix()
    row = empty_row(root.category, source_path, schema.features)

    try:
        row["sha256"] = sha256_file(path)
    except OSError as exc:
        row["failure_reason"] = f"unreadable file: {clean_error(exc)}"
        return row

    try:
        manifest_bytes, zip_readable, manifest_present = read_manifest_only(path)
        row["zip_readable"] = zip_readable
        row["manifest_present"] = manifest_present
    except ManifestAuditError as exc:
        row["zip_readable"] = bool(getattr(exc, "zip_readable", False))
        row["manifest_present"] = bool(getattr(exc, "manifest_present", False))
        row["failure_reason"] = str(exc)
        return row

    try:
        package, raw_permissions, manifest_format = parse_manifest_isolated(
            manifest_bytes, timeout_seconds
        )
        normalized_keys = sorted(
            {normalize_permission(permission) for permission in raw_permissions}
            - {""}
        )
        vector = [0] * EXPECTED_FEATURE_COUNT
        for key in normalized_keys:
            index = schema.key_to_index.get(key)
            if index is not None:
                vector[index] = 1
        if len(vector) != EXPECTED_FEATURE_COUNT:
            raise ManifestAuditError("internal feature-vector length mismatch")

        normalized_package = normalize_package(package)
        row.update(
            {
                "package": package,
                "normalized_package": normalized_package,
                "parse_success": True,
                "manifest_format": manifest_format,
                "permission_count": len(raw_permissions),
                "matched_schema_permission_count": sum(vector),
                "historical_package_overlap": (
                    bool(normalized_package)
                    and normalized_package in historical.packages
                ),
                "feature_vector_generated": True,
                "unmatched_permission_count": sum(
                    1 for key in normalized_keys if key not in schema.key_to_index
                ),
                "declared_permissions_json": json.dumps(
                    raw_permissions, ensure_ascii=True, separators=(",", ":")
                ),
                "normalized_permission_keys_json": json.dumps(
                    normalized_keys, ensure_ascii=True, separators=(",", ":")
                ),
            }
        )
        row.update(dict(zip(schema.features, vector, strict=True)))
    except Exception as exc:
        row["failure_reason"] = clean_error(exc)
    return row


def add_duplicate_and_eligibility_flags(rows: list[dict[str, Any]]) -> None:
    hash_counts = Counter(row["sha256"] for row in rows if row["sha256"])
    package_counts = Counter(
        row["normalized_package"] for row in rows if row["normalized_package"]
    )
    hash_categories: dict[str, set[str]] = defaultdict(set)
    package_categories: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["sha256"]:
            hash_categories[row["sha256"]].add(row["category"])
        if row["normalized_package"]:
            package_categories[row["normalized_package"]].add(row["category"])

    for row in rows:
        sha256 = row["sha256"]
        package = row["normalized_package"]
        row["duplicate_sha256"] = bool(sha256 and hash_counts[sha256] > 1)
        row["duplicate_package"] = bool(package and package_counts[package] > 1)
        row["cross_category_hash_conflict"] = bool(
            sha256 and len(hash_categories[sha256]) > 1
        )
        row["cross_category_package_conflict"] = bool(
            package and len(package_categories[package]) > 1
        )

        reasons: list[str] = []
        if not row["parse_success"]:
            reasons.append("parse_failed")
        if not package:
            reasons.append("blank_package")
        if not sha256:
            reasons.append("missing_sha256")
        elif row["duplicate_sha256"]:
            reasons.append("duplicate_sha256")
        if row["historical_package_overlap"]:
            reasons.append("historical_package_overlap")
        if row["cross_category_hash_conflict"]:
            reasons.append("cross_category_hash_conflict")
        if row["cross_category_package_conflict"]:
            reasons.append("cross_category_package_conflict")
        if not row["feature_vector_generated"]:
            reasons.append("feature_vector_not_generated")

        row["eligibility_reasons"] = ";".join(reasons)
        row["eligible_holdout"] = not reasons


def safe_csv_text(value: str) -> str:
    value = "".join(
        character
        if ord(character) >= 32 and ord(character) != 127
        else f"\\u{ord(character):04x}"
        for character in value
    )
    # Prevent spreadsheet formula execution if malformed manifest metadata is
    # opened interactively in Excel/LibreOffice. Valid package/permission names
    # are unaffected.
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return safe_csv_text(value)
    return value


def write_csv_atomic(
    path: Path,
    rows: Iterable[dict[str, Any]],
    fieldnames: Sequence[str],
) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            for row in rows:
                writer.writerow({name: csv_value(row.get(name)) for name in fieldnames})
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def relative_display(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def is_same_or_descendant(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def build_summary(
    rows: list[dict[str, Any]],
    roots: Sequence[InputRoot],
    selected_counts: dict[str, int],
    discovered_counts: dict[str, int],
    schema: SchemaContract,
    historical: HistoricalPackages,
    limit: int | None,
    parser_version: str,
) -> dict[str, Any]:
    category_counts: dict[str, dict[str, int]] = {}
    for root in roots:
        category_rows = [row for row in rows if row["category"] == root.category]
        category_counts[root.category] = {
            "discovered": discovered_counts[root.category],
            "selected": selected_counts[root.category],
            "parse_success": sum(bool(row["parse_success"]) for row in category_rows),
            "parse_failed": sum(not bool(row["parse_success"]) for row in category_rows),
            "eligible_holdout": sum(bool(row["eligible_holdout"]) for row in category_rows),
        }

    return {
        "audit_complete": limit is None,
        "category_counts": category_counts,
        "cross_category_hash_conflict_rows": sum(
            bool(row["cross_category_hash_conflict"]) for row in rows
        ),
        "cross_category_package_conflict_rows": sum(
            bool(row["cross_category_package_conflict"]) for row in rows
        ),
        "duplicate_scope": "full_discovered_collection" if limit is None else "processed_batch",
        "duplicate_sha256_rows": sum(bool(row["duplicate_sha256"]) for row in rows),
        "duplicate_package_rows": sum(bool(row["duplicate_package"]) for row in rows),
        "eligible_holdout_rows": sum(bool(row["eligible_holdout"]) for row in rows),
        "failed_rows": sum(not bool(row["parse_success"]) for row in rows),
        "feature_contract": {
            "count": len(schema.features),
            "normalization": "permission.strip().rsplit('.', 1)[-1].upper()",
            "path": relative_display(schema.path),
            "sha256": sha256_file(schema.path),
        },
        "historical_packages": {
            "column": historical.column,
            "distinct_nonblank_packages": len(historical.packages),
            "nonblank_rows": historical.nonblank_count,
            "normalization": "strip whitespace; preserve case",
            "path": relative_display(historical.path),
            "rows": historical.row_count,
            "sha256": sha256_file(historical.path),
            "split_counts": historical.split_counts,
        },
        "input_roots": {
            root.category: {
                "actual": relative_display(root.path),
                "requested": relative_display(root.requested_path),
                "used_legacy_fallback": root.used_legacy_fallback,
            }
            for root in roots
        },
        "limit_per_category": limit,
        "manifest_parser": {"package": "axml", "version": parser_version},
        "outputs": [
            "apk_audit.csv",
            "eligible_holdout_candidates.csv",
            "failed_apks.csv",
            "audit_summary.json",
        ],
        "package_duplicate_normalization": "strip whitespace; preserve case",
        "parser_failure_isolation": {
            "max_manifest_bytes": MAX_MANIFEST_BYTES,
            "per_manifest_child_process": True,
        },
        "safety": {
            "apk_code_executed": False,
            "apk_installed": False,
            "apk_modified": False,
            "android_runtime_or_emulator_invoked": False,
            "archive_members_extracted_to_disk": False,
            "category_model_loaded": False,
            "category_predictions_generated": False,
            "csv_formula_injection_escaped": True,
            "parsed_archive_members": ["AndroidManifest.xml"],
        },
        "successful_rows": sum(bool(row["parse_success"]) for row in rows),
        "total_rows": len(rows),
    }


def ensure_parser_dependency() -> str:
    try:
        version = importlib.metadata.version("axml")
        from axml.axml import AXMLPrinter  # noqa: F401
    except (importlib.metadata.PackageNotFoundError, ImportError) as exc:
        raise AuditConfigurationError(
            "missing manifest parser; run: .venv-audit/bin/python -m pip install axml==0.0.2"
        ) from exc
    return version


def run(args: argparse.Namespace) -> int:
    schema_path = resolve_reference(
        args.permission_features, Path("reference/permission_features.json")
    )
    split_path = resolve_reference(args.split_manifest, Path("reference/split_manifest.csv"))

    print(f"[setup] loading 153-feature contract: {relative_display(schema_path)}", flush=True)
    schema = load_schema(schema_path)
    print(f"[setup] loading historical packages: {relative_display(split_path)}", flush=True)
    historical = load_historical_packages(split_path)
    parser_version = ensure_parser_dependency()

    roots = [
        resolve_input_root(
            "banking", args.banking_dir, Path("raw/banking"), Path("Banking")
        ),
        resolve_input_root("sms", args.sms_dir, Path("raw/sms"), Path("SMS")),
    ]

    all_candidates = {root.category: discover_candidates(root) for root in roots}
    selected = {
        category: (paths[: args.limit] if args.limit is not None else paths)
        for category, paths in all_candidates.items()
    }
    for root in roots:
        print(
            f"[setup] {root.category}: discovered={len(all_candidates[root.category])} "
            f"selected={len(selected[root.category])} root={relative_display(root.path)}",
            flush=True,
        )

    if any(not selected[root.category] for root in roots):
        missing = [root.category for root in roots if not selected[root.category]]
        raise AuditConfigurationError(
            f"no APK candidates selected for category/categories: {', '.join(missing)}"
        )

    output_dir = resolve_project_path(args.output_dir)
    if is_same_or_descendant(output_dir, PROJECT_ROOT / "raw"):
        raise AuditConfigurationError(
            f"output directory must not be inside input-only raw/: {output_dir}"
        )
    for root in roots:
        if is_same_or_descendant(output_dir, root.path):
            raise AuditConfigurationError(
                f"output directory must not be inside input-only {root.category} root: "
                f"{output_dir}"
            )

    rows: list[dict[str, Any]] = []
    for root in roots:
        paths = selected[root.category]
        for index, path in enumerate(paths, start=1):
            relative = path.relative_to(root.path).as_posix()
            print(
                f"[{root.category} {index:04d}/{len(paths):04d}] "
                f"{console_text(relative)}",
                flush=True,
            )
            try:
                row = process_one(path, root, schema, historical, args.parse_timeout)
            except Exception as exc:
                source_path = (Path(root.path.name) / path.relative_to(root.path)).as_posix()
                row = empty_row(root.category, source_path, schema.features)
                try:
                    row["sha256"] = sha256_file(path)
                except OSError:
                    pass
                row["failure_reason"] = f"unexpected audit failure: {clean_error(exc)}"
            rows.append(row)
            if row["parse_success"]:
                print(
                    f"  ok package={console_text(row['package'] or '<blank>')} "
                    f"permissions={row['permission_count']} matched={row['matched_schema_permission_count']}",
                    flush=True,
                )
            else:
                print(f"  failed {console_text(row['failure_reason'])}", flush=True)

    add_duplicate_and_eligibility_flags(rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = BASE_FIELDS + list(schema.features)
    failed_rows = [row for row in rows if not row["parse_success"]]
    eligible_rows = [row for row in rows if row["eligible_holdout"]]

    write_csv_atomic(output_dir / "apk_audit.csv", rows, fieldnames)
    write_csv_atomic(
        output_dir / "eligible_holdout_candidates.csv", eligible_rows, fieldnames
    )
    write_csv_atomic(output_dir / "failed_apks.csv", failed_rows, fieldnames)
    summary = build_summary(
        rows=rows,
        roots=roots,
        selected_counts={key: len(value) for key, value in selected.items()},
        discovered_counts={key: len(value) for key, value in all_candidates.items()},
        schema=schema,
        historical=historical,
        limit=args.limit,
        parser_version=parser_version,
    )
    write_json_atomic(output_dir / "audit_summary.json", summary)

    print(
        f"[done] rows={len(rows)} success={summary['successful_rows']} "
        f"failed={summary['failed_rows']} eligible={summary['eligible_holdout_rows']}",
        flush=True,
    )
    print(f"[done] outputs: {relative_display(output_dir)}", flush=True)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except AuditConfigurationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

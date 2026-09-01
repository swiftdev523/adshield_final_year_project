"""APK Permission Extraction module (APK Analysis Mode).

Pipeline implemented here
-------------------------
1. Parse an uploaded ``.apk`` and read its ``AndroidManifest.xml``.
2. Extract the declared ``android.permission.*`` constants.
3. Translate each permission to the dataset's feature label and build a 0/1
   feature vector aligned to the 151 training columns.
4. Return the permission list, dangerous-permission count and safe-permission
   count (plus the ready-to-score feature vector).

This module deliberately does NOT load or run the ML model. Its output is the
input that a later scoring layer will consume.

CLI
---
    python -m backend.apk_analysis.permission_extractor path/to/app.apk
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .feature_schema import load_permission_feature_names
from .permission_mapping import map_permission

# AndroidManifest.xml inside an APK is *binary* XML (AXML), not plain text, so a
# dedicated parser is required. ``pyaxmlparser`` is a lightweight library built
# for exactly this. It is imported lazily so the rest of the module (mapping,
# vector building) is usable and testable even when the parser is absent.
try:
    from pyaxmlparser import APK as _APK  # type: ignore

    _PARSER_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    _APK = None
    _PARSER_AVAILABLE = False


@dataclass
class ExtractionResult:
    """Structured result of analysing a single APK."""

    apk_path: str
    package: str | None
    raw_permissions: list[str]               # android.permission.* from manifest
    mapped_features: dict[str, int]          # matched dataset labels -> 1
    feature_vector: dict[str, int]           # all 151 training columns -> 0/1
    dangerous_permission_count: int
    safe_permission_count: int
    unmapped_permissions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def extract_permissions(apk_path: str | Path) -> list[str]:
    """Read an APK and return its declared permission constants.

    Raises:
        RuntimeError: if the APK parser dependency is not installed.
        FileNotFoundError: if ``apk_path`` does not exist.
    """
    apk_path = Path(apk_path)
    if not apk_path.exists():
        raise FileNotFoundError(f"APK not found: {apk_path}")
    if not _PARSER_AVAILABLE:
        raise RuntimeError(
            "pyaxmlparser is not installed. Install backend requirements:\n"
            "    pip install -r backend/requirements.txt"
        )
    apk = _APK(str(apk_path))
    # ``get_permissions`` returns the full list of <uses-permission> values.
    return sorted(set(apk.get_permissions() or []))


def build_feature_vector(permissions: list[str]) -> tuple[dict[str, int], dict[str, int], list[str]]:
    """Convert raw permissions into the model's training feature format.

    Returns a tuple of:
        feature_vector   : every training permission column -> 0/1
        mapped_features  : only the columns this APK activated -> 1
        unmapped         : raw permissions with no dataset equivalent
    """
    canonical = load_permission_feature_names()
    # Start every known training column at 0 so the vector shape is stable.
    feature_vector: dict[str, int] = {col: 0 for col in canonical}

    mapped_features: dict[str, int] = {}
    unmapped: list[str] = []

    for perm in permissions:
        label = map_permission(perm)
        if label is None:
            unmapped.append(perm)
            continue
        mapped_features[label] = 1
        # Only flip columns the trained model actually knows about.
        if label in feature_vector:
            feature_vector[label] = 1

    return feature_vector, mapped_features, unmapped


def count_dangerous_safe(mapped_features: dict[str, int]) -> tuple[int, int]:
    """Count dangerous vs safe permissions using the dataset's (D)/(S) marker.

    The training labels end in ``(D)`` (dangerous) or ``(S)`` (safe/normal);
    we reuse that exact convention so the counts match how the dataset's own
    ``Dangerous/Safe permissions count`` columns were defined.
    """
    dangerous = sum(1 for label in mapped_features if label.rstrip().endswith("(D)"))
    safe = sum(1 for label in mapped_features if label.rstrip().endswith("(S)"))
    return dangerous, safe


def analyze_apk(apk_path: str | Path) -> ExtractionResult:
    """Full APK Analysis Mode extraction for a single APK file."""
    apk_path = Path(apk_path)
    permissions = extract_permissions(apk_path)

    package = None
    if _PARSER_AVAILABLE:
        try:
            package = _APK(str(apk_path)).get_package()
        except Exception:
            package = None

    feature_vector, mapped_features, unmapped = build_feature_vector(permissions)
    dangerous, safe = count_dangerous_safe(mapped_features)

    return ExtractionResult(
        apk_path=str(apk_path),
        package=package,
        raw_permissions=permissions,
        mapped_features=mapped_features,
        feature_vector=feature_vector,
        dangerous_permission_count=dangerous,
        safe_permission_count=safe,
        unmapped_permissions=unmapped,
    )


def analyze_permission_list(permissions: list[str], apk_path: str = "<in-memory>") -> ExtractionResult:
    """Run the mapping/counting pipeline on an already-extracted permission list.

    Useful for testing and for Installed App Mode, which obtains permissions
    from ``PackageManager`` rather than from an APK file.
    """
    feature_vector, mapped_features, unmapped = build_feature_vector(permissions)
    dangerous, safe = count_dangerous_safe(mapped_features)
    return ExtractionResult(
        apk_path=apk_path,
        package=None,
        raw_permissions=sorted(set(permissions)),
        mapped_features=mapped_features,
        feature_vector=feature_vector,
        dangerous_permission_count=dangerous,
        safe_permission_count=safe,
        unmapped_permissions=unmapped,
    )


def _summary(result: ExtractionResult) -> dict:
    """A compact view that omits the full 151-column vector for readability."""
    d = result.to_dict()
    d["feature_vector_active"] = {k: v for k, v in result.feature_vector.items() if v}
    d["feature_vector_size"] = len(result.feature_vector)
    del d["feature_vector"]
    return d


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python -m backend.apk_analysis.permission_extractor <app.apk>")
        return 2
    result = analyze_apk(argv[1])
    print(json.dumps(_summary(result), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

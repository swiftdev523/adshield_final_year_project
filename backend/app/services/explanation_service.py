"""Rule-based Explanation Engine (no LLMs).

Input:
    permissions  - list of detected permissions (raw ``android.permission.*``,
                   bare names like ``SEND_SMS``, or dataset training labels)

Outputs:
    explanation  - factual permission-capability headline, not a final verdict
    reasons      - factual permission findings

The final overall explanation is built later by ``assessment_integrator`` after
the model and contextual/install-source components have been combined.
"""

from __future__ import annotations

from collections.abc import Iterable

from ...apk_analysis.permission_mapping import PERMISSION_TO_FEATURE, map_permission, normalize_permission
from .explanation_rules import (
    COMBINATION_RULES,
    PERMISSION_RULES,
)
from .permission_catalog import curated_sensitive_permissions


# Reverse map: dataset training label -> bare permission key.
_LABEL_TO_BARE: dict[str, str] = {label: bare for bare, label in PERMISSION_TO_FEATURE.items()}


def _to_bare_names(permissions: list[str]) -> set[str]:
    """Normalise any permission string to bare upper-case keys (``SEND_SMS``)."""
    bare: set[str] = set()
    for perm in permissions:
        if not perm or not str(perm).strip():
            continue
        text = str(perm).strip()

        # Already a dataset training column label?
        if text in _LABEL_TO_BARE:
            bare.add(_LABEL_TO_BARE[text])
            continue

        # Raw android.permission.* constant -> bare key via map table.
        mapped_label = map_permission(text)
        if mapped_label and mapped_label in _LABEL_TO_BARE:
            bare.add(_LABEL_TO_BARE[mapped_label])
            continue

        key = normalize_permission(text)
        if key in PERMISSION_RULES:
            bare.add(key)
        elif key in PERMISSION_TO_FEATURE:
            bare.add(key)
    return bare


def _to_catalog_labels(permissions: list[str]) -> set[str]:
    """Return canonical labels suitable for exact curated-catalog lookup."""
    labels: set[str] = set()
    for permission in permissions:
        if not permission or not str(permission).strip():
            continue
        text = str(permission).strip()
        if text in _LABEL_TO_BARE:
            labels.add(text)
            continue
        mapped = map_permission(text)
        if mapped:
            labels.add(mapped)
    return labels


def _deduplicate(lines: list[str]) -> list[str]:
    return list(dict.fromkeys(line.strip() for line in lines if line and line.strip()))


def explain(
    permissions: list[str],
    risk_score: int,
    risk_tier: str,
    *,
    dangerous_count: int | None = None,
    safe_count: int | None = None,
    canonical_labels: Iterable[str] | None = None,
) -> dict:
    """Generate factual permission findings without a final risk verdict.

    ``risk_score`` and ``risk_tier`` remain in the signature for the standalone
    endpoint and backward compatibility, but this permission-level stage does
    not append Safe/Suspicious/High-Risk conclusions. The authoritative verdict
    is generated only after contextual integration.

    Returns:
        explanation, permission reasons, and curated catalog matches.
    """
    del risk_score, risk_tier, dangerous_count, safe_count
    bare = _to_bare_names(permissions)
    catalog_labels = set(canonical_labels) if canonical_labels is not None else _to_catalog_labels(permissions)
    catalog_matches = curated_sensitive_permissions(catalog_labels)

    reasons: list[str] = []
    covered_by_combo: set[str] = set()

    # Layer 1: combination rules (highest priority).
    matched_combos = [r for r in COMBINATION_RULES if r["required"] <= bare]
    matched_combos.sort(key=lambda r: r["rank"], reverse=True)

    for combo in matched_combos:
        reasons.append(combo["detail"])
        covered_by_combo |= combo["required"]

    # Layer 2: curated permission descriptions, ordered high before medium.
    catalog_bare = set()
    for item in catalog_matches:
        key = _LABEL_TO_BARE.get(item["label"])
        if key:
            catalog_bare.add(key)
        if key in covered_by_combo:
            continue
        reasons.append(f"This app {item['description'].rstrip('.')}.")

    # Layer 3: factual rules not represented in the curated catalog.
    for key in sorted(bare):
        if key in covered_by_combo or key in catalog_bare:
            continue
        if key in PERMISSION_RULES:
            reasons.append(PERMISSION_RULES[key])

    # Headline: best combination, then highest curated item, then a factual
    # permission line. It deliberately contains no final risk-tier conclusion.
    if matched_combos:
        explanation = max(matched_combos, key=lambda r: r["rank"])["message"]
    elif catalog_matches:
        explanation = f"This app {catalog_matches[0]['description'].rstrip('.')}."
    else:
        perm_lines = [
            PERMISSION_RULES[k] for k in sorted(bare)
            if k in PERMISSION_RULES and k not in covered_by_combo
        ]
        if perm_lines:
            explanation = perm_lines[0].rstrip(".")
            if len(perm_lines) > 1:
                explanation += f" It also {perm_lines[1].replace('This app ', '').lower()}"
            explanation += "."
        else:
            explanation = "No high-priority permission capability was identified by the current rules."

    return {
        "explanation": explanation,
        "reasons": _deduplicate(reasons),
        "curated_sensitive_permissions": catalog_matches,
    }


def generate_explanation(
    active_permissions: set[str],
    prediction: str,
    dangerous_count: int,
    safe_count: int,
    risk_score: int | None = None,
) -> dict:
    """Backward-compatible wrapper used by existing prediction routes.

    Maps the old ``summary`` key to the new ``explanation`` key.
    """
    tier = prediction
    score = risk_score if risk_score is not None else _default_score_for_tier(tier)
    result = explain(
        list(active_permissions),
        score,
        tier,
        dangerous_count=dangerous_count,
        safe_count=safe_count,
    )
    return {"summary": result["explanation"], "reasons": result["reasons"], **result}


def build_reasons(
    features: dict[str, float],
    dangerous_count: int,
    safe_count: int,
    tier: str,
    risk_score: int | None = None,
) -> list[str]:
    """Backward-compatible helper returning only the reasons list."""
    active = {label for label, v in features.items() if float(v) >= 1}
    return generate_explanation(active, tier, dangerous_count, safe_count, risk_score)["reasons"]


def _default_score_for_tier(tier: str) -> int:
    """Fallback score when routes call without an explicit risk_score."""
    return {"Safe": 15, "Suspicious": 50, "High Risk": 85}.get(tier, 50)

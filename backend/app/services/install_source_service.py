"""Install source risk rules and overall risk combination.

Supported sources (normalised keys):
    google_play_store | website_download | apk_sideload | unknown_source

Each source maps to a source-specific risk level, a score adjustment, and an
explanation. The adjustment is added to the permission/model risk score (capped
at 100) to produce the **overall** risk assessment shown to the user.
"""

from __future__ import annotations

from ..config import TIER_HIGH_RISK, TIER_SAFE, TIER_SUSPICIOUS
from .risk_score import band_range, classify_risk

# Canonical source keys.
GOOGLE_PLAY = "google_play_store"
WEBSITE = "website_download"
APK_SIDELOAD = "apk_sideload"
UNKNOWN = "unknown_source"

SUPPORTED_SOURCES = {GOOGLE_PLAY, WEBSITE, APK_SIDELOAD, UNKNOWN}

# Aliases accepted from clients (Android PackageManager / human input).
SOURCE_ALIASES: dict[str, str] = {
    "play_store": GOOGLE_PLAY,
    "google_play": GOOGLE_PLAY,
    "play": GOOGLE_PLAY,
    "com.android.vending": GOOGLE_PLAY,
    "website": WEBSITE,
    "web": WEBSITE,
    "browser": WEBSITE,
    "download": WEBSITE,
    "sideload": APK_SIDELOAD,
    "sideloaded": APK_SIDELOAD,
    "apk": APK_SIDELOAD,
    "manual_apk": APK_SIDELOAD,
    "local_apk": APK_SIDELOAD,
    "unknown": UNKNOWN,
    "other": UNKNOWN,
    "unspecified": UNKNOWN,
}

# Rule table: source -> metadata used in assessment.
INSTALL_SOURCE_RULES: dict[str, dict] = {
    GOOGLE_PLAY: {
        "display_name": "Google Play Store",
        "source_risk_level": "Low",
        "risk_points": 0,
        "explanation": (
            "Reported as installed from Google Play Store. This source adds no "
            "contextual risk adjustment, but store origin alone does not guarantee safety."
        ),
    },
    WEBSITE: {
        "display_name": "Website download",
        "source_risk_level": "Moderate",
        "risk_points": 12,
        "explanation": (
            "Reported as downloaded from a website rather than an official app store. "
            "This can make publisher and origin verification harder, adding contextual "
            "uncertainty; it is not evidence that the app is malware."
        ),
    },
    APK_SIDELOAD: {
        "display_name": "APK sideload",
        "source_risk_level": "High",
        "risk_points": 20,
        "explanation": (
            "Reported as installed by sideloading an APK. This can make publisher "
            "and origin verification harder, adding contextual uncertainty; "
            "sideloading alone is not evidence that the app is malware."
        ),
    },
    UNKNOWN: {
        "display_name": "Unknown source",
        "source_risk_level": "Very High",
        "risk_points": 28,
        "explanation": (
            "The install source could not be verified. This adds contextual "
            "uncertainty about provenance; an unknown source alone is not evidence "
            "that the app is malware."
        ),
    },
}


def normalize_install_source(source: str | None) -> str:
    """Map client input to a canonical source key."""
    if not source or not str(source).strip():
        return UNKNOWN
    key = str(source).strip().lower().replace(" ", "_").replace("-", "_")
    if key in SUPPORTED_SOURCES:
        return key
    return SOURCE_ALIASES.get(key, UNKNOWN)


def analyze_install_source(source: str | None) -> dict:
    """Return source risk level and explanation for one install source."""
    canonical = normalize_install_source(source)
    rule = INSTALL_SOURCE_RULES[canonical]
    return {
        "install_source": canonical,
        "install_source_display": rule["display_name"],
        "source_risk_level": rule["source_risk_level"],
        "source_risk_points": rule["risk_points"],
        "source_explanation": rule["explanation"],
    }


def combine_risk_assessment(
    permission_risk_score: int,
    permission_risk_level: str,
    install_source: str | None,
) -> dict:
    """Merge permission/model risk with install-source risk into one verdict."""
    source = analyze_install_source(install_source)
    overall_score = min(100, int(permission_risk_score) + int(source["source_risk_points"]))
    overall_level = classify_risk(overall_score)

    tier_changed = overall_level != permission_risk_level
    if tier_changed and overall_level != TIER_SAFE:
        integration_note = (
            f"Overall risk raised from {permission_risk_level} to {overall_level} "
            f"after the contextual install-source adjustment "
            f"({source['install_source_display']}, +{source['source_risk_points']})."
        )
    elif source["source_risk_points"] == 0:
        integration_note = (
            f"Install source ({source['install_source_display']}) did not increase "
            "the permission-based risk score."
        )
    else:
        integration_note = (
            f"Install source ({source['install_source_display']}) added "
            f"+{source['source_risk_points']} to the permission risk score "
            f"({permission_risk_score} -> {overall_score})."
        )

    return {
        **source,
        "permission_risk_score": int(permission_risk_score),
        "permission_risk_level": permission_risk_level,
        "overall_risk_score": overall_score,
        "overall_risk_level": overall_level,
        "overall_band_range": band_range(overall_level),
        "risk_score": overall_score,
        "risk_level": overall_level,
        "band_range": band_range(overall_level),
        "integration_note": integration_note,
    }

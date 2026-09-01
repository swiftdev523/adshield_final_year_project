"""Permission risk mapping (the knowledge base of the Explanation Engine).

Each entry maps one model permission-column label to:
    phrase     : a plain-language description of what the permission lets an app do
    group      : a short noun phrase used when composing headline sentences
    category   : a coarse grouping (sms, telephony, location, ...)
    severity   : HIGH | MEDIUM | LOW  -- how concerning the permission is on its own

This is pure data. It contains no model logic and no LLM calls; the rules in
``explanation_service`` read from it to build deterministic explanations.
"""

from __future__ import annotations

from collections.abc import Iterable

HIGH = "high"
MEDIUM = "medium"
LOW = "low"

# label -> {phrase, group, category, severity}
PERMISSION_CATALOG: dict[str, dict] = {
    # --- Messaging / SMS (classic adware & fraud signal) ---------------
    "Services that cost you money : send SMS messages (D)": {
        "phrase": "can send SMS messages (which may incur charges)",
        "group": "SMS sending",
        "category": "sms",
        "severity": HIGH,
    },
    "Your messages : read SMS or MMS (D)": {
        "phrase": "can read your SMS/MMS messages",
        "group": "SMS reading",
        "category": "sms",
        "severity": HIGH,
    },
    "Your messages : receive SMS (D)": {
        "phrase": "can intercept incoming SMS",
        "group": "SMS interception",
        "category": "sms",
        "severity": HIGH,
    },
    "Your messages : edit SMS or MMS (D)": {
        "phrase": "can edit your SMS/MMS messages",
        "group": "SMS editing",
        "category": "sms",
        "severity": HIGH,
    },
    # --- Telephony ------------------------------------------------------
    "Services that cost you money : directly call phone numbers (D)": {
        "phrase": "can directly call phone numbers",
        "group": "phone calling",
        "category": "telephony",
        "severity": HIGH,
    },
    "Phone calls : read phone state and identity (D)": {
        "phrase": "can read your phone identity (device ID)",
        "group": "phone identity access",
        "category": "telephony",
        "severity": MEDIUM,
    },
    # --- Location -------------------------------------------------------
    "Your location : fine (GPS) location (D)": {
        "phrase": "tracks your precise GPS location",
        "group": "location tracking",
        "category": "location",
        "severity": HIGH,
    },
    "Your location : coarse (network-based) location (D)": {
        "phrase": "tracks your approximate location",
        "group": "location tracking",
        "category": "location",
        "severity": MEDIUM,
    },
    # --- Personal data --------------------------------------------------
    "Your personal information : read contact data (D)": {
        "phrase": "can read your contacts",
        "group": "contact access",
        "category": "contacts",
        "severity": HIGH,
    },
    "Your personal information : read sensitive log data (D)": {
        "phrase": "can read sensitive device logs",
        "group": "log access",
        "category": "system",
        "severity": MEDIUM,
    },
    # --- Display / overlay (ad-injection signal) -----------------------
    "System tools : display system-level alerts (D)": {
        "phrase": "can draw pop-ups or other content over other apps",
        "group": "screen overlays",
        "category": "overlay",
        "severity": HIGH,
    },
    # --- Persistence ----------------------------------------------------
    "System tools : automatically start at boot (S)": {
        "phrase": "starts automatically when the phone boots",
        "group": "startup permission",
        "category": "persistence",
        "severity": MEDIUM,
    },
    # --- Network --------------------------------------------------------
    "Network communication : full Internet access (D)": {
        "phrase": "has full internet access",
        "group": "internet access",
        "category": "network",
        "severity": MEDIUM,
    },
    # --- Hardware -------------------------------------------------------
    "Hardware controls : record audio (D)": {
        "phrase": "can record audio with the microphone",
        "group": "microphone access",
        "category": "microphone",
        "severity": HIGH,
    },
    "Hardware controls : take pictures and videos (D)": {
        "phrase": "can use the camera",
        "group": "camera access",
        "category": "camera",
        "severity": HIGH,
    },
    # --- Storage --------------------------------------------------------
    "Storage : modify/delete USB storage contents modify/delete SD card contents (D)": {
        "phrase": "can modify or delete files in your storage",
        "group": "storage modification",
        "category": "storage",
        "severity": MEDIUM,
    },
    # --- Surveillance of other apps ------------------------------------
    "System tools : retrieve running applications (D)": {
        "phrase": "can see what other apps are running",
        "group": "app monitoring",
        "category": "system",
        "severity": MEDIUM,
    },
}

# Severity ranking for ordering/selection.
SEVERITY_RANK = {HIGH: 3, MEDIUM: 2, LOW: 1}


def get_info(label: str) -> dict | None:
    """Return the catalog entry for a permission label, or None if unknown."""
    return PERMISSION_CATALOG.get(label)


def curated_sensitive_permissions(active_labels: Iterable[str]) -> list[dict]:
    """Return unique high/medium catalog matches in deterministic order.

    ``active_labels`` must contain canonical dataset permission labels. This
    curated project classification is intentionally independent of the legacy
    ``(D)``/``(S)`` suffix convention and is not Android ``protectionLevel``.
    """
    matched: list[dict] = []
    for label in {str(value).strip() for value in active_labels if str(value).strip()}:
        info = get_info(label)
        if not info or info["severity"] not in {HIGH, MEDIUM}:
            continue
        matched.append(
            {
                "label": label,
                "description": info["phrase"],
                "group": info["group"],
                "category": info["category"],
                "severity": info["severity"],
            }
        )

    return sorted(
        matched,
        key=lambda item: (-SEVERITY_RANK[item["severity"]], item["label"]),
    )

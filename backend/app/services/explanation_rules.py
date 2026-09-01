"""Rule-based explanation dictionary for the Android Adware Detection System.

All rules use **bare Android permission names** (e.g. ``SEND_SMS``), matching what
APK manifests and ``PackageManager`` return after normalisation.

No LLMs - every explanation is deterministic and auditable.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Layer 1: single-permission rules
# Key = bare permission constant | Value = human-readable sentence
# ---------------------------------------------------------------------------
PERMISSION_RULES: dict[str, str] = {
    "SEND_SMS": "This app can send SMS messages.",
    "READ_SMS": "This app can read SMS messages.",
    "RECEIVE_SMS": "This app can receive SMS messages.",
    "WRITE_SMS": "This app can modify SMS messages.",
    "RECEIVE_MMS": "This app can receive MMS messages.",
    "CALL_PHONE": "This app can directly call phone numbers.",
    "READ_PHONE_STATE": "This app can read phone state and device identity.",
    "PROCESS_OUTGOING_CALLS": "This app can intercept outgoing phone calls.",
    "ACCESS_FINE_LOCATION": "This app can track your location.",
    "ACCESS_COARSE_LOCATION": "This app can track your approximate location.",
    "ACCESS_MOCK_LOCATION": "This app can use mock location data.",
    "READ_CONTACTS": "This app can access contact information.",
    "WRITE_CONTACTS": "This app can modify your contacts.",
    "READ_CALENDAR": "This app can read your calendar.",
    "WRITE_CALENDAR": "This app can modify your calendar.",
    "READ_CALL_LOG": "This app can read your call history.",
    "WRITE_CALL_LOG": "This app can modify your call history.",
    "CAMERA": "This app can use the camera.",
    "RECORD_AUDIO": "This app can record audio with the microphone.",
    "READ_EXTERNAL_STORAGE": "This app can read files on your storage.",
    "WRITE_EXTERNAL_STORAGE": "This app can modify or delete files on your storage.",
    "INTERNET": "This app has full internet access.",
    "ACCESS_NETWORK_STATE": "This app can check network connectivity.",
    "ACCESS_WIFI_STATE": "This app can check Wi-Fi status.",
    "RECEIVE_BOOT_COMPLETED": "This app can automatically start when the phone boots.",
    "SYSTEM_ALERT_WINDOW": "This app can display pop-ups over other apps.",
    "GET_TASKS": "This app can see what other apps are running.",
    "READ_LOGS": "This app can read sensitive device logs.",
    "WAKE_LOCK": "This app can prevent the phone from sleeping.",
    "VIBRATE": "This app can control the vibrator.",
    "BLUETOOTH": "This app can use Bluetooth.",
    "NFC": "This app can use Near Field Communication (NFC).",
    "INSTALL_PACKAGES": "This app can install other applications.",
    "DELETE_PACKAGES": "This app can uninstall other applications.",
}

# ---------------------------------------------------------------------------
# Layer 2: combination rules (fire when ALL listed permissions are present)
# Combination messages take priority over individual permission lines.
# ---------------------------------------------------------------------------
COMBINATION_RULES: list[dict] = [
    {
        "name": "send_and_read_sms",
        "required": frozenset({"SEND_SMS", "READ_SMS"}),
        "message": "This app can send and read SMS messages.",
        "detail": (
            "The app can both send and read SMS messages, giving it broad access "
            "to messaging functions that should be justified by its purpose."
        ),
        "rank": 5,
    },
    {
        "name": "sms_and_boot",
        "required": frozenset({"SEND_SMS", "RECEIVE_BOOT_COMPLETED"}),
        "message": "This app can send SMS messages and start automatically when the phone boots.",
        "detail": (
            "SMS sending combined with automatic startup can resume messaging "
            "activity after a restart; verify that the app genuinely needs both."
        ),
        "rank": 5,
    },
    {
        "name": "overlay_and_boot",
        "required": frozenset({"SYSTEM_ALERT_WINDOW", "RECEIVE_BOOT_COMPLETED"}),
        "message": "This app can display over other apps and start automatically when the phone boots.",
        "detail": (
            "Overlay access combined with automatic startup can support persistent "
            "pop-ups or other always-available behaviour; legitimate apps may also "
            "use this combination."
        ),
        "rank": 4,
    },
    {
        "name": "read_sms_and_internet",
        "required": frozenset({"READ_SMS", "INTERNET"}),
        "message": "This app can read messages and access the internet.",
        "detail": (
            "Message access combined with internet access could expose message "
            "content if misused; verify why the app needs both capabilities."
        ),
        "rank": 4,
    },
    {
        "name": "contacts_and_internet",
        "required": frozenset({"READ_CONTACTS", "INTERNET"}),
        "message": "This app can read contacts and access the internet.",
        "detail": (
            "Contact access combined with internet access could expose address-book "
            "data if misused; verify that both are necessary."
        ),
        "rank": 3,
    },
    {
        "name": "location_and_internet",
        "required": frozenset({"ACCESS_FINE_LOCATION", "INTERNET"}),
        "message": "This app can access precise location and the internet.",
        "detail": (
            "Location and internet access together could transmit location data if "
            "misused; verify that this matches the app's purpose."
        ),
        "rank": 3,
    },
]

# Permissions covered by a fired combination (skip duplicate single-perm lines).
COMBINATION_COVERS: dict[str, frozenset[str]] = {
    rule["name"]: rule["required"] for rule in COMBINATION_RULES
}


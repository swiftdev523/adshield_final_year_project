"""Mapping from raw Android permission constants to the model's feature labels.

Why this file exists
--------------------
An APK's ``AndroidManifest.xml`` declares permissions as constants such as
``android.permission.SEND_SMS``. The training dataset (Android_Permission.csv),
however, names its columns with legacy Google-Play *display labels* such as
``Services that cost you money : send SMS messages (D)``.

To turn a real APK into the exact feature format the model was trained on, every
raw permission constant must be translated to its dataset label. This module
holds that translation table.

Keys
----
Each key is the *bare* permission name: the part after the final ``.`` of the
constant, upper-cased. For example:
    ``android.permission.ACCESS_FINE_LOCATION`` -> ``ACCESS_FINE_LOCATION``
    ``com.google.android.c2dm.permission.RECEIVE`` -> ``RECEIVE``
Use :func:`normalize_permission` to derive the bare key from any constant.

The ``(D)`` / ``(S)`` suffix inside each label is the dataset's own
dangerous/safe marker and is reused for counting (see ``permission_extractor``).
Permissions not present here (mostly obsolete Google-service labels with no
predictive signal) are reported as ``unmapped`` and left at 0 in the vector.
"""

from __future__ import annotations

# Bare permission name -> exact dataset feature column label.
PERMISSION_TO_FEATURE: dict[str, str] = {
    # --- Location -------------------------------------------------------
    "ACCESS_FINE_LOCATION": "Your location : fine (GPS) location (D)",
    "ACCESS_COARSE_LOCATION": "Your location : coarse (network-based) location (D)",
    "ACCESS_MOCK_LOCATION": "Your location : mock location sources for testing (D)",
    "ACCESS_LOCATION_EXTRA_COMMANDS": "Your location : access extra location provider commands (S)",
    "INSTALL_LOCATION_PROVIDER": "Default : permission to install a location provider (S)",
    "CONTROL_LOCATION_UPDATES": "Default : control location update notifications (S)",
    # --- Network communication -----------------------------------------
    "INTERNET": "Network communication : full Internet access (D)",
    "ACCESS_NETWORK_STATE": "Network communication : view network state (S)",
    "ACCESS_WIFI_STATE": "Network communication : view Wi-Fi state (S)",
    "RECEIVE": "Network communication : receive data from Internet (S)",
    "BLUETOOTH": "Network communication : create Bluetooth connections (D)",
    "NFC": "Network communication : control Near Field Communication (D)",
    "USE_SIP": "Network communication : make/receive Internet calls (D)",
    # --- System tools ---------------------------------------------------
    "SET_WALLPAPER": "System tools : set wallpaper (S)",
    "SET_WALLPAPER_HINTS": "System tools : set wallpaper size hints (S)",
    "WAKE_LOCK": "System tools : prevent device from sleeping (D)",
    "RECEIVE_BOOT_COMPLETED": "System tools : automatically start at boot (S)",
    "KILL_BACKGROUND_PROCESSES": "System tools : kill background processes (S)",
    "RESTART_PACKAGES": "System tools : kill background processes (S)",
    "GET_TASKS": "System tools : retrieve running applications (D)",
    "REORDER_TASKS": "System tools : reorder running applications (D)",
    "SYSTEM_ALERT_WINDOW": "System tools : display system-level alerts (D)",
    "WRITE_SETTINGS": "System tools : modify global system settings (D)",
    "CHANGE_NETWORK_STATE": "System tools : change network connectivity (D)",
    "CHANGE_WIFI_STATE": "System tools : change Wi-Fi state (D)",
    "CHANGE_WIFI_MULTICAST_STATE": "System tools : allow Wi-Fi Multicast reception (D)",
    "EXPAND_STATUS_BAR": "System tools : expand/collapse status bar (S)",
    "BROADCAST_STICKY": "System tools : send sticky broadcast (S)",
    "MOUNT_UNMOUNT_FILESYSTEMS": "System tools : mount and unmount filesystems (D)",
    "MOUNT_FORMAT_FILESYSTEMS": "System tools : format external storage (D)",
    "CLEAR_APP_CACHE": "System tools : delete all application cache data (D)",
    "WRITE_APN_SETTINGS": "System tools : write Access Point Name settings (D)",
    "WRITE_SYNC_SETTINGS": "System tools : write sync settings (D)",
    "READ_SYNC_SETTINGS": "System tools : read sync settings (S)",
    "READ_SYNC_STATS": "System tools : read sync statistics (S)",
    "SET_TIME_ZONE": "System tools : set time zone (D)",
    "SET_PREFERRED_APPLICATIONS": "System tools : set preferred applications (S)",
    "GET_PACKAGE_SIZE": "System tools : measure application storage space (S)",
    "CHANGE_CONFIGURATION": "System tools : change your UI settings (D)",
    "SET_ANIMATION_SCALE": "System tools : modify global animation speed (D)",
    "DISABLE_KEYGUARD": "System tools : disable keylock (D)",
    "PERSISTENT_ACTIVITY": "System tools : make application always run (D)",
    "BLUETOOTH_ADMIN": "System tools : bluetooth administration (D)",
    "FORCE_STOP_PACKAGES": "System tools : force stop other applications (S)",
    "SUBSCRIBED_FEEDS_READ": "System tools : read subscribed feeds (S)",
    "SUBSCRIBED_FEEDS_WRITE": "System tools : write subscribed feeds (D)",
    # --- Phone calls ----------------------------------------------------
    "READ_PHONE_STATE": "Phone calls : read phone state and identity (D)",
    "MODIFY_PHONE_STATE": "Phone calls : modify phone state (S)",
    "PROCESS_OUTGOING_CALLS": "Phone calls : intercept outgoing calls (D)",
    # --- Services that cost money --------------------------------------
    "SEND_SMS": "Services that cost you money : send SMS messages (D)",
    "CALL_PHONE": "Services that cost you money : directly call phone numbers (D)",
    "CALL_PRIVILEGED": "Default : directly call any phone numbers (S)",
    # --- Your messages --------------------------------------------------
    "RECEIVE_SMS": "Your messages : receive SMS (D)",
    "READ_SMS": "Your messages : read SMS or MMS (D)",
    "WRITE_SMS": "Your messages : edit SMS or MMS (D)",
    "RECEIVE_MMS": "Your messages : receive MMS (D)",
    "RECEIVE_WAP_PUSH": "Your messages : receive WAP (D)",
    "READ_GMAIL": "Your messages : read Gmail (D)",
    # --- Your personal information -------------------------------------
    "READ_CONTACTS": "Your personal information : read contact data (D)",
    "WRITE_CONTACTS": "Your personal information : write contact data (D)",
    "READ_CALENDAR": "Your personal information : read calendar events (D)",
    "WRITE_CALENDAR": "Your personal information : add or modify calendar events and send email to guests (D)",
    "READ_HISTORY_BOOKMARKS": "Your personal information : read Browser's history and bookmarks (D)",
    "WRITE_HISTORY_BOOKMARKS": "Your personal information : write Browser's history and bookmarks (D)",
    "READ_LOGS": "Your personal information : read sensitive log data (D)",
    "READ_USER_DICTIONARY": "Your personal information : read user defined dictionary (D)",
    "WRITE_USER_DICTIONARY": "Your personal information : write to user defined dictionary (S)",
    "SET_ALARM": "Your personal information : set alarm in alarm clock (S)",
    # --- Hardware controls ---------------------------------------------
    "RECORD_AUDIO": "Hardware controls : record audio (D)",
    "CAMERA": "Hardware controls : take pictures and videos (D)",
    "VIBRATE": "Hardware controls : control vibrator (S)",
    "FLASHLIGHT": "Hardware controls : control flashlight (S)",
    "MODIFY_AUDIO_SETTINGS": "Hardware controls : change your audio settings (D)",
    "HARDWARE_TEST": "Hardware controls : test hardware (S)",
    # --- Your accounts --------------------------------------------------
    "GET_ACCOUNTS": "Your accounts : view configured accounts (S)",
    "MANAGE_ACCOUNTS": "Your accounts : manage the accounts list (D)",
    "USE_CREDENTIALS": "Your accounts : use the authentication credentials of an account (D)",
    "AUTHENTICATE_ACCOUNTS": "Your accounts : act as an account authenticator (D)",
    # --- Storage --------------------------------------------------------
    "WRITE_EXTERNAL_STORAGE": "Storage : modify/delete USB storage contents modify/delete SD card contents (D)",
    # --- Development tools ---------------------------------------------
    "SET_DEBUG_APP": "Development tools : enable application debugging (D)",
    "SET_ALWAYS_FINISH": "Development tools : make all background applications close (D)",
    "SET_PROCESS_LIMIT": "Development tools : limit number of running processes (D)",
    "SIGNAL_PERSISTENT_PROCESSES": "Development tools : send Linux signals to applications (D)",
    # --- Default / misc -------------------------------------------------
    "DEVICE_POWER": "Default : power device on or off (S)",
    "REBOOT": "Default : force device reboot (S)",
    "SET_TIME": "Default : set time (S)",
    "SET_ORIENTATION": "Default : change screen orientation (S)",
    "STATUS_BAR": "Default : disable or modify status bar (S)",
    "ACCESS_CHECKIN_PROPERTIES": "Default : access checkin properties (S)",
    "ACCESS_CACHE_FILESYSTEM": "Default : access the cache filesystem (S)",
    "ACCESS_SURFACE_FLINGER": "Default : access SurfaceFlinger (S)",
    "READ_FRAME_BUFFER": "Default : read frame buffer (S)",
    "BATTERY_STATS": "Default : modify battery statistics (S)",
    "BIND_INPUT_METHOD": "Default : bind to an input method (S)",
    "BIND_WALLPAPER": "Default : bind to a wallpaper (S)",
    "BIND_DEVICE_ADMIN": "Default : interact with a device admin (S)",
    "BACKUP": "Default : control system backup and restore (S)",
    "INSTALL_PACKAGES": "Default : directly install applications (S)",
    "DELETE_PACKAGES": "Default : delete applications (S)",
    "DELETE_CACHE_FILES": "Default : delete other applications' caches (S)",
    "CLEAR_APP_USER_DATA": "Default : delete other applications' data (S)",
    "WRITE_SECURE_SETTINGS": "Default : modify secure system settings (S)",
    "WRITE_GSERVICES": "Default : modify the Google services map (S)",
}


def normalize_permission(permission: str) -> str:
    """Return the bare, upper-cased key for a raw permission constant.

    ``android.permission.SEND_SMS``                 -> ``SEND_SMS``
    ``com.google.android.c2dm.permission.RECEIVE``  -> ``RECEIVE``
    ``SEND_SMS``                                     -> ``SEND_SMS``
    """
    if not permission:
        return ""
    return permission.strip().rsplit(".", 1)[-1].upper()


def map_permission(permission: str) -> str | None:
    """Map one raw permission constant to its dataset label, or ``None``."""
    return PERMISSION_TO_FEATURE.get(normalize_permission(permission))

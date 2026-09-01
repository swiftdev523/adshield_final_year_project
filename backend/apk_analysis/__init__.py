"""APK Analysis Mode components.

Public entry points:
    extract_permissions(apk_path)   -> list[str]   raw android.permission.* strings
    analyze_apk(apk_path)           -> dict         full extraction result

The result is shaped to match the feature format used during model training
(see ``feature_schema.py``), but this module never calls the ML model itself.
"""

from .permission_extractor import analyze_apk, extract_permissions

__all__ = ["analyze_apk", "extract_permissions"]

"""Central configuration: artifact paths and risk-tier cut-offs.

Keeping these in one place makes the scoring policy easy to audit and tune
without touching the service code.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

# backend/app/config.py -> project root is two parents up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
RUNTIME_TEMP_DIR = PROJECT_ROOT / ".runtime" / "tmp"


def configure_runtime_temp_dir() -> Path:
    """Keep multipart spooling and APK temp files off the system drive."""
    RUNTIME_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(RUNTIME_TEMP_DIR)
    return RUNTIME_TEMP_DIR

# The two artifacts produced by final_train.py (Installed App Mode model:
# permissions + store metadata).
FINAL_MODEL_PATH = MODELS_DIR / "final_model.joblib"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.joblib"

# --- APK Analysis Mode model ------------------------------------------
# Frozen TUANDROMD RandomForest with a mixed 241-column permission/API contract.
# The current runtime supplies manifest permissions only and reports the input
# contract as partial; it does not fabricate the unavailable static API flags.
# No store metadata is required. To swap models, change this path.
#
# Head-to-head on identical TUANDROMD data (in-sample for both, fair relative
# comparison): adware_detection_rf_model beats best_adware_model_tuned on every
# metric (ROC-AUC 0.9996 vs 0.9935, F1 0.998 vs 0.987) AND works at the standard
# 0.5 threshold, so it is the chosen model.
APK_MODEL_PATH = MODELS_DIR / "adware_detection_rf_model.pkl"
APK_MODEL_THRESHOLD = 0.5

# --- Experimental selective category classification -------------------
# This unchanged four-class Random Forest is a post-binary sidecar only. It
# must run only after APK_MODEL_PATH returns the Malicious binary path. The
# exact margin threshold is locked by the accepted development analysis in
# models/category_final_validation/abstention_analysis/locked_abstention_rule.json.
# New independent validation is still required; this is not a production
# malware-family classifier and its raw class scores are not confidence values.
CATEGORY_MODEL_PATH = (
    MODELS_DIR
    / "category_final_validation"
    / "artifacts"
    / "selected_category_model_provisional.joblib"
)
CATEGORY_MARGIN_THRESHOLD = 0.70

# --- Notification spam detection --------------------------------------
# Production artifacts (v2). Paths also recorded in notification_threshold.json.
NOTIFICATION_THRESHOLD_JSON = MODELS_DIR / "notification_threshold.json"
NOTIFICATION_MODEL_PATH = MODELS_DIR / "notification_spam_model_v2.joblib"
NOTIFICATION_VECTORIZER_PATH = MODELS_DIR / "notification_vectorizer_v2.joblib"
NOTIFICATION_DECISION_THRESHOLD = 0.29  # overridden from JSON at load time if present

# Monitor: flag an app when it exceeds this many notifications in the window.
NOTIFICATION_MONITOR_WINDOW_SECONDS = 300  # 5 minutes
NOTIFICATION_MONITOR_ALERT_COUNT = 10        # total notifications in window
NOTIFICATION_MONITOR_SPAM_ALERT_COUNT = 5  # spam notifications in window

# --- Risk Score Engine policy -----------------------------------------
# The model outputs P(malware) in [0, 1]. The Risk Score Engine converts that to
# a 0-100 score (score = round(p * 100)) and assigns one of three bands:
#
#   0  - 30   -> Safe
#   31 - 70   -> Suspicious
#   71 - 100  -> High Risk
#
# These are the single source of truth for the band cut-offs.
SAFE_MAX_SCORE = 30
SUSPICIOUS_MAX_SCORE = 70

# Tier labels (single source of truth).
TIER_SAFE = "Safe"
TIER_SUSPICIOUS = "Suspicious"
TIER_HIGH_RISK = "High Risk"

"""Loads the canonical permission-feature column list used during training.

This reads ``models/feature_columns.joblib`` - the *feature contract* produced
by ``final_train.py`` - and exposes the ordered list of the 151 active
permission columns the model expects.

Important: this file loads only the column **names / recipe**, never the trained
model. It exists so the APK extractor emits a vector whose columns exactly match
training, without coupling to (or running) the ML model.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib

# backend/apk_analysis/feature_schema.py -> project root is three parents up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURE_COLUMNS_PATH = PROJECT_ROOT / "models" / "feature_columns.joblib"


@lru_cache(maxsize=1)
def load_permission_feature_names() -> list[str]:
    """Return the ordered list of active permission feature columns.

    Falls back to an empty list if the schema artifact is missing, so the
    extractor can still run (it will simply have no canonical column order).
    """
    if not FEATURE_COLUMNS_PATH.exists():
        return []
    bundle = joblib.load(FEATURE_COLUMNS_PATH)
    recipe = bundle.get("feature_recipe", {})
    return list(recipe.get("active_permission_features", []))

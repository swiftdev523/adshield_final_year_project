# AdShield Runtime Artifact Manifest

This manifest identifies the files that a clean clone needs in order to run the current backend and Android development client. Raw datasets and malware APK collections are not runtime dependencies and are intentionally excluded.

All binary artifacts are below GitHub's 50 MB warning threshold, so the baseline uses normal Git rather than Git LFS.

| Artifact | Path | Purpose | Included in repository | Normal Git or Git LFS |
| --- | --- | --- | --- | --- |
| Installed-app binary model | `models/final_model.joblib` | Scores installed-app permission and install-source feature vectors | Yes | Normal Git |
| Installed-app feature schema | `models/feature_columns.joblib` | Preserves the exact ordered input columns required by the installed-app model | Yes | Normal Git |
| APK binary malware model | `models/adware_detection_rf_model.pkl` | Scores manifest-permission input for APK analysis | Yes | Normal Git |
| Category model | `models/category_final_validation/artifacts/selected_category_model_provisional.joblib` | Applies the accepted four-category Random Forest after the APK binary model returns Malicious | Yes | Normal Git |
| Category 153-feature schema | `models/category_experimental/permission_features.json` | Human-readable/exported ordered permission contract; the category bundle also embeds and validates the same 153-feature contract | Yes | Normal Git |
| Locked abstention rule | `models/category_final_validation/abstention_analysis/locked_abstention_rule.json` | Records the precommitted category rejection rule represented by the backend's locked margin threshold | Yes | Normal Git |
| Notification spam model | `models/notification_spam_model_v2.joblib` | Classifies explicitly selected eligible notification text | Yes | Normal Git |
| Notification vectorizer | `models/notification_vectorizer_v2.joblib` | Reproduces the notification model's text feature transformation | Yes | Normal Git |
| Notification threshold | `models/notification_threshold.json` | Supplies the persisted notification decision threshold | Yes | Normal Git |
| Permission mapping | `backend/apk_analysis/permission_mapping.py` | Normalizes Android permissions and maps APK declarations to model features | Yes | Normal Git |
| Curated permission catalog | `backend/app/services/permission_catalog.py` | Produces user-facing permissions-worth-reviewing metadata | Yes | Normal Git |
| Installed App native module | `adshield_final_year_project-main/modules/installed-app-monitor/` | Reads launcher-visible PackageManager metadata locally on Android | Yes | Normal Git |
| Notification Listener native module | `adshield_final_year_project-main/modules/notification-monitor/` | Captures eligible Android notification events into the on-device history | Yes | Normal Git |
| Persistent dependency patches | `adshield_final_year_project-main/patches/` | Reapplies the verified React Native/Expo/CMake fixes after `npm ci` | Yes | Normal Git |

## Required runtime SHA-256 values

| Path | SHA-256 |
| --- | --- |
| `models/final_model.joblib` | `a1185c43c3aee82461ccebb6b2a62ab09bc471e328adf4390c63bf6388d24ac4` |
| `models/feature_columns.joblib` | `e3a3205e15f50d4e4c5cdefac0c6c55734694f43874582fc1821ad02b413d7fa` |
| `models/adware_detection_rf_model.pkl` | `54b7560bf7845b5eb5fb7a60057fd9a166c2843c5c8e65c133ad78d80d2aeba5` |
| `models/category_final_validation/artifacts/selected_category_model_provisional.joblib` | `9b2f3b2a880372ff077fdc37e6e3d7909c9ba3ba28cabce371a58d1f6b80f3b9` |
| `models/category_experimental/permission_features.json` | `9bbbdbf826db7957a0335baefa93eb8bc3440c4edcf7f5825cccf949a105a4fd` |
| `models/notification_spam_model_v2.joblib` | `8bcb6512a3e8d96296b6d2ac1089533c92bc417e28f18b1f7c3b84753384889e` |
| `models/notification_vectorizer_v2.joblib` | `8925cbb5643320be333295f82cda0c62b1c955109515f13c91ae86f0d2d64b2f` |
| `models/notification_threshold.json` | `c848d85d6ac32efde42292ce32c39aefc6085b2ddfc4d3a293378a4e6c1d61d8` |


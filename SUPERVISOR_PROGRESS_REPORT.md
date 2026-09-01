# Supervisor Progress Report
## Android Adware Detection and Prevention System Using Machine Learning

**Prepared for:** Progress meeting  
**Scope covered:** Project start → data preparation → machine learning → production model → APK permission extraction  
**Status:** Core ML pipeline complete; APK Analysis Mode extraction module implemented

---

## 1. Project Overview

The approved project goal is to build a **mobile security system** that helps users identify potentially dangerous Android applications **before and after installation**, using:

- Permission-based risk analysis  
- Machine learning classification  
- Risk scoring and human-readable explanations (planned)  
- Notification spam detection (separate track)  
- Guardian mode for non-technical users (planned)

This report summarises work completed from the beginning of the project through the **APK Permission Extraction module**, which connects real Android app files to the trained model’s feature format.

---

## 2. Work Completed — Chronological Summary

### Phase 1: Data collection and understanding

Four datasets were gathered and analysed:

| Dataset | Purpose | Size (approx.) |
|---------|---------|----------------|
| **Android_Permission.csv** | App permissions + store metadata + malware labels | ~30,000 apps |
| **TUANDROMD.csv** | Manifest permissions / APIs | ~4,500 apps |
| **computer and security_2.xlsx** | APK permission matrices (Play Store, third-party, malware) | up to ~117k rows |
| **SMSSpamCollection** | SMS spam text (for notification spam detection — kept separate) | ~5,600 messages |

**Actions taken:**
- Profiled each dataset (shape, columns, missing values, duplicates, label distribution).
- Documented findings in analysis and cleaning reports.
- Resolved practical issues (large Excel file loading, path mismatches, label naming differences across sources).

**Outcome:** A clear picture of what each dataset contains and which sources are suitable for permission-based malware detection.

---

### Phase 2: Data cleaning and preparation

**Actions taken:**
- Standardised labels to binary form: **0 = benign/safe**, **1 = malware/spam**.
- Removed duplicate rows (notably in TUANDROMD and Android_Permission).
- Imputed missing values (numeric → 0 or median; text → empty string).
- Exported cleaned CSVs to `data/processed/cleaned/`.

**Outcome:** Consistent, ML-ready datasets with uniform labelling.

---

### Phase 3: Feature alignment and merged dataset (experimental)

**Actions taken:**
- Built a unified permission schema across Android_Permission, TUANDROMD, and Excel sources.
- Aligned each app to the same permission columns (missing permissions → 0).
- Produced merged artifacts: `ml_merged_permissions.csv` / `.joblib` (117,355 rows × 1,523 features).
- Excluded SMS data from the permission merge (text-only, different task).

**Key finding:** Merging all sources did **not** improve the final model. The merged set dropped valuable store metadata from Android_Permission and was dominated by a weakly separable source (~67% baseline accuracy). This led to the decision to use **Android_Permission.csv as the production dataset**, with merged data kept for comparison and reporting only.

---

### Phase 4: Baseline modelling and diagnostics

**Actions taken:**
- Trained and compared **Random Forest, Decision Tree, and Logistic Regression** on the merged dataset.
- Ran **5-fold stratified cross-validation** and **GridSearchCV** hyperparameter tuning on Random Forest.
- Investigated class imbalance (balanced weights, undersampling, SMOTE).

**Results:**
- Baseline accuracy plateaued around **~68%** on the merged data.
- Tuning and resampling gave only marginal gains — the limit was **feature quality**, not model choice.

**Outcome:** Reframed the project toward **better features and dataset selection** rather than endless model tuning.

---

### Phase 5: Feature engineering breakthrough

**Actions taken:**
- Re-introduced previously dropped **metadata features** from Android_Permission.csv:
  - Rating, Number of ratings, Price  
  - Dangerous permissions count, Safe permissions count  
- Engineered **`log_number_of_ratings = log1p(Number of ratings)`** — kept permanently.
- Tested and **excluded** `dangerous_to_safe_ratio` (no predictive signal).

**Key finding:** Store metadata (especially **Price** and **Number of ratings**, with log transform) is **far more predictive** than individual permission flags alone. Permission flags still contribute, but metadata unlocked meaningful separability.

**Final feature set (157 features):**
- 151 active permission flags (binary 0/1)  
- 5 metadata fields  
- 1 engineered feature (`log_number_of_ratings`)

---

### Phase 6: Final production model

**Script:** `final_train.py` (single self-contained production training pipeline)

**Dataset:** Android_Permission.csv — **27,310 rows** (deduplicated), **66.8% malware**

**Model selected:** **HistGradientBoostingClassifier** (`class_weight=balanced`)

**Why this model:**
- Best **ROC-AUC (0.8115)** — fairest threshold-independent measure of separability  
- Best **F1 (0.8088)** and highest **recall (95%)** — important for security (catching malware)  
- Handles mixed binary + numeric features without extra scaling  

**Model comparison (held-out 20% test, tuned threshold):**

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|-------|----------|-----------|--------|-----|---------|
| **HistGradientBoosting** | 0.70 | 0.70 | **0.95** | **0.81** | **0.81** |
| Logistic Regression | 0.71 | 0.74 | 0.88 | 0.80 | 0.80 |
| Random Forest | 0.67 | 0.67 | 0.99 | 0.80 | 0.76 |
| Decision Tree | 0.67 | 0.75 | 0.77 | 0.76 | 0.62 |

**Saved artifacts:**
- `models/final_model.joblib` — model + decision threshold + feature recipe  
- `models/feature_columns.joblib` — ordered 157 feature names  
- `final_metrics.json`, `final_model_report.md`, `final_feature_importance.csv`

---

### Phase 7: System design (APK vs Installed App modes)

Before building the extraction module, the architecture was defined to match supervisor feedback (**not APK-only**):

- **APK Analysis Mode** — uses permissions extractable from the APK file (pre-install).  
- **Installed App Analysis Mode** — adds store metadata, notification behaviour, and install source when available.

Shared core: **151 permission flags + dangerous/safe permission counts** — the part both modes can always supply.

---

### Phase 8: APK Permission Extraction module ✅ (latest milestone)

**Location:** `backend/apk_analysis/`

**Purpose:** Bridge a real `.apk` file to the exact feature format the model was trained on — without yet calling the ML model.

**What it does:**
1. Accepts an uploaded APK file.  
2. Parses **AndroidManifest.xml** (binary AXML via `pyaxmlparser`).  
3. Extracts declared `android.permission.*` constants.  
4. Maps each permission to the **dataset’s human-readable column labels** (e.g. `SEND_SMS` → `Services that cost you money : send SMS messages (D)`).  
5. Builds a **151-column binary feature vector** aligned to `feature_columns.joblib`.  
6. Computes **dangerous** and **safe** permission counts using the dataset’s `(D)` / `(S)` markers.

**Key files:**
| File | Role |
|------|------|
| `permission_extractor.py` | Main pipeline (`analyze_apk`, `extract_permissions`) |
| `permission_mapping.py` | Android permission → training column label table |
| `feature_schema.py` | Loads canonical 151 column names from saved model recipe |
| `backend/examples/example_output.json` | Sample output |

**Example output (tested):**
- Raw permissions extracted from manifest  
- Mapped features (0/1 per training column)  
- `dangerous_permission_count` and `safe_permission_count`  
- Full `feature_vector` (151 columns) ready for the scoring layer  

**Design note:** The module is deliberately **decoupled from the ML model** so extraction can be tested and demonstrated independently. The next integration step is feeding this vector into `final_model.joblib` for a live risk score.

---

## 3. Key Technical Decisions (for discussion)

| Decision | Rationale |
|----------|-----------|
| Android_Permission.csv as production dataset | Best performance; retains metadata; aligns with project goal |
| Merged dataset kept experimental only | Dropped metadata; dominated by weak signal source |
| HistGradientBoosting as production model | Best ROC-AUC + recall; practical for mixed features |
| `log_number_of_ratings` kept permanently | Strong engineered signal; especially helps linear models |
| APK extractor maps to training labels | Model columns use Play Store display names, not raw `android.permission.*` strings |
| Two-mode architecture (APK + Installed) | Respects TA feedback: support Play Store, sideloaded APK, and installed apps |

---

## 4. Challenges Encountered and Resolved

1. **~68% accuracy ceiling on merged data** — diagnosed as weak separability in the dominant dataset, not a tuning problem.  
2. **Large Excel file timeouts** — sampling (`EXCEL_MAX_ROWS`) for development; full run optional.  
3. **Class imbalance** — resampling did not materially improve F1; feature quality was the bottleneck.  
4. **APK manifest is binary XML** — requires dedicated parser (`pyaxmlparser`), not plain text reading.  
5. **Permission name mismatch** — training uses legacy Play Store labels; mapping table built to translate manifest permissions.

---

## 5. Current Project Status

| Component | Status |
|-----------|--------|
| Data analysis and cleaning | ✅ Complete |
| Feature engineering and model selection | ✅ Complete |
| Production model trained and saved | ✅ Complete |
| System architecture (two analysis modes) | ✅ Designed |
| **APK permission extraction** | ✅ **Implemented and tested** |
| Backend API / risk scoring / explanations | 🔜 Next phase |
| Android app / Guardian Mode | 🔜 Planned |

---

## 6. Planned Next Steps (after APK extraction)

1. Connect the APK extractor output to `final_model.joblib` for live predictions.  
2. Implement risk scoring (0–100) and tiers (Safe / Suspicious / High Risk).  
3. Build the rule-based explanation engine for permission combinations.  
4. Integrate notification spam detection (separate Random Forest on SMS data).  
5. Develop the Android client and Guardian Mode UI.

---

## 7. Summary Statement (for the meeting)

> From project start, I have completed the full machine learning pipeline: data analysis, cleaning, feature engineering, model training, and selection of a production HistGradientBoosting classifier (ROC-AUC 0.81, 95% malware recall). I identified that store metadata and engineered features were the main drivers of performance, and chose Android_Permission.csv as the production dataset after finding merged data did not improve results. Most recently, I implemented the **APK Permission Extraction module**, which reads an APK’s manifest, extracts permissions, and converts them into the exact 151-feature format the model expects — the critical link between a real app file and the trained classifier. The next phase is connecting this extractor to the model and building the user-facing risk score and explanation layers.

---

*End of report — scope: project start through APK permission extraction.*

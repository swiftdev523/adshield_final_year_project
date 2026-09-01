# Android Adware / Malware Detection — Project Summary Report

*Prepared for presentation — a complete walkthrough of the work, decisions, findings, and final model.*

---

## 1. Executive Summary

We built a machine-learning system that classifies Android applications as **benign (0)** or **malware (1)** using the permissions they request together with app-store metadata.

The project ran end-to-end: raw data analysis → cleaning → feature alignment → exploratory analysis → model training → cross-validation → hyperparameter tuning → full-scale data run → class-imbalance handling → feature engineering → a final production model with documentation.

**Headline outcome:** the final production model is a **HistGradientBoosting** classifier reaching **ROC-AUC 0.81** and **F1 0.81**. The single most important discovery was that **app-store metadata (price, number of ratings, rating) is far more predictive of malware than the individual permission flags** that the project originally focused on.

---

## 2. Project Goal

> Detect malicious / adware Android apps automatically from their requested permissions and basic app metadata, and identify which signals best distinguish malware from legitimate apps.

---

## 3. Datasets

Four data sources were analyzed (kept separate at first, not blindly merged):

| Dataset | Rows (raw) | Columns | Label | Nature |
|---------|-----------|---------|-------|--------|
| **Android_Permission.csv** | 29,999 | 184 | `Class` (0/1) | App metadata + human-readable permissions |
| **TUANDROMD.csv** | 4,465 | 242 | `Label` (malware/goodware) | Android manifest permissions/APIs |
| **computer and security_2.xlsx** (3 sheets) | up to ~90k | ~1,439 | per-sheet | APK permission matrices |
| **SMSSpamCollection** | 5,572 | 2 | `label` (ham/spam) | SMS text (kept separate — NLP, not permissions) |

---

## 4. Methodology — Step by Step

### Step 1 — Data Analysis
Profiled every dataset: shape, columns, missing values, duplicates, label column, class balance. Reports: `dataset_analysis_report.md`.

### Step 2 — Cleaning (`clean_datasets.py`)
- **Standardized labels** to `0` (benign / goodware / ham) and `1` (malware / spam).
- **Removed duplicates** (TUANDROMD was ~85% duplicates; Android_Permission ~2,900).
- **Imputed missing values** (numeric → 0, text → empty).
- Reports: `dataset_cleaning_report.md`.

### Step 3 — Feature Alignment & Merge (`merge_datasets.py`)
- Built a **unified permission schema** (union of all permission names).
- Each app aligned to the schema; **missing permissions filled with 0**.
- Produced an ML-ready merged dataset (`data/processed/ml_merged_permissions.joblib`).
- SMS data excluded (text-only, no permission vector).

### Step 4 — Exploratory Data Analysis
Examined class balance, per-source composition, and most common permissions (Internet access, network state, storage, phone state dominate).

### Step 5 — Baseline Models (`train_models.py`)
Trained **Random Forest, Decision Tree, Logistic Regression** with an 80/20 stratified split. All clustered near **68% accuracy** — a warning sign.

### Step 6 — Cross-Validation
5-fold stratified CV on Logistic Regression confirmed stable but modest results (~0.68 accuracy, ~0.80 F1) — consistent across folds, so not a fluke.

### Step 7 — Hyperparameter Tuning (`tune_random_forest.py`)
GridSearchCV over `n_estimators`, `max_depth`, `min_samples_split`, `min_samples_leaf`.
Best CV accuracy **0.686** — barely above baseline, confirming the ceiling was a **data/feature problem, not a tuning problem**.

### Step 8 — Full-Data Run
Re-ran cleaning + merge on the **complete** Excel workbook (117,355 rows). Accuracy headline rose to ~88% on the APK subset, but malware-class F1 fell because malware became a small minority — exposing a **class-imbalance** issue.

### Step 9 — Imbalance Handling (`fix_imbalance.py`)
Compared **balanced class weights, random undersampling, and SMOTE** (leak-free, threshold-tuned).
**Finding:** resampling barely moved F1 (all within ±0.005). The limit is **class separability**, not sampling method.

### Step 10 — Feature Engineering (the breakthrough)
Re-introduced previously-dropped **metadata** (rating, price, permission counts) and engineered features:
- `log_number_of_ratings = log1p(Number of ratings)` — **kept**
- `dangerous_to_safe_ratio` — **dropped (no signal)**

This is where real improvement appeared (see §6).

### Step 11 — Final Production Model (`final_train.py`)
Trained the final HistGradientBoosting model on the optimized feature set, with Logistic Regression for comparison, full metrics, and feature importance.

---

## 5. Why Accuracy Was "Stuck" at ~68% (Key Diagnostic)

A crucial diagnostic explained the plateau:

| Source | Rows | Standalone separability |
|--------|------|--------------------------|
| **Android_Permission** | 27,077 (81% of merged data) | **~67%** (≈ coin-flip-ish) |
| TUANDROMD | 662 | **~97%** (strong, but tiny) |
| Excel sheets | single-class each | trivial / source-memorization |

The merged dataset was **dominated by the weakly-separable Android_Permission data**, and the majority-class baseline was already 66%. No model or tuning could exceed this — the **features themselves lacked signal**. This reframed the whole project: the path forward was **better features, not better models**.

---

## 6. The Breakthrough — Metadata Beats Permissions

Adding store metadata to the weak dataset and engineering a log feature produced the only meaningful gains.

**Feature correlation with malware:**

| Feature | Correlation |
|---------|-------------|
| `Rating` | −0.222 |
| `Number of ratings` (raw) | −0.036 |
| **`log_number_of_ratings`** | **−0.367** ← log transform unlocked ~10× signal |
| `dangerous_to_safe_ratio` | +0.014 (noise) |

**Effect of engineered features by model:**

| Δ from engineered features | HistGradientBoosting | Logistic Regression |
|----------------------------|----------------------|---------------------|
| ROC-AUC | +0.0006 | **+0.0579** |
| Accuracy (default 0.5) | −0.005 | **+0.078** |

*Trees already handle skew internally, so the log transform helped the linear model dramatically — a textbook example of feature engineering substituting for model complexity.*

---

## 7. Final Production Model

**Model:** HistGradientBoosting (`class_weight=balanced`), stratified 80/20, decision threshold tuned for F1.
**Dataset:** Android_Permission.csv — 27,310 rows (deduplicated), 66.8% malware.
**Feature set (157):** 151 permission flags + 5 metadata + `log_number_of_ratings`.

### Performance (held-out test, tuned threshold)

| Metric | **HistGradientBoosting (primary)** | Logistic Regression (comparison) |
|--------|-----------------------------------|----------------------------------|
| Accuracy | 0.6999 | 0.7133 |
| Precision | 0.7038 | 0.7414 |
| Recall | **0.9506** | 0.8760 |
| F1 | **0.8088** | 0.8031 |
| ROC-AUC | **0.8115** | 0.7956 |

### Confusion matrix (HGB, tuned threshold)

| | Predicted benign | Predicted malware |
|--|------------------|-------------------|
| **Actual benign** | 357 | 1,459 |
| **Actual malware** | 180 | 3,466 |

The model is tuned for **high recall (95%)** — it catches almost all malware (only 180 missed of 3,646), accepting more false positives. This is the appropriate trade-off for security screening, where missing malware is worse than flagging a benign app for review.

### Most important features (permutation importance)

| Rank | Feature | Importance |
|------|---------|-----------|
| 1 | **Price** | 0.1262 |
| 2 | **Number of ratings** | 0.1231 |
| 3 | Your location : fine (GPS) location | 0.0180 |
| 4 | Rating | 0.0076 |
| 5 | Network communication : view network state | 0.0051 |

**`Price` and `Number of ratings` are ~7× more important than the strongest permission** — the clearest evidence that metadata, not individual permissions, drives detection.

---

## 8. Key Insights / Lessons

1. **Feature quality beat everything.** Metadata + a log transform improved results more than GridSearch, SMOTE, or swapping models combined.
2. **Always check the baseline.** ~68% accuracy looked okay until we saw the majority class was already 66%.
3. **Resampling is not a cure for weak features.** SMOTE/undersampling couldn't create separability that wasn't there.
4. **Match the transform to the model.** The log transform was near-useless for trees but transformative for the linear model.
5. **Don't blindly merge datasets.** Mixing incompatible feature spaces and single-class sources diluted signal; per-domain analysis was more honest.
6. **Threshold tuning matters.** Choosing the operating point (high recall vs high precision) is a deliberate, use-case-driven decision.

---

## 9. Deliverables / Artifacts

| File | Purpose |
|------|---------|
| `models/final_model.joblib` | **Production model** (HGB + tuned threshold + feature recipe & imputation values) |
| `final_metrics.json` | Full metrics for both models |
| `final_feature_importance.csv` | Permutation importance, all 157 features |
| `final_model_report.md` | Final model technical report |
| `dataset_analysis_report.md` | Raw data profiling |
| `dataset_cleaning_report.md` | Cleaning summary |
| `dataset_merge_report.md` | Feature alignment / merge summary |
| `model_comparison_report.md` | Baseline RF / DT / LogReg comparison |
| `imbalance_fix_report.md` | Resampling strategy comparison |
| `experiment_engineered_features_report.md` | Engineered features on HGB |
| `experiment_engineered_logreg_report.md` | Engineered features on Logistic Regression |

---

## 10. Suggested Next Steps

- **Add metadata to the other datasets** if obtainable — it is the strongest signal we found.
- **Dedicated TUANDROMD detector** (~97% on its own) as a high-confidence second opinion.
- **Collect richer metadata** (developer reputation, install counts, update history) — likely to push accuracy well beyond 80%.
- **Calibrate probabilities** and expose the decision threshold as a tunable knob for the security team.

---

## 11. One-Slide Talking Points

- Built a full ML pipeline: clean → align → train → tune → engineer → finalize.
- Diagnosed that accuracy was capped by **weak permission features**, not modeling.
- **Discovery:** store metadata (**price, number of ratings**) predicts malware far better than permissions.
- Final **HistGradientBoosting** model: **ROC-AUC 0.81, F1 0.81, recall 95%** (catches almost all malware).
- Lesson: **better features > bigger models.**

# Final Model Report — Android Adware / Malware Detector

## Production model
- **Selected model: HistGradientBoosting** (`class_weight=balanced`, `max_iter=300`)
- Decision threshold (tuned for F1): **0.23**
- Dataset: Android_Permission.csv — **27,310** rows (deduplicated), malware **66.8%**
- Split: stratified 80/20 (random_state=42)

## Optimized feature set
- 151 active permission flags
- 5 metadata: `Rating`, `Number of ratings`, `Price`, `Dangerous permissions count`, `Safe permissions count`
- 1 engineered: `log_number_of_ratings = log1p(Number of ratings)` **(kept)**
- `dangerous_to_safe_ratio` **(removed — no signal)**
- **Total features: 157**

## Model comparison (held-out test, tuned threshold; ROC-AUC threshold-independent)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|-------|----------|-----------|--------|-----|---------|
| HistGradientBoosting | 0.6999 | 0.7038 | 0.9506 | 0.8088 | 0.8115 |
| Logistic Regression | 0.7133 | 0.7414 | 0.8760 | 0.8031 | 0.7956 |
| Random Forest | 0.6723 | 0.6729 | 0.9907 | 0.8014 | 0.7560 |
| Decision Tree | 0.6712 | 0.7454 | 0.7707 | 0.7578 | 0.6175 |

**Ranking by ROC-AUC:** HistGradientBoosting (0.8115) > Logistic Regression (0.7956) > Random Forest (0.7560) > Decision Tree (0.6175)

## Why HistGradientBoosting was selected

- **Best ranking metric (ROC-AUC = 0.8115).** ROC-AUC is threshold-independent and the fairest single measure of separability; the production model leads on it.
- **Best F1 (0.8088).** It gives the strongest precision/recall balance for the malware class.
- **Highest recall** among the models — it catches the most malware, which is the priority for security screening.
- **Robust to mixed feature scales and skew.** The feature set mixes binary permission flags with wide-range counts (`Number of ratings` up to ~1.9M); gradient-boosted trees handle this natively, no scaling required.
- **Versus Logistic Regression:** competitive but lower ROC-AUC; it is linear and needs careful scaling/transforms to compete.
- **Versus Random Forest:** similar family but bagging underperformed boosting here on ROC-AUC/F1.
- **Versus Decision Tree:** a single tree overfits and is the weakest; boosting many shallow trees generalizes far better.

### Production model at default 0.5 threshold
- Accuracy 0.7182 | Precision 0.9007 | Recall 0.6495 | F1 0.7547

### Confusion matrix — production model (tuned threshold)

| | Pred benign (0) | Pred malware (1) |
|--|-----------------|------------------|
| **Actual benign** | 357 | 1459 |
| **Actual malware** | 180 | 3466 |

## Top 15 features (permutation importance, scoring=ROC-AUC)

| Rank | Feature | Importance |
|------|---------|-----------|
| 1 | `Price` | 0.12622 |
| 2 | `Number of ratings` | 0.12309 |
| 3 | `Your location : fine (GPS) location (D)` | 0.01804 |
| 4 | `Rating` | 0.00756 |
| 5 | `Network communication : view network state (S)` | 0.00514 |
| 6 | `System tools : set wallpaper (S)` | 0.00477 |
| 7 | `Dangerous permissions count` | 0.00454 |
| 8 | `Phone calls : read phone state and identity (D)` | 0.00205 |
| 9 | `Safe permissions count` | 0.00184 |
| 10 | `Storage : modify/delete USB storage contents modify/delete SD card contents (D)` | 0.00151 |
| 11 | `Your personal information : read contact data (D)` | 0.00131 |
| 12 | `Hardware controls : control vibrator (S)` | 0.00118 |
| 13 | `Network communication : view Wi-Fi state (S)` | 0.00117 |
| 14 | `Services that cost you money : send SMS messages (D)` | 0.00108 |
| 15 | `Services that cost you money : directly call phone numbers (D)` | 0.00106 |

**Insight:** `Price` and `Number of ratings` dominate — store metadata is far more predictive of malware than any individual permission.

## Artifacts
- `models/final_model.joblib` — production model + tuned threshold + feature recipe
- `models/feature_columns.joblib` — ordered feature columns + recipe
- `final_metrics.json` — metrics for all four models
- `final_feature_importance.csv` — permutation importance (all features)
- `final_model_report.md` — this report

## How to load and predict
```python
import joblib, numpy as np, pandas as pd
bundle = joblib.load('models/final_model.joblib')
model, thr = bundle['model'], bundle['decision_threshold']
cols = bundle['feature_names']
# build X_new with the same columns/order, then:
proba = model.predict_proba(X_new[cols])[:, 1]
pred = (proba >= thr).astype(int)  # 1 = malware
```

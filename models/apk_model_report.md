# APK Model Metrics Report — Verified Held-Out Evaluation

**Model:** Random Forest (`adware_detection_rf_model.pkl`)  
**Mode:** APK Analysis Mode (permission-only, pre-install scanning)  
**Date verified:** June 2026 (local reproduction matches Google Colab)

---

## Purpose

This report documents the **honest, held-out performance** of the permission-only Random Forest model used for **APK Analysis Mode**. These are the numbers to present to your supervisor — not the earlier inflated in-sample figures.

---

## Dataset and methodology

| Item | Value |
|------|-------|
| Dataset | TUANDROMD.csv |
| Raw rows | 4,464 |
| **Unique rows (after de-duplication)** | **662** |
| Duplicates removed | 3,802 (85%) |
| Split | Stratified 80/20 (`random_state=42`) |
| Train set | 529 apps |
| **Held-out test set** | **133 apps** (26 malware, 107 benign) |
| Model | RandomForestClassifier, 241 permission features |

**Important:** TUANDROMD contains many duplicate rows. If duplicates are not removed before splitting, the same app can appear in both train and test, inflating accuracy to ~99%+. Your Colab run and our local verification both used **de-duplicated data**, which is why the honest score is **96.2%**, not 99%+.

---

## Held-out test results (present these)

| Metric | Value | Meaning |
|--------|-------|---------|
| **Accuracy** | **96.2%** | Correct on 96% of unseen apps |
| **Precision** | **92.0%** | When flagged as malware, correct 92% of the time |
| **Recall** | **88.5%** | Catches ~89 of every 100 actual malware apps |
| **F1-score** | **90.2%** | Balanced overall performance |
| **ROC-AUC** | **0.9804** | Strong ranking ability on unseen data |

### Confusion matrix (held-out test, n=133)

|  | Predicted benign | Predicted malware |
|--|----------------|-------------------|
| **Actual benign** | 105 | 2 |
| **Actual malware** | 3 | 23 |

- **2 false positives** — safe apps wrongly flagged  
- **3 false negatives** — malware missed  

---

## Verification

Local script `models/verify_holdout.py` reproduces your Colab results **exactly**:

| Metric | Colab | Local (held-out) | Match |
|--------|-------|------------------|-------|
| Accuracy | 0.9624… | 0.9624 | ✅ |
| Precision | 0.92 | 0.9200 | ✅ |
| Recall | 0.8846… | 0.8846 | ✅ |
| F1 | 0.9020… | 0.9020 | ✅ |

---

## Two-mode model summary (for presentation)

| Mode | Model | Dataset | Features | Held-out performance |
|------|-------|---------|----------|----------------------|
| **APK Analysis** (pre-install) | Random Forest | TUANDROMD | 241 permissions only | Acc **96.2%**, F1 **90.2%**, ROC-AUC **0.98** |
| **Installed App** (with metadata) | HistGradientBoosting | Android_Permission | 157 (permissions + metadata) | ROC-AUC **0.81**, F1 **0.81**, Recall **95%** |

Each mode uses the model suited to the data available at scan time.

---

## Limitations (be ready to mention)

1. **Small unique sample** — only 662 unique apps after de-duplication; test set has 26 malware cases. Metrics are honest but confidence intervals would be wider than a large dataset.
2. **Permission-only** — APK mode cannot use store metadata (rating, price); that is intentional and correct for pre-install scanning.
3. **TUANDROMD permission schema** — 241 features; some modern permissions may not be in the training schema and will be ignored (mapped to 0).

---

## How to reproduce

```bash
python models/verify_holdout.py
```

Metrics are also saved in `models/apk_model_metrics.json`.

---

*End of report.*

# Project Study Guide — Android Adware Detection System

Use this document to prepare for your supervisor meeting. It covers **what exists**, **how it fits together**, and **what to say**.

---

## 1. The big picture (30-second version)

You are building a **mobile security system** that detects dangerous Android apps using:

1. **Permissions** (from APK manifest or installed app)
2. **Machine learning** (two models for two situations)
3. **Risk score 0–100** + **Safe / Suspicious / High Risk**
4. **Plain-English explanations** (rule-based, no LLM)

The backend is **working**. The Android app is **not built yet**.

---

## 2. Two analysis modes (memorise this)

| | **APK Analysis Mode** | **Installed App Mode** |
|--|------------------------|-------------------------|
| **When** | Before install (user has `.apk` file) | App already on device / on Play Store |
| **Data available** | Permissions only | Permissions + rating, price, ratings count |
| **Model** | Random Forest (`adware_detection_rf_model.pkl`) | HistGradientBoosting (`final_model.joblib`) |
| **Features** | 241 raw permission names | 157 (151 permissions + 5 metadata + 1 engineered) |
| **Dataset trained on** | TUANDROMD (662 unique apps) | Android_Permission (27,310 apps) |
| **Held-out performance** | Acc **96.2%**, F1 **90.2%**, ROC-AUC **0.98** | ROC-AUC **0.81**, F1 **0.81**, Recall **95%** |
| **API endpoint** | `POST /analyze/apk` | `POST /predict-apk` |

**Why two models?** An APK file has **no Play Store rating or price**. The old production model needed that metadata, so it could not truly scan APKs before install. The Random Forest fixes that.

---

## 3. Codebase map — what each part does

```
android adware detection system1/
│
├── final_train.py              ← TRAINING: builds Installed App Mode model
├── final_metrics.json          ← Metrics for 4 models compared during training
├── final_model_report.md       ← Full report on HistGradientBoosting selection
├── final_feature_importance.csv← Which features matter most (Price, ratings top)
│
├── models/                     ← ALL SAVED MODELS
│   ├── final_model.joblib           ★ Installed App Mode (HGB + threshold + recipe)
│   ├── feature_columns.joblib       ★ Column names + recipe for 157 features
│   ├── adware_detection_rf_model.pkl ★ APK Mode (241 permissions)
│   ├── apk_model_metrics.json       ★ Verified held-out APK model metrics
│   ├── apk_model_report.md          ★ Writeup for supervisor
│   ├── verify_holdout.py            Reproduce 96.2% held-out evaluation
│   ├── notification_spam_model_v2.joblib   SMS spam classifier (not in API yet)
│   ├── notification_vectorizer_v2.joblib   TF-IDF for spam model
│   ├── notification_threshold.json         Tuned threshold = 0.29
│   └── testing_notification_model.py       Quick test script for spam model
│
├── backend/                    ← RUNNING WEB SERVICE
│   ├── requirements.txt
│   ├── apk_analysis/           ← APK PERMISSION EXTRACTION (no ML here)
│   │   ├── permission_extractor.py  Parse APK → permissions → feature vector
│   │   ├── permission_mapping.py    android.permission.SEND_SMS → dataset label
│   │   └── feature_schema.py      Loads 151 column names from feature_columns.joblib
│   │
│   └── app/                    ← FASTAPI BACKEND
│       ├── main.py                  App entry + /health
│       ├── config.py                Model paths, thresholds, risk bands
│       ├── api/routes_predict.py    POST /predict-apk, POST /analyze/apk
│       ├── schemas/predict.py       Request/response validation (Pydantic)
│       └── services/
│           ├── model_service.py         Installed App Mode scoring
│           ├── apk_model_service.py     APK Mode scoring
│           ├── risk_score.py            Probability → 0-100 → tier
│           ├── explanation_service.py   Rule-based human explanations
│           └── permission_catalog.py    Permission → friendly phrase + severity
│
├── data/
│   ├── datasets/               ← RAW DATA
│   │   ├── Android_Permission.csv   ★ Production training data
│   │   ├── TUANDROMD.csv            ★ APK model training data
│   │   ├── computer and security_2.xlsx  (experimental merge)
│   │   └── sms_spam_collection/     Notification spam training
│   └── processed/              ← Cleaned/merged (experimental, not production)
│
└── Reports (for presentations)
    ├── SUPERVISOR_PROGRESS_REPORT.md
    ├── PROJECT_SUMMARY_REPORT.md
    └── PRESENTATION_PROGRESS_REPORT.md
```

★ = most important files to know

---

## 4. How a request flows (study this diagram)

### APK Analysis Mode (`POST /analyze/apk`)

```
User sends: { "permissions": ["android.permission.SEND_SMS", ...] }
                    │
                    ▼
        apk_model_service.py
        • Maps SEND_SMS → model's 241 features
        • Random Forest → P(malware)
                    │
                    ▼
        risk_score.py
        • P(malware) → score 0-100
        • 0-30 Safe | 31-70 Suspicious | 71-100 High Risk
                    │
                    ▼
        permission_extractor.py (for counts)
        • dangerous_permission_count, safe_permission_count
                    │
                    ▼
        explanation_service.py
        • "This app requests SMS access and startup permissions..."
                    │
                    ▼
        JSON response: risk_score, prediction, explanation, reasons
```

### Installed App Mode (`POST /predict-apk`)

```
User sends: { "features": { permission labels → 0/1 }, "metadata": { rating, price, ... } }
                    │
                    ▼
        model_service.py
        • Builds full 157-column row (missing metadata → training medians)
        • HistGradientBoosting → P(malware)
                    │
                    ▼
        risk_score.py + explanation_service.py  (same as above)
```

---

## 5. Key files to open and read (in order)

| Order | File | Why read it |
|-------|------|-------------|
| 1 | `backend/app/config.py` | All paths and thresholds in one place |
| 2 | `backend/app/api/routes_predict.py` | The two API endpoints |
| 3 | `backend/app/services/apk_model_service.py` | How APK Mode scoring works |
| 4 | `backend/app/services/model_service.py` | How Installed Mode scoring works |
| 5 | `backend/app/services/risk_score.py` | Score 0-100 logic |
| 6 | `backend/app/services/explanation_service.py` | How explanations are generated |
| 7 | `backend/apk_analysis/permission_extractor.py` | APK → permissions pipeline |
| 8 | `models/apk_model_report.md` | Verified metrics for APK model |
| 9 | `final_model_report.md` | Verified metrics for Installed model |
| 10 | `final_train.py` | How the production model was trained |

---

## 6. Numbers to remember for the meeting

### APK Mode (Random Forest — pre-install)
- **Accuracy 96.2%** | Precision 92% | Recall 88.5% | F1 90.2% | ROC-AUC 0.98
- Held-out test (133 apps, 26 malware) — **honest, verified**
- TUANDROMD: 662 **unique** apps after removing 85% duplicates

### Installed App Mode (HistGradientBoosting)
- **ROC-AUC 0.81** | F1 0.81 | Recall **95%** (catches most malware)
- 27,310 apps, 157 features
- Top predictors: **Price**, **Number of ratings**, then permissions

### Notification spam (separate, not in API yet)
- Random Forest + TF-IDF on SMS data
- ~99.7% accuracy on SMS corpus (threshold 0.29)
- Accuracy **not** the same task as app malware detection

---

## 7. Important concepts (supervisor may ask)

### What is AndroidManifest.xml?
The config file inside every APK listing **permissions** and app identity. Your extractor reads it (binary XML via `pyaxmlparser`).

### What is a held-out test set?
Data the model **never saw during training**. Your 96.2% is held-out (good). Earlier 99%+ numbers were in-sample or had duplicate leakage (bad to present).

### Why not one model for everything?
Store metadata (rating, price) **does not exist inside an APK**. Pre-install scanning must use **permissions only**.

### What is feature engineering?
Creating new inputs from raw data. Example kept: `log_number_of_ratings = log1p(Number of ratings)`.

### What is the explanation engine?
**Rule-based** (not AI chatbot): checks dangerous permission **combinations** and outputs sentences like *"SMS + auto-start = common adware pattern"*.

---

## 8. How to run and demo

### Start the API server
```bash
cd "d:\beeeen\android adware detection system1"
python -m uvicorn backend.app.main:app --reload
```
Open: http://127.0.0.1:8000/docs

### Test endpoints in Swagger
- **POST /analyze/apk** — send permission list (APK Mode)
- **POST /predict-apk** — send feature dict + optional metadata (Installed Mode)
- **GET /health** — confirms models loaded

### Reproduce APK model metrics
```bash
python models/verify_holdout.py
```

### Test notification spam model
```bash
cd models
python testing_notification_model.py
```

---

## 9. What is NOT done yet

| Feature | Status |
|---------|--------|
| APK **file upload** (parse `.apk` on server) | ❌ Not built — only permission list input |
| Notification spam **API** | ❌ Model exists, not wired |
| Installed app endpoint with install source | ❌ |
| Android mobile app | ❌ |
| Guardian Mode UI | ❌ |
| Dynamic analysis models (`large_dataset_*`) | ❌ Parked — need runtime data |

---

## 10. Suggested talking points for the meeting

1. **Problem:** Detect adware/malware from Android app permissions before and after install.

2. **Approach:** Two-mode architecture — permission-only model for APKs, metadata-rich model for installed apps.

3. **ML results:** APK model 96.2% held-out accuracy; Installed model 81% ROC-AUC with 95% recall.

4. **Backend built:** Extraction, scoring, risk tiers, explanations — live API with two endpoints.

5. **Key insight:** Merging all datasets did not help; feature quality and correct mode-specific models matter more.

6. **Next:** APK file upload endpoint, notification spam API, then Android app.

---

## 11. Quick self-test (quiz yourself)

1. Name the two models and when each is used.
2. Why does APK Mode not use Price/Rating?
3. What does `POST /analyze/apk` accept and return?
4. What are the three risk tiers and score ranges?
5. Why is 96.2% more trustworthy than 99.6%?
6. What file trains the Installed App Mode model?
7. Where are explanations generated — which service?

**Answers:** (1) RF for APK, HGB for installed. (2) Not in APK file. (3) Permissions list → score, tier, explanation. (4) Safe 0-30, Suspicious 31-70, High Risk 71-100. (5) Held-out vs in-sample/duplicate leakage. (6) `final_train.py`. (7) `explanation_service.py`.

---

*Good luck with your meeting.*

"""Held-out verification for the APK Analysis Mode model.

Goal: confirm the reported ~96% held-out result is reproducible with the same
modeling approach (standard RandomForest) on the same data (TUANDROMD, 241
permission features) and a clean, unseen 20% test split.

Note on methodology:
- The wired-in model (adware_detection_rf_model.pkl) was trained on the FULL
  TUANDROMD, so evaluating *it* on any TUANDROMD row is in-sample. We therefore
  train a FRESH RandomForest on 80% and test on the held-out 20% — an honest
  estimate of how this model family generalises to unseen apps.
- For reference we also show the pre-trained model on the same 20% (in-sample,
  expected to look optimistic).
"""
import warnings
warnings.filterwarnings("ignore")
import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix,
)

HERE = Path(__file__).resolve().parent
RANDOM_STATE = 42

# Use the wired-in model's exact feature order for an apples-to-apples setup.
wired = joblib.load(HERE / "adware_detection_rf_model.pkl")
cols = list(wired.feature_names_in_)

df = pd.read_csv(HERE.parent / "data" / "datasets" / "TUANDROMD.csv").dropna(subset=["Label"])
print(f"raw rows: {len(df)}")
# TUANDROMD is known to contain many duplicate rows. If not removed before the
# split, identical rows leak into both train and test and inflate the score.
before = len(df)
df = df.drop_duplicates().reset_index(drop=True)
print(f"after drop_duplicates: {len(df)} (removed {before - len(df)} duplicates)")

y = df["Label"].astype(str).str.lower().map(lambda v: 1 if v in ("malware", "1", "1.0") else 0).values
X = pd.DataFrame(0, index=df.index, columns=cols)
for c in cols:
    if c in df.columns:
        X[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int).values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
)
print(f"Dataset: {len(y)} apps | train {len(y_train)} / test {len(y_test)} "
      f"| malware in test: {int(y_test.sum())}/{len(y_test)}")


def report(name, proba, pred):
    print(f"\n{name}")
    print(f"  Accuracy : {accuracy_score(y_test, pred):.4f}")
    print(f"  Precision: {precision_score(y_test, pred, zero_division=0):.4f}")
    print(f"  Recall   : {recall_score(y_test, pred, zero_division=0):.4f}")
    print(f"  F1-score : {f1_score(y_test, pred, zero_division=0):.4f}")
    print(f"  ROC-AUC  : {roc_auc_score(y_test, proba):.4f}")
    print(f"  Confusion matrix [[TN FP][FN TP]]: {confusion_matrix(y_test, pred).tolist()}")


# 1) FRESH model trained only on the 80% -> honest held-out estimate.
fresh = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1)
fresh.fit(X_train, y_train)
report("[HELD-OUT] Fresh RandomForest trained on 80%, tested on unseen 20%",
       fresh.predict_proba(X_test)[:, 1], fresh.predict(X_test))

# 2) Reference: the pre-trained wired-in model on the same 20% (in-sample,
#    and the wired model also saw these dedup'd rows during its full-data train).
report("[REFERENCE/in-sample] Wired-in adware_detection_rf_model.pkl on the 20%",
       wired.predict_proba(X_test)[:, 1], wired.predict(X_test))

"""Tune the decision threshold for the notification spam model.

The model scores messages well (spam scores high, ham scores low) but the
default 0.5 cutoff misses borderline spam. This script sweeps thresholds against
the labelled SMS dataset, selects the threshold that maximises spam-detection
F1, saves it to ``notification_threshold.json``, and verifies the result.

Note: the model was trained externally (Colab) so we don't have its exact
held-out split; the sweep runs on the full labelled set. This is fine for
choosing an operating point, but treat the reported metrics as in-sample.
"""

import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import joblib
import numpy as np
from sklearn.metrics import precision_recall_fscore_support

HERE = Path(__file__).resolve().parent
DATASET = HERE.parent / "data" / "sms_spam_collection" / "SMSSpamCollection"
THRESHOLD_OUT = HERE / "notification_threshold.json"


def load_dataset():
    labels, texts = [], []
    with open(DATASET, encoding="utf-8") as fh:
        for line in fh:
            if "\t" not in line:
                continue
            label, text = line.rstrip("\n").split("\t", 1)
            labels.append(1 if label.strip().lower() == "spam" else 0)
            texts.append(text)
    return np.array(labels), texts


def main():
    model = joblib.load(HERE / "notification_spam_model_v2.joblib")
    vectorizer = joblib.load(HERE / "notification_vectorizer_v2.joblib")

    y, texts = load_dataset()
    proba = model.predict_proba(vectorizer.transform(texts))[:, 1]

    # Sweep thresholds and keep the one with the best spam F1.
    best = None
    for t in np.round(np.linspace(0.05, 0.95, 91), 2):
        pred = (proba >= t).astype(int)
        p, r, f1, _ = precision_recall_fscore_support(
            y, pred, average="binary", pos_label=1, zero_division=0
        )
        if best is None or f1 > best["f1"]:
            best = {"threshold": float(t), "precision": float(p), "recall": float(r), "f1": float(f1)}

    # Metrics at the default 0.5 for comparison.
    pred_default = (proba >= 0.5).astype(int)
    p0, r0, f0, _ = precision_recall_fscore_support(
        y, pred_default, average="binary", pos_label=1, zero_division=0
    )

    print(f"Dataset: {len(y)} messages ({int(y.sum())} spam / {int((1 - y).sum())} ham)")
    print(f"Default 0.50 -> precision {p0:.3f} | recall {r0:.3f} | F1 {f0:.3f}")
    print(f"Best   {best['threshold']:.2f} -> precision {best['precision']:.3f} "
          f"| recall {best['recall']:.3f} | F1 {best['f1']:.3f}")

    # Verify on the four sample messages.
    samples = [
        "Congratulations! You have won $1000. Click here now.",
        "URGENT! Claim your free prize now.",
        "Meeting starts at 10am tomorrow.",
        "Don't forget to bring your laptop.",
    ]
    sp = model.predict_proba(vectorizer.transform(samples))[:, 1]
    print("\nSample checks at tuned threshold:")
    for text, pr in zip(samples, sp):
        verdict = "SPAM" if pr >= best["threshold"] else "HAM"
        print(f"  {pr:.3f} -> {verdict:4} | {text}")

    THRESHOLD_OUT.write_text(json.dumps(best, indent=2), encoding="utf-8")
    print(f"\nSaved tuned threshold to {THRESHOLD_OUT.name}")


if __name__ == "__main__":
    main()

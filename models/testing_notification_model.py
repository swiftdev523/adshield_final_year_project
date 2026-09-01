import json
from pathlib import Path

import joblib

MODELS_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODELS_DIR / "notification_spam_model_v2.joblib"
VECTORIZER_PATH = MODELS_DIR / "notification_vectorizer_v2.joblib"
THRESHOLD_PATH = MODELS_DIR / "notification_threshold.json"


def main() -> None:
    print("Script started")
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)

    # Tuned decision threshold (from tune_notification_threshold.py). Falls
    # back to 0.5 if the file is missing.
    try:
        with THRESHOLD_PATH.open(encoding="utf-8") as fh:
            threshold = float(json.load(fh)["threshold"])
    except FileNotFoundError:
        threshold = 0.5

    sample = ["Congratulations! You have won a free iPhone. Click here now!"]
    X = vectorizer.transform(sample)
    probability = model.predict_proba(X)[0][1]
    prediction = 1 if probability >= threshold else 0

    print("Threshold:", threshold)
    print("Prediction:", prediction)
    print("Spam Probability:", probability)


if __name__ == "__main__":
    main()

# CICMalDroid Category Classifier — Offline Experiment

This directory is intentionally isolated from the production FastAPI application and existing binary malware detectors.

Run the reproducible experiment from the project root:

```powershell
python models/category_experimental/train_category_poc.py
```

The script uses only static permission values from `feature_vectors_static.csv`. It reads only the `Class` columns from the accompanying five-category files to validate the documented positional label assumption. Syscall and Binder values are never model inputs.

The generated `report.md`, `metrics.json`, ordered `permission_features.json`, split manifests, prediction-probability CSVs, confusion matrices, and experimental model bundles remain inside this directory. Nothing here is referenced by `backend/app/config.py`.

Important: the installed environment currently has scikit-learn 1.6.0 while the backend pins 1.6.1. These artifacts are proof-of-concept outputs, not production integration artifacts.

# CICMalDroid final validation phase

This directory preserves the isolated offline model-selection and validation
evidence for the category classifier. It preserves `models/category_experimental`
as historical POC evidence and performs package-grouped model-family selection
under scikit-learn 1.6.1.

Run from the project root:

```powershell
& ".runtime\category-final-venv\Scripts\python.exe" "models\category_final_validation\run_final_validation.py"
```

The script writes generated evidence to `artifacts/` and the human-readable
result to `REPORT.md`.

Verify the completed artifacts without retraining:

```powershell
& ".runtime\category-final-venv\Scripts\python.exe" "models\category_final_validation\verify_validation_outputs.py"
```

Important: the current CICMalDroid corpus has no package groups for Banking
Malware or SMS Malware that were absent from all historical POC partitions.
The script therefore refuses to claim or score a fresh four-class holdout. Its
exported model remains explicitly provisional.

## Experimental backend sidecar

The unchanged provisional Random Forest is now used by an **experimental
selective category sidecar** in the backend. This does not revise the historical
validation result or make the model production-validated:

- It runs only after the existing raw-permission APK binary detector returns
  `Malicious`.
- It accepts a supported category only when the raw top-two class-score margin
  is at least the locked threshold `0.70`; otherwise it returns `Uncertain`.
- Its raw class scores are not calibrated probabilities or confidence.
- It cannot change the binary verdict, malware probability, risk score, or risk
  level.
- It is backend-only; the frontend does not display raw category model values.
- New independently labelled and source-disjoint validation data is still
  required before any production claim or broader integration.

The frozen rule and development evidence are under `abstention_analysis/`.
Runtime behavior is documented in
`backend/EXPERIMENTAL_CATEGORY_CLASSIFIER.md`. Historical reports, manifests,
and the saved model bundle remain unchanged as hash-verified evidence.

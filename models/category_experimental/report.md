# CICMalDroid 2020 Static-Permission Category Classifier — Offline POC

## Scope

This is an isolated secondary classifier experiment. It does not replace or modify the existing benign/malware detectors, and it is not connected to FastAPI.

Only static Android permission features are model inputs. The syscall/Binder files were read only for their `Class` columns to validate positional labels; no dynamic value entered training or prediction.

## Dataset preparation

- Final ordered permission features: **153**
- Static rows: **11,598**
- Cross-label packages excluded: **18** (264 rows across all five classes)
- Benign samples were excluded before modeling because this classifier is gated behind the existing malicious decision.
- Duplicate encoded/plain permission columns were collapsed with logical OR after converting positive numeric/boolean values to presence.
- Package names were used only for conflict detection and split grouping, never as model features.

### Clean malicious rows available before cohort capping

| Category | Rows |
|---|---:|
| Adware | 1,250 |
| Banking Malware | 2,037 |
| SMS Malware | 3,757 |
| Riskware | 2,499 |

### Label-alignment assumption

feature_vectors_static.csv contains no label or hash. Labels are attached by row position because the static matrix and both accompanying 5-category files have exactly 11,598 rows, both Class vectors match row-for-row, and their contiguous class runs exactly match the category counts and order published for CICMalDroid 2020. This is strong positional evidence, not an independently keyed hash join.

The assertion is strong but positional: the static CSV has no hash or label field, so it is not an independently keyed join.

## Splits and balancing

The full cleaned malicious dataset was group-stratified by package before downsampling. Missing packages were treated as unique row groups. Each already assigned partition was then sampled round-robin across package groups with a maximum of 8 rows per package, so balancing could not move a package between splits or let one repeated package dominate a category.

| Split | Adware | Banking Malware | SMS Malware | Riskware | Total |
|---|---:|---:|---:|---:|---:|
| Train | 600 | 600 | 600 | 600 | 2,400 |
| Validation | 200 | 200 | 200 | 200 | 800 |
| Test | 200 | 200 | 200 | 200 | 800 |

No oversampling or SMOTE was used.

## Model comparison

The winner was selected on **validation macro-F1**, with balanced accuracy and worst-class recall as tie-breakers. Accuracy was not a selection criterion.

### Validation

| Model | Macro F1 | Weighted F1 | Balanced Accuracy | Accuracy (context only) | Worst-class Recall |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.9149 | 0.9149 | 0.9150 | 0.9150 | 0.8750 |
| Random Forest | 0.9252 | 0.9252 | 0.9250 | 0.9250 | 0.9000 |
| HistGradientBoosting | 0.9276 | 0.9276 | 0.9275 | 0.9275 | 0.9050 |

### Held-out test

| Model | Macro F1 | Weighted F1 | Balanced Accuracy | Accuracy (context only) | Worst-class Recall |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.8875 | 0.8875 | 0.8875 | 0.8875 | 0.8500 |
| Random Forest | 0.9288 | 0.9288 | 0.9287 | 0.9287 | 0.9000 |
| HistGradientBoosting | 0.9017 | 0.9017 | 0.9012 | 0.9012 | 0.8900 |

## Selected baseline

**HistGradientBoosting** was selected because it had the strongest validation macro-F1 (0.9276). Its validation balanced accuracy was 0.9275, and its held-out test macro-F1 was 0.9017.

**Important holdout note:** Random Forest produced the highest held-out test macro-F1 (0.9288), above the formal validation-selected model. The test set was not used to change the winner after observation. This disagreement indicates single-split model-selection uncertainty and is a reason to require repeated package-grouped cross-validation before integration.

## Per-class held-out test results — selected model

| Category | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Adware | 0.8916 | 0.9050 | 0.8983 | 200 |
| Banking Malware | 0.8436 | 0.8900 | 0.8662 | 200 |
| SMS Malware | 0.9634 | 0.9200 | 0.9412 | 200 |
| Riskware | 0.9128 | 0.8900 | 0.9013 | 200 |

## Confusion matrix — selected model, held-out test

| Actual \ Predicted | Adware | Banking Malware | SMS Malware | Riskware |
|---|---:|---:|---:|---:|
| Adware | 181 | 11 | 1 | 7 |
| Banking Malware | 8 | 178 | 4 | 10 |
| SMS Malware | 4 | 12 | 184 | 0 |
| Riskware | 10 | 10 | 2 | 178 |

## Most frequent category confusions

- Banking Malware ↔ Riskware: **20** total errors
- Adware ↔ Banking Malware: **19** total errors
- Adware ↔ Riskware: **17** total errors

## Probability/confidence summary — selected model, held-out test

- Mean maximum predicted probability: **0.9500**
- Median maximum predicted probability: **0.9979**
- Mean probability assigned to the true class: **0.8866**
- Errors with confidence ≥ 0.80: **47**
- Errors with confidence ≥ 0.90: **31**

These are uncalibrated model confidence values under a balanced experimental prior; they must not be presented as real-world malware-category prevalence probabilities.

## Limitations

1. Static-to-label linkage is positional, not a hash-keyed join.
2. The experiment uses only manifest-reproducible permission features, discarding richer static CICMalDroid signals.
3. Package grouping reduces leakage but cannot prove that different packages are not repackaged copies; hashes are absent from the static CSV.
4. Two known cross-labelled raw-APK hashes cannot be mapped back to static rows and therefore cannot be explicitly removed here.
5. CICMalDroid samples are historical and cover only Adware, Banking Malware, SMS Malware, and Riskware for this secondary task.
6. A balanced cohort changes the class prior, so predicted probabilities are not calibrated for deployment.
7. This run used scikit-learn 1.6.0, while the backend currently pins 1.6.1; retraining or compatibility verification under the pinned environment is required before integration.

## Technical integration assessment

The feature interface is technically compatible with `ExtractionResult.raw_permissions`: inference can build a binary row by checking each ordered `android.permission.*` feature against the extractor's returned permission set. The saved feature-list hash guards ordering.

The model is **proof-of-concept suitable at the interface level, but not production-ready** because of the positional-label assumption, historical dataset, uncalibrated balanced probabilities, and scikit-learn patch-version mismatch. No FastAPI integration was performed.

## Reproduction

```powershell
python models/category_experimental/train_category_poc.py
```

# Final supplementary holdout evaluation

## Outcome

The predeclared FYP experimental-integration criterion **NOT PASSED**.

This criterion is a project-specific experimental prototype heuristic. It is **not** a production-security certification threshold.

## Immutable pre-prediction checks

- Model SHA-256: `9b2f3b2a880372ff077fdc37e6e3d7909c9ba3ba28cabce371a58d1f6b80f3b9`
- Runtime scikit-learn: `1.6.1`
- Model input features: `153`
- Ordered feature-contract SHA-256: `7aecf3b202c88d707e458a3705b4e3a326a9ee062c9b1e0f209a6b9a5c087c34`
- `model.classes_`: `[0, 1, 2, 3]`
- Verified class mapping: `0=Adware, 1=Banking Malware, 2=SMS Malware, 3=Riskware`
- All frozen holdout hashes matched before prediction: `true`

## Overall metrics

Frozen holdout composition: **196 total samples; 49 per category**.

| Metric | Value |
|---|---:|
| Accuracy | 0.806122 |
| Macro F1 (primary) | 0.794577 |
| Weighted F1 | 0.794577 |
| Balanced accuracy | 0.806122 |

## Per-class results

| Category | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Adware | 0.796610 | 0.959184 | 0.870370 | 49 |
| Banking Malware | 0.766667 | 0.469388 | 0.582278 | 49 |
| SMS Malware | 0.976190 | 0.836735 | 0.901099 | 49 |
| Riskware | 0.723077 | 0.959184 | 0.824561 | 49 |

## Confusion matrix

Rows are actual categories; columns are predicted categories.

| Actual / predicted | Adware | Banking Malware | SMS Malware | Riskware |
|---|---:|---:|---:|---:|
| Adware | 47 | 1 | 0 | 1 |
| Banking Malware | 11 | 23 | 1 | 14 |
| SMS Malware | 0 | 5 | 41 | 3 |
| Riskware | 1 | 1 | 0 | 47 |

## Banking and SMS recall

- Banking Malware recall: **0.469388**
- SMS Malware recall: **0.836735**

## Repeated grouped-CV comparison

The supplementary holdout Macro F1 is `0.794577`. The previously reported repeated grouped-CV Random Forest Macro F1 was `0.914532`.

Holdout minus repeated-CV Macro F1: `-0.119955` (-11.9955 percentage points).

This is a descriptive comparison only; no statistical-significance claim is made.

## Predeclared experimental-integration criterion

- Macro F1 >= 0.80: `false`
- Recall >= 0.70 for every supported category: `false`
- Lowest category recall: `0.469388`
- Overall decision: **NOT PASSED**

Passing this heuristic supports experimental prototype integration only. It does not certify production malware-detection safety or security.

## Raw probability diagnostics

`final_predictions.csv` contains raw `predict_proba` outputs. They are uncalibrated research diagnostics, conditional on the upstream detector and the true category being one of the four supported classes. They are not calibrated confidence values and must not be presented to users as confidence.

## Limitations

- The holdout contains only 49 packages per class; one additional error changes a class recall by about 2.04 percentage points.
- The balanced 49/49/49/49 class distribution is an evaluation design and does not represent real-world malware-family prevalence.
- This is a within-CICMalDroid supplementary holdout with mixed static-source and Kali APK-extraction provenance, not a fully independent external dataset.
- Adware/Riskware labels rely on documented positional alignment; Banking/SMS labels are inherited from audited source folders rather than independent multi-engine family adjudication.
- Only Banking and SMS samples have linkable APK SHA-256 evidence, covering 98 of 196 holdout samples.
- Package-disjoint grouping cannot prove that differently named packages are not repackaged or closely related variants.
- The model uses only 153 static permission-presence features and cannot observe code behavior, payloads, URLs, runtime actions, or other static structures.
- The classifier is closed-set: unsupported malware families are forced into one of Adware, Banking Malware, SMS Malware, or Riskware.
- Raw probabilities are uncalibrated and conditional on the upstream binary detector already classifying the application as malicious.
- This one-time holdout must not be reused for model, threshold, feature, or hyperparameter selection.

## Non-actions

- No retraining, calibration, threshold change, tuning, or sample reselection occurred.
- The selected Random Forest and frozen holdout artifacts were not modified.
- No FastAPI integration was performed.
- This holdout must not be reused to choose a changed model.

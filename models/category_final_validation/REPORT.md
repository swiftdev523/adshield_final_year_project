# CICMalDroid final model-selection and validation report

## Outcome

Repeated grouped CV selected **Random Forest** using the precommitted one-standard-error stability rule. The historical test results were not used to select or change the family.

A strict fresh four-class package-unseen holdout could not be created: the current corpus contains zero never-used Banking Malware packages and zero never-used SMS Malware packages. No replacement holdout was manufactured, and no fresh-holdout score or confusion matrix is reported.

**Integration is not yet justified**, regardless of the CV result. New independently labelled Banking and SMS packages compatible with the 153-permission schema are required.

## Historical POC preserved

The existing POC files were hash-verified before and after this run. Its selection remains HistGradientBoosting on validation Macro F1. Random Forest's higher old test score remains reporting-only and did not retroactively alter that decision.

| Model | Historical validation Macro F1 | Historical test Macro F1 |
|---|---:|---:|
| Logistic Regression | 0.91493458 | 0.88750240 |
| Random Forest | 0.92519556 | 0.92884022 |
| HistGradientBoosting | 0.92763547 | 0.90172134 |

## Development protocol

- scikit-learn: `1.6.1` (exact backend pin matched)
- Ordered static permission features: 153
- Cohort: 3,516 rows (879 per class)
- Composition: 3,008 named historical train/validation rows plus 508 unused named rows from the same development package universe
- Blank-package rows excluded because package isolation cannot be verified: 192
- Package cap: 8 rows per normalized package
- Cross-validation: 5 repeats x 5 folds of StratifiedGroupKFold
- Package identifiers were stripped and case-folded for conservative grouping; package is not a model feature
- Every historical test package was quarantined in full, including its unused rows
- No SMOTE, no oversampling, no syscall features, and no Binder features

## Repeated grouped cross-validation

Metrics below are the mean and sample standard deviation across five complete repeat-level OOF predictions; each row is scored exactly once per repeat.

| Model | Mean Macro F1 | SD | Mean balanced accuracy | SD | Mean worst-class recall |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.888235 | 0.003955 | 0.888680 | 0.003872 | 0.816610 |
| Random Forest | 0.914532 | 0.002646 | 0.914676 | 0.002568 | 0.853242 |
| HistGradientBoosting | 0.908447 | 0.001534 | 0.908305 | 0.001486 | 0.858931 |

### Per-class precision and recall across repeats

These are repeated-CV diagnostics, not fresh-holdout estimates.

| Model / class | Precision mean +/- SD | Recall mean +/- SD |
|---|---:|---:|
| Logistic Regression / Adware | 0.874929 +/- 0.006303 | 0.930830 +/- 0.002833 |
| Logistic Regression / Banking Malware | 0.853600 +/- 0.008999 | 0.816610 +/- 0.012525 |
| Logistic Regression / SMS Malware | 0.934138 +/- 0.010876 | 0.937201 +/- 0.009996 |
| Logistic Regression / Riskware | 0.891615 +/- 0.005833 | 0.870080 +/- 0.005933 |
| Random Forest / Adware | 0.884839 +/- 0.002248 | 0.959727 +/- 0.001904 |
| Random Forest / Banking Malware | 0.886122 +/- 0.007694 | 0.853242 +/- 0.007589 |
| Random Forest / SMS Malware | 0.968463 +/- 0.007744 | 0.942662 +/- 0.005890 |
| Random Forest / Riskware | 0.922404 +/- 0.003592 | 0.903072 +/- 0.004649 |
| HistGradientBoosting / Adware | 0.899900 +/- 0.003914 | 0.934699 +/- 0.004593 |
| HistGradientBoosting / Banking Malware | 0.856807 +/- 0.004917 | 0.858931 +/- 0.005688 |
| HistGradientBoosting / SMS Malware | 0.963962 +/- 0.003435 | 0.931058 +/- 0.004593 |
| HistGradientBoosting / Riskware | 0.915009 +/- 0.004930 | 0.908532 +/- 0.004800 |

## Selection decision

- Raw mean-Macro-F1 leader: **Random Forest**
- One-standard-error threshold: 0.913349
- Eligible families: Random Forest
- Selected family: **Random Forest**
- Selected mean Macro F1: 0.914532
- Selected Macro-F1 SD: 0.002646

Highest mean repeat-level OOF Macro F1 defines the leader. Models within one leader standard error are eligible; among them choose the lowest repeat-level Macro-F1 standard deviation, then higher mean balanced accuracy, higher mean worst-class recall, then the simpler family.
This one-standard-error rule is a precommitted stability heuristic, not a formal independent-sample confidence interval; repeat OOF scores are dependent and five repeats give a noisy SD estimate.

## Selected-family repeated-OOF confusion matrix

This matrix aggregates five repeat-level OOF prediction vectors. It is a CV diagnostic, not a fresh-holdout matrix.

| Actual / predicted | Adware | Banking Malware | SMS Malware | Riskware |
|---|---:|---:|---:|---:|
| Adware | 4218 | 113 | 0 | 64 |
| Banking Malware | 281 | 3750 | 129 | 235 |
| SMS Malware | 21 | 196 | 4143 | 35 |
| Riskware | 247 | 173 | 6 | 3969 |

## Calibration findings

Calibration was studied separately with nested package-grouped CV. Values remain conditional on the capped historical four-class study distribution.
Because model-family selection and calibration exploration reuse the same development cohort, the calibration comparison may be post-selection optimistic and is not independent validation.

| Method | Macro F1 | Log loss | Multiclass Brier | Top-label ECE |
|---|---:|---:|---:|---:|
| raw | 0.910982 | 0.323723 | 0.124480 | 0.019455 |
| sigmoid | 0.912031 | 0.264072 | 0.124834 | 0.038259 |
| isotonic | 0.914704 | 0.281883 | 0.122153 | 0.015492 |

Rule-qualified calibration candidate: **none**.

No probability is approved as user-facing confidence. Even a calibrated value here is not a current real-world likelihood: it assumes the binary detector already said malicious and the true type is one of these four classes. Other malware families would be forced into a known class.

## Fresh holdout status

- Status: **unavailable_current_corpus**
- Fresh holdout Macro F1: not computed
- Fresh holdout per-class precision/recall: not computed
- Fresh holdout confusion matrix: not computed

| Class | Never-used rows | Never-used normalized groups | Verifiably named groups |
|---|---:|---:|---:|
| Adware | 151 | 138 | 138 |
| Banking Malware | 0 | 0 | 0 |
| SMS Malware | 0 | 0 | 0 |
| Riskware | 1252 | 1031 | 1006 |

## Final recommendation

Do not integrate the category model into FastAPI yet. Obtain a frozen, independently labelled, schema-compatible holdout with new package groups in all four classes (especially Banking and SMS), ideally with APK hashes for duplicate/repackaging checks. Lock the family and calibration method first, then evaluate that holdout exactly once.

The exported joblib is deliberately named `selected_category_model_provisional.joblib`. It was fitted under scikit-learn 1.6.1, but metadata marks it uncalibrated, not integrated, and not justified for production use.

## Material limitations retained from the POC

- Category labels remain positionally aligned rather than hash-joined: feature_vectors_static.csv contains no label or hash. Labels are attached by row position because the static matrix and both accompanying 5-category files have exactly 11,598 rows, both Class vectors match row-for-row, and their contiguous class runs exactly match the category counts and order published for CICMalDroid 2020. This is strong positional evidence, not an independently keyed hash join.
- Cross-label package conflicts excluded before cohort construction: 18 packages / 264 rows.
- Package grouping cannot prove that different package names are repackaged copies because the static table has no APK hash join.
- CICMalDroid is historical and the permission-only representation omits richer static signals.
- The classifier is closed-set: unsupported malware types are forced into one of four known categories.

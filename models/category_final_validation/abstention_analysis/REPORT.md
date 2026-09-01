# Four-class Random Forest abstention analysis

## Outcome

Margin-based rejection is promising on the saved development evidence. The
locked rule is:

```text
top_score = largest of the four raw Random Forest class scores
second_score = second-largest class score
margin = top_score - second_score

if margin >= 0.70:
    return the top-scoring category
else:
    return Uncertain
```

`Uncertain` means only that the category classifier cannot safely distinguish
one of its four supported categories. It does **not** mean the upstream binary
malware detector considers the application benign.

The rule was selected and locked using development/repeated-CV evidence only.
The Random Forest was not retrained, tuned, calibrated, replaced, or modified.
FastAPI was not modified, and no final V2 evaluation was performed.

## Evidence and terminology

The primary artifact was `artifacts/cv_oof_predictions.csv`, filtered to
`model == "Random Forest"` (SHA-256
`720bb3fb31feb0f9819c29642e3acc0b1b95a2f148864e26f8c52d1bacf5626f`).
It contains 17,580 saved out-of-fold prediction events: 3,516 development rows
scored once in each of five repeated package-grouped CV runs. These are not
17,580 independent applications.

The four outputs are called **raw Random Forest class scores** throughout this
report. They are not calibrated probabilities and must not be presented as
confidence. The fixed score order is Adware, Banking Malware, SMS Malware,
Riskware.

Integrity checks found no missing/non-finite scores, range violations, score-sum
failures, argmax mismatches, saved-maximum mismatches, or correctness-flag
mismatches. Five events had an exact top-score tie; all had margin zero, were
incorrect, and are rejected by the locked rule.

## Phase 1: score and margin diagnostics

### Correct versus incorrect predictions

| Outcome | Events | Top score mean | Top score median | Second score mean | Second score median | Margin mean | Margin median | Margin P10-P90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Correct | 16,080 | 0.9263 | 1.0000 | 0.0497 | 0.0000 | 0.8766 | 1.0000 | 0.5125-1.0000 |
| Incorrect | 1,500 | 0.5942 | 0.5592 | 0.2663 | 0.2900 | 0.3279 | 0.2625 | 0.0350-0.7264 |

The large separation in median margin is the main reason rejection is useful.
It is not perfect: some errors have large margins, so no threshold makes an
accepted label intrinsically safe.

### By true category and correctness

| True category / outcome | Events | Top score mean | Top score median | Margin mean | Margin median |
|---|---:|---:|---:|---:|---:|
| Adware / correct | 4,218 | 0.9111 | 0.9850 | 0.8486 | 0.9705 |
| Adware / incorrect | 177 | 0.5491 | 0.5053 | 0.2494 | 0.2025 |
| Banking Malware / correct | 3,750 | 0.9200 | 1.0000 | 0.8714 | 1.0000 |
| Banking Malware / incorrect | 645 | 0.6253 | 0.6000 | 0.3810 | 0.3300 |
| SMS Malware / correct | 4,143 | 0.9282 | 1.0000 | 0.8759 | 1.0000 |
| SMS Malware / incorrect | 252 | 0.5804 | 0.5534 | 0.2875 | 0.2539 |
| Riskware / correct | 3,969 | 0.9464 | 1.0000 | 0.9118 | 1.0000 |
| Riskware / incorrect | 426 | 0.5739 | 0.5288 | 0.3039 | 0.2261 |

### Banking Malware error directions

| True Banking outcome | Events | Top score mean | Margin mean | Margin P25 | Margin median | Margin P75 |
|---|---:|---:|---:|---:|---:|---:|
| Correct Banking | 3,750 | 0.9200 | 0.8714 | 0.8616 | 1.0000 | 1.0000 |
| Predicted Adware | 281 | 0.6724 | 0.4496 | 0.1700 | 0.4064 | 0.7064 |
| Predicted Riskware | 235 | 0.5811 | 0.3274 | 0.1131 | 0.2656 | 0.5413 |
| Predicted SMS Malware | 129 | 0.6032 | 0.3292 | 0.0654 | 0.2324 | 0.4771 |

Yes: Banking samples mislabeled Adware or Riskware tend to have much smaller
margins than correctly classified Banking samples. This pattern is stable in
all five repeats. Correct-Banking median margin is 1.000 in every repeat;
Banking-to-Adware repeat medians range 0.363-0.460 and Banking-to-Riskware
medians range 0.242-0.300. Some Banking-to-Adware errors remain high-margin,
which limits what a simple rejection rule can fix.

## Phase 2: candidate rules

Definitions:

- Coverage is accepted events divided by all events.
- Accepted accuracy is correctness conditional on acceptance.
- Macro accepted precision is the unweighted mean of the four accepted-label
  precisions.
- True-class coverage is the accepted fraction within a true category.
- Accepted precision for a category is correctness among accepted predictions
  carrying that category label.

The table is a representative coarse-grid shortlist. The full 193-rule grid is
in `candidate_rules_all.csv`. Counts are repeated-OOF prediction events.

| Candidate | Coverage | Accepted accuracy | Macro accepted precision | Rejected events / rate | Errors rejected |
|---|---:|---:|---:|---:|---:|
| No abstention | 100.00% | 91.47% | 91.54% | 0 / 0.00% | 0.00% |
| A: top score >= 0.75 | 82.00% | 98.06% | 98.09% | 3,165 / 18.00% | 81.33% |
| A: top score >= 0.80 | 79.11% | 98.60% | 98.62% | 3,673 / 20.89% | 87.00% |
| B: margin >= 0.60 | 81.13% | 98.23% | 98.26% | 3,317 / 18.87% | 83.20% |
| **B: margin >= 0.70** | **77.86%** | **98.72%** | **98.73%** | **3,892 / 22.14%** | **88.33%** |
| B: margin >= 0.80 | 73.12% | 99.06% | 99.04% | 4,725 / 26.88% | 91.93% |
| C: top score >= 0.65 and margin >= 0.40 | 86.84% | 97.02% | 97.07% | 2,314 / 13.16% | 69.67% |

### True-class coverage and accepted-label precision

Each cell is `true-class coverage / accepted precision for that predicted
label`.

| Candidate | Adware | Banking Malware | SMS Malware | Riskware |
|---|---:|---:|---:|---:|
| No abstention | 100.00% / 88.48% | 100.00% / 88.61% | 100.00% / 96.84% | 100.00% / 92.24% |
| Top score >= 0.75 | 83.80% / 96.19% | 76.61% / 98.55% | 83.57% / 99.29% | 84.00% / 98.32% |
| Top score >= 0.80 | 80.20% / 96.75% | 73.61% / 99.05% | 80.14% / 99.38% | 82.48% / 99.31% |
| Margin >= 0.60 | 82.53% / 96.42% | 76.52% / 98.59% | 81.80% / 99.36% | 83.69% / 98.66% |
| **Margin >= 0.70** | **77.79% / 96.96%** | **72.67% / 99.16%** | **79.34% / 99.43%** | **81.64% / 99.38%** |
| Margin >= 0.80 | 69.78% / 97.36% | 68.87% / 99.56% | 75.06% / 99.52% | 78.77% / 99.74% |
| Top >= 0.65 and margin >= 0.40 | 89.33% / 94.71% | 83.50% / 97.40% | 87.19% / 98.59% | 87.33% / 97.57% |

Predicted-label retention is reported separately in
`candidate_rules_per_class.csv` so that it is not confused with true-class
coverage.

### Banking-specific candidate results

| Candidate | True-Banking coverage | Accuracy among accepted true Banking | Accepted Banking-label precision | Banking errors rejected | Banking->Adware rejected | Banking->Riskware rejected |
|---|---:|---:|---:|---:|---:|---:|
| No abstention | 100.00% | 85.32% | 88.61% | 0.00% | 0.00% | 0.00% |
| Top score >= 0.75 | 76.61% | 95.13% | 98.55% | 74.57% | 66.90% | 80.43% |
| Top score >= 0.80 | 73.61% | 96.32% | 99.05% | 81.55% | 72.24% | 91.49% |
| Margin >= 0.60 | 76.52% | 95.60% | 98.59% | 77.05% | 68.68% | 83.83% |
| **Margin >= 0.70** | **72.67%** | **96.62%** | **99.16%** | **83.26%** | **74.38%** | **92.77%** |
| Margin >= 0.80 | 68.87% | 97.39% | 99.56% | 87.75% | 79.72% | 97.02% |
| Top >= 0.65 and margin >= 0.40 | 83.50% | 92.83% | 97.40% | 59.22% | 51.25% | 68.94% |

### Class-specific sensitivity

Class-specific cutoffs were checked only as a small sensitivity analysis, not
as a large tuning grid.

| Predicted-top-class margin rule | Coverage | Accepted accuracy | Macro accepted precision | True-Banking coverage | Accepted true-Banking accuracy |
|---|---:|---:|---:|---:|---:|
| Adware/Riskware 0.70; Banking/SMS 0.60 | 79.27% | 98.58% | 98.57% | 75.68% | 96.66% |
| Adware/Riskware 0.80; Banking/SMS 0.70 | 75.05% | 98.95% | 98.92% | 72.10% | 97.38% |
| Banking 0.80; all others 0.70 | 77.00% | 98.80% | 98.83% | 69.53% | 96.47% |

The added complexity is not justified by the modest trade-offs. In particular,
a stricter cutoff for a top-predicted Banking label cannot reject a true Banking
sample already mislabeled as Adware or Riskware. The global margin rule directly
addresses those ambiguous outcomes and is easier to precommit and audit.

## Phase 3: locked rule and development estimate

The locked cutoff is **margin >= 0.70**, inclusive. It was chosen as a
conservative, simple knee in the development trade-off:

- It rejects 1,325 of 1,500 errors (88.33%) and leaves 175 accepted error
  events.
- It retains 13,688 of 17,580 prediction events (77.86% coverage).
- Accepted accuracy is 98.72%; macro accepted precision is 98.73%.
- Tightening from 0.70 to 0.80 gains only 0.34 percentage points of accepted
  accuracy while losing 4.74 points of coverage and reducing Banking coverage
  by 3.80 points.
- A margin-only rule is simpler than a combined rule and was slightly more
  efficient than score-only rules at comparable coverage.

Across the five repeats, coverage was 77.86% +/- 0.55 percentage points
(range 77.08%-78.53%), accepted accuracy was 98.72% +/- 0.12 points (range
98.56%-98.91%), and macro accepted precision was 98.73% +/- 0.13 points (range
98.57%-98.94%). These repeat SDs describe stability; they are not confidence
intervals because the repeats reuse the same development applications.

Package-equal sensitivity, which gives each normalized package equal weight
within a repeat, estimated 77.56% coverage, 98.38% accepted accuracy, and 98.44%
macro accepted precision. This is slightly less favorable than row weighting
but does not reverse the conclusion. It is relevant because SMS has 879 rows
but only 241 package groups.

### Banking effect of the locked rule

- True-Banking coverage: 72.67% (3,194/4,395 events accepted).
- Accepted true-Banking accuracy: 96.62%, up from 85.32% without abstention.
- Accepted Banking-label precision: 99.16%, up from 88.61%.
- Correct Banking events retained: 3,086/3,750 (82.29%); 664 correct Banking
  events are rejected as the cost of abstention.
- Banking errors rejected: 537/645 (83.26%); 108 remain accepted.
- Banking-to-Adware rejected: 209/281 (74.38%).
- Banking-to-Riskware rejected: 218/235 (92.77%).
- Banking-to-SMS rejected: 110/129 (85.27%).

Package-equal Banking sensitivity is less favorable: 71.99% true-Banking
coverage and 95.55% accepted true-Banking accuracy. This reinforces the need
for untouched validation rather than weakening or changing the locked rule.

## Previously consumed 196-sample holdout: descriptive only

Only after the 0.70 rule was locked, it was applied once to the already-consumed
supplementary artifact. It was not searched, ranked, or changed against this
data. These numbers are **not** a clean V2 evaluation:

| Descriptive metric | Result |
|---|---:|
| Coverage | 63.27% (124/196 accepted) |
| Rejected as Uncertain | 36.73% (72/196) |
| Accepted accuracy | 97.58% |
| Macro accepted precision | 97.26% |
| True-Banking coverage | 34.69% (17/49) |
| Accepted true-Banking accuracy | 88.24% |
| Accepted Banking-label precision | 93.75% |

The coverage and Banking shifts are a warning about dataset shift and optimism
in development estimates. They must not be used to revise the locked cutoff.

## Required untouched data for a clean V2 evaluation

Before scoring, freeze the Random Forest artifact, feature order and extractor,
the 0.70 rule, tie/boundary behavior, inclusion criteria, metrics, and analysis
code. Then obtain a newly collected cohort with:

1. Independently adjudicated labels for all four supported categories, with
   enough independent Banking and SMS groups to estimate their coverage,
   accepted accuracy, and accepted-label precision reliably.
2. No overlap with any historical split, the 3,516-row development cohort, or
   the consumed 196 samples at the APK hash, package, signing-certificate,
   family/campaign, near-duplicate, or repackaging-lineage level.
3. SHA-256 and provenance for every sample in every category, not only Banking
   and SMS, plus grouping of related versions before analysis.
4. The same frozen 153-permission feature contract. Extraction failures and
   missing features must be retained and reported rather than silently dropped.
5. Sources and collection dates independent of the current CICMalDroid-derived
   evidence. Use a deployment-representative class mix if user-facing precision
   is a target; the balanced development cohort cannot estimate that precision.
6. A prospectively chosen sample size based on desired interval widths and the
   expected 70%-80% acceptance rate, with intervals clustered or bootstrapped at
   the package/family level.
7. A separate unsupported-malware/OOD cohort to test whether unknown families
   become `Uncertain` rather than receiving a high-scoring supported label.
   Benign apps and upstream binary-detector outcomes are also required for a
   later end-to-end system evaluation, but are distinct from category
   abstention.

Evaluate the untouched supported-class cohort exactly once. Any later threshold
revision would require another untouched validation cohort.

## Reproducible outputs

- `development_prediction_scores.csv`: every saved Random Forest OOF event with
  all four scores, top/second labels and scores, margin, and correctness.
- `diagnostic_by_correctness.csv`, `diagnostic_by_actual_class.csv`, and
  `diagnostic_by_class_and_correctness.csv`: Phase 1 distributions.
- `banking_outcome_diagnostics.csv` and `banking_outcome_by_repeat.csv`:
  Banking-focused diagnostics.
- `candidate_rules_all.csv`, `candidate_rules_per_class.csv`,
  `candidate_rules_by_repeat.csv`, and `candidate_rules_repeat_summary.csv`:
  candidate-rule evidence.
- `locked_abstention_rule.json`: machine-readable precommitment.
- Files beginning `supplementary_holdout_`: clearly separated descriptive-only
  outputs for the consumed 196 samples.

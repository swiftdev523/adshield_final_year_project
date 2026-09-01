# Experimental selective category classifier

The backend contains an experimental, backend-only category sidecar for APK
Analysis Mode. It uses the existing unchanged four-class Random Forest and
still requires new independent validation.

## Scope and gating

Category inference is supported only by the raw-permission APK paths:

- `POST /analyze/apk`
- `POST /upload-apk`

The existing permission-only binary detector runs first. Category inference is
invoked only when its exact binary output is `Malicious`. It does not run for a
binary-benign result, even if install-source context later makes the overall
risk level `Suspicious` or `High Risk`.

`POST /predict-apk` does not run category inference because that installed-app
route supplies legacy display-label features rather than the category model's
frozen 153 raw-permission inputs.

For paths where category inference does not run, `threat_assessment` is `null`.
Because this is an experimental sidecar, an artifact-loading or category-scoring
failure also leaves the sidecar and its diagnostics `null` while preserving the
already completed binary and risk response. Operational failure is logged and
must not be mislabeled as score-based `Uncertain`.

## Locked selective rule

The threshold is fixed at exactly `0.70`:

```text
category_margin = highest_class_score - second_highest_class_score

accept when category_margin >= 0.70
otherwise return Uncertain
```

The supported category order and mapping are fixed:

```text
0 Adware
1 Banking Malware
2 SMS Malware
3 Riskware
```

An accepted response is:

```json
{
  "status": "classified",
  "likely_category": "Adware",
  "supported_categories": [
    "Adware",
    "Banking Malware",
    "SMS Malware",
    "Riskware"
  ],
  "method": "selective_category_classification"
}
```

A rejected response is:

```json
{
  "status": "uncertain",
  "likely_category": null,
  "supported_categories": [
    "Adware",
    "Banking Malware",
    "SMS Malware",
    "Riskware"
  ],
  "method": "selective_category_classification",
  "message": "The app's permission pattern does not clearly match one supported threat category."
}
```

`Uncertain` concerns category assignment only. It does not mean benign and does
not alter the upstream binary-malware result.

## Isolation from risk assessment

The binary verdict, malware probability, permission-risk score/level, install
source adjustment, and overall risk score/level are completed before the route
attaches `threat_assessment`. Category output is never an input to those fields.

Only the top score, second score, margin, and locked threshold are exposed, and
only under `diagnostics.category_classification`. The four-value class-score
vector is never returned. These values must be called raw class scores, never
confidence or calibrated probability, and must not be added to the normal UI.

## Validation status

This is an experimental selective classifier, not a production malware-family
system. Its threshold was locked using repeated grouped development predictions.
The previously consumed supplementary holdout cannot be used to revise it.

Before a clean V2 evaluation, freeze the model, feature contract, mapping,
threshold, and endpoint behavior, then collect new independently adjudicated,
source-disjoint, package/hash/certificate/family-disjoint APKs in all four
categories, especially Banking Malware and SMS Malware. Evaluate that untouched
cohort once under a predeclared protocol.

# `/upload-apk` response mapping and frontend integration plan

Status: endpoint mapping documented; frontend source code has not been changed.

## API verification basis

The real FastAPI application and multipart `POST /upload-apk` route were
exercised through its ASGI interface with real APK bytes, real manifest
parsing, the existing binary Random Forest, the existing risk integration, the
response model, and JSON serialization. The real category model was used for
the classified and uncertain cases. Only the category-service-failure case
used an injected exception, after real APK parsing and binary scoring, to
exercise the route's failure isolation.

Swagger UI (`GET /docs`) and OpenAPI (`GET /openapi.json`) both returned HTTP
200. OpenAPI advertises multipart form data, `UploadAPKResponse`, a nullable
`threat_assessment` union discriminated by `status`, the exact four supported
categories, and separately nullable category diagnostics.

All five requests returned HTTP 200. Complete serialized bodies, verification
metadata, sample paths, category-service invocation counts, and wire-body
hashes are captured in
[`../backend/UPLOAD_APK_ENDPOINT_VERIFICATION.json`](../backend/UPLOAD_APK_ENDPOINT_VERIFICATION.json).

## Verified canonical response projections

The JSON below is an exact projection of the canonical fields needed to reason
about each captured wire response. The capture linked above contains every
serialized field, including advanced permission details and deprecated
compatibility fields.

### Binary Benign

The category-service getter was called zero times.

```json
{
  "model_prediction": "Benign",
  "overall_risk_score": 14,
  "overall_risk_level": "Safe",
  "summary": {
    "recommendation": "Proceed only if you trust the publisher and the requested permissions match the app's purpose."
  },
  "risk_components": {
    "permission_assessment": {
      "risk_score": 14,
      "risk_level": "Safe",
      "model_prediction": "Benign"
    }
  },
  "threat_assessment": null
}
```

### Binary Malicious, classified

The category service was called once and returned a supported category.

```json
{
  "model_prediction": "Malicious",
  "overall_risk_score": 56,
  "overall_risk_level": "Suspicious",
  "summary": {
    "recommendation": "Verify the publisher and install source, then review the highlighted permissions before installing or keeping the app."
  },
  "threat_assessment": {
    "status": "classified",
    "likely_category": "Banking Malware",
    "supported_categories": [
      "Adware",
      "Banking Malware",
      "SMS Malware",
      "Riskware"
    ],
    "method": "selective_category_classification"
  }
}
```

### Binary Malicious, uncertain

The category service was called once. The serialized body contains an explicit
`null` category.

```json
{
  "model_prediction": "Malicious",
  "overall_risk_score": 52,
  "overall_risk_level": "Suspicious",
  "summary": {
    "recommendation": "Verify the publisher and install source, then review the highlighted permissions before installing or keeping the app."
  },
  "threat_assessment": {
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
}
```

### Category-service failure

The category service was called once and deliberately raised. The route still
returned the completed binary and overall assessment. After removing only
`threat_assessment` and `diagnostics.category_classification`, this response
was value-for-value identical to the classified response for the same APK and
install source.

```json
{
  "model_prediction": "Malicious",
  "overall_risk_score": 56,
  "overall_risk_level": "Suspicious",
  "summary": {
    "recommendation": "Verify the publisher and install source, then review the highlighted permissions before installing or keeping the app."
  },
  "risk_components": {
    "permission_assessment": {
      "risk_score": 56,
      "risk_level": "Suspicious",
      "model_prediction": "Malicious"
    }
  },
  "threat_assessment": null
}
```

### Binary Benign with install-source risk increase

The same benign APK was submitted as a sideload. Its binary permission
assessment remained Benign/Safe at 14, while contextual risk raised the final
assessment to Suspicious at 34. The category-service getter was called zero
times.

```json
{
  "model_prediction": "Benign",
  "overall_risk_score": 34,
  "overall_risk_level": "Suspicious",
  "summary": {
    "recommendation": "Verify the publisher and install source, then review the highlighted permissions before installing or keeping the app."
  },
  "risk_components": {
    "permission_assessment": {
      "risk_score": 14,
      "risk_level": "Safe",
      "model_prediction": "Benign"
    },
    "contextual_adjustment": {
      "install_source_display": "APK sideload",
      "score_adjustment": 20,
      "context_level": "High"
    }
  },
  "threat_assessment": null
}
```

## Frontend allowlist

Frontend rendering must consume the canonical fields below rather than the
deprecated flat compatibility fields.

| UI concept | Backend field |
| --- | --- |
| Filename and package | `summary.app.filename`, `summary.app.package` |
| Binary category gate | top-level `model_prediction` |
| Displayed risk score | `summary.overall_risk_score` |
| Displayed risk level and color token | `summary.overall_risk_level` |
| Recommendation | `summary.recommendation` |
| Explanation and reasons | `summary.final_explanation`, `summary.important_reasons` |
| Install-source label | `summary.install_source_display` |
| Permission counts | `summary.total_permission_count`, `summary.curated_sensitive_permission_count` |
| Requested permissions | `advanced_details.permissions` |
| Curated permission cards | `advanced_details.curated_sensitive_permissions` |
| Threat category | `threat_assessment` |

The frontend view model must not contain or display:

- `diagnostics` or any nested category score, margin, or threshold;
- `malware_probability`, `probability_malware`, or `confidence`;
- deprecated flat score, risk, explanation, permission, or model aliases.

The risk meter must display the backend score and backend level directly. It
may map `Safe`, `Suspicious`, and `High Risk` to visual colors, but it must not
recalculate a level from the number. Category state must never be an input to
the risk score, risk label, recommendation, explanation, or permission cards.

## Category rendering contract

Apply the binary gate first:

1. When `model_prediction !== "Malicious"`, render no threat-category section,
   regardless of any stale or malformed local category value.
2. For Malicious plus `status === "classified"`, render the title **Likely
   Threat Category** and `likely_category`.
3. For Malicious plus `status === "uncertain"`, render the title **Threat
   Category — Uncertain** and the exact backend-supplied `message`.
4. For Malicious plus `threat_assessment === null`, treat the category sidecar
   as unavailable. Do not call it uncertain and do not invent a category. A
   neutral unavailable state may be shown inside the malicious-only section.

## Planned frontend implementation

1. Add `lib/api/types.ts` with the exact supported-category union, a
   `status`-discriminated threat-assessment union, and canonical upload response
   types. Add `lib/api/uploadApk.ts` using `EXPO_PUBLIC_API_BASE_URL` and
   multipart fields `file` and `install_source`. Native uploads use the picker
   asset's `{ uri, name, type }`; web uploads use a `File`. Do not manually set
   the multipart `Content-Type` boundary.
2. Add a pure adapter such as `lib/scan/mapUploadApkResponse.ts`. It will map
   the allowlisted fields into a narrow, source-neutral `ScanAssessment`. The
   adapter will intentionally omit probabilities, diagnostics, category model
   values, and deprecated fields.
3. Replace the filename/score-only state in `store/useScanStore.ts` with
   `idle | uploading | success | error`, the real assessment, and retry/error
   state. Use a discriminated input source: `{ kind: "apk", asset,
   installSource }` now, with `{ kind: "installed_app", packageName }` reserved
   for a later adapter.
4. Update `components/scan/FilePicker.tsx` to retain DocumentPicker, start the
   real upload, and navigate to the result screen while it shows the actual
   request state. Remove the fixed score `72`.
5. Rebuild `app/scan-result.tsx` around `ScanAssessment`: remove fake timers,
   fixed permission arrays/counts, score-derived risk/advice, and fallback APK
   names. Render loading, error/retry, the canonical summary, real permissions,
   and the malicious-only category states described above.
6. Change `components/ui/RiskMeter.tsx` to accept both the backend score and
   backend risk level. Change `components/scan/PermissionItem.tsx` to consume
   backend labels, descriptions, and high/medium severity; raw uncatalogued
   permissions must be described as requested permissions, not safe ones.
7. Remove APK-result mocks and fake result entry points from
   `app/(tabs)/scan.tsx`, `app/(tabs)/index.tsx`, and the APK/history portions
   of `lib/mockData.ts`. Home scan history and stats should derive from stored
   completed assessments. Notification-demo data is a separate subsystem and
   is outside this APK endpoint integration.
8. Verify the pure adapter against all five captured bodies. Add UI coverage
   for benign hidden, classified, uncertain exact message, malicious/null
   unavailable, request failure/retry, and invariance of risk/recommendation
   across category states. Add a multipart request test, run
   `tsc --noEmit`, and perform a physical-device or emulator upload against the
   backend.

Keeping the transport clients separate from the source-neutral assessment
adapter preserves the working APK scanner and allows a future installed-app
scanner to produce the same view model without changing the result UI.

For native Expo, the API host must be reachable from the device or emulator;
`127.0.0.1` refers to the device itself. Expo Web would additionally require a
separately approved backend CORS change, which is not part of this plan.

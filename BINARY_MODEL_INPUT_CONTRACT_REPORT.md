# Binary Model Input Contract Report

Audit date: 2026-08-11  
Decision: **Phase 6 Case B — the historical 241-feature contract cannot be reproduced reliably**

## Executive outcome

The frozen binary Random Forest and its feature order are intact, but the
runtime supplies only manifest-declared permissions. The model was trained with
a mixed TUANDROMD schema that includes API/code features. The repository does
not contain the original APK feature extractor or a sufficiently precise
definition of how those API values were produced.

Therefore no DEX/API proxy was added. The model remains unchanged, the binary
threshold remains `0.50`, and runtime diagnostics now describe the input
contract as `partial`.

The machine-readable, row-by-row table for all 241 features is in
`models/binary_feature_contract_audit.json`.

## Frozen artifact verification

| Item | Verified value |
|---|---:|
| Estimator | `RandomForestClassifier` |
| Classes | `[0, 1]` |
| Ordered input features | 241 |
| Binary decision threshold | `0.50` |
| Model SHA-256 | `54b7560bf7845b5eb5fb7a60057fd9a166c2843c5c8e65c133ad78d80d2aeba5` |
| Ordered-feature SHA-256 | `024ca7f02a42988fd35bb8154d10dd1e1315089cb0d77361bcda7b9164e0d4d8` |

The current runtime still constructs a row with exactly these 241 columns in
the embedded order. Missing inputs are zero. The ordering is not the defect;
the defect is incomplete feature availability.

## Exact contract inventory

The [UCI TUANDROMD record](https://archive.ics.uci.edu/dataset/855/tuandromd)
documents features 1–214 as permission based and 215–241 as API based. The
frozen estimator contains those 241 names, but its first block also contains
the unexplained field `activityCalled` and several malformed headers.

| Audit group | Count | Share of impurity-based importance |
|---|---:|---:|
| A — manifest permission reproducible by the current normalizer | 208 | 62.3986% |
| B — exact API/method name is statically observable in principle | 26 | 29.0773% |
| C — unclear, corrupted, or unreachable exact name | 7 | 8.5241% |
| **Total** | **241** | **100.0000%** |

Additional views of the same contract:

- Dataset-declared permission block: 214 features.
- Dataset-declared API block: 27 features.
- Artifact features that are not manifest permissions: 28 — `activityCalled`
  plus the 27 API columns.
- Non-manifest importance mass: 37.5426%.
- Features that the current permission-only runtime cannot activate: 33.
- Importance mass assigned to those 33 features: 37.6014%.
- Exact API/method names that a structured DEX parser could observe in
  principle: 26.
- API features implemented during this task: 0.

“Importance mass” above means the Random Forest's stored impurity-based feature
importance allocation. It is not a probability and does not mean that removing
a group reduces accuracy by the same percentage.

## Unclear, corrupted, or unreachable features

| Frozen feature name | Probable meaning | Why it is not repaired automatically |
|---|---|---|
| `activityCalled` | Unknown aggregate or extraction field | It is neither a permission constant nor an API signature, and no definition is present. |
| `AUTORUN_MANAGER_LICENSE_SERVICE(.autorun)` | Vendor autorun-service permission | Final-token normalization cannot reproduce the full punctuation-bearing header. |
| `BIND_goodwareTIFICATION_LISTENER_SERVICE` | Probably `BIND_NOTIFICATION_LISTENER_SERVICE` | The probable correction is an inference; the mixed-case stored name is unreachable. |
| `DIAGgoodwareSTIC` | Probably `DIAGNOSTIC` | The probable correction is an inference; the mixed-case stored name is unreachable. |
| `DOWNLOAD_WITHOUT_goodwareTIFICATION` | Probably `DOWNLOAD_WITHOUT_NOTIFICATION` | The probable correction is an inference; the mixed-case stored name is unreachable. |
| `FULLSCREEN.FULL` | Vendor full-screen permission | Final-token normalization yields only `FULL`. |
| `Landroid/location/LocationManager;->getLastKgoodwarewnLocation` | Probably `getLastKnownLocation` | The frozen API name is corrupted and the historical matching rule is absent. |

These probable meanings are documentation only. They are not runtime aliases,
because changing them would fabricate values for a frozen model.

## Static API extraction feasibility

The 26 well-formed API names can be looked for safely without running an APK.
For example, Androguard supports structured DEX classes, methods, and
cross-references through its
[Analysis API](https://androguard.github.io/androguard/reference/androguard/core/analysis/analysis.html).
That establishes technical observability, not historical equivalence.

| Question | Finding |
|---|---|
| Can the exact historical meaning be determined? | **No.** The dataset page identifies an API block but does not define whether a `1` meant a method-id reference, an invoke instruction, a reachable call, or another extraction rule. The original extractor is absent. |
| Can API references be extracted statically? | **Yes, in principle.** A DEX parser can inspect method identifiers and invoke cross-references without executing the app. |
| Uploaded APK support | Technically possible by scanning every DEX entry, but not currently implemented. |
| Installed-app support | Technically possible only after obtaining and scanning the base APK and all split APKs. Android exposes these through [`ApplicationInfo.sourceDir` and `splitSourceDirs`](https://developer.android.com/reference/android/content/pm/ApplicationInfo), but the protected native scanner currently submits permissions only. |
| New dependency or native contract | A structured DEX parser would be required, and installed-app analysis would require a new, explicitly approved read-only APK transfer/analysis contract. |
| Can static analysis prove execution? | **No.** It can show a reference or invoke instruction exists; it cannot prove the path executes at runtime. |

Naive byte/string searching was rejected because it can:

- match a method name in resources, metadata, or unused library code;
- miss obfuscated, reflective, dynamically loaded, or native behavior;
- confuse a method-id reference with a real invoke instruction;
- ignore overload descriptors, which the frozen feature names omit;
- miss secondary DEX files or installed split APKs.

Because the historical rule is unknown, even a correct modern DEX-reference
extractor could create a different distribution from the one on which the
Random Forest was trained.

## Permission-normalization audit

The current binary path deliberately maps a raw permission to its upper-case
final token:

```text
permission.strip().rsplit(".", 1)[-1].upper()
```

This is compatible with the shortened names embedded in the model, so it was
not changed. It can, however, collapse unrelated vendor permissions. The real
device snapshot for `com.whatsapp` contained 85 full permission strings and 82
unique normalized tokens. Three collisions occurred, and all three normalized
tokens exist in the binary model:

| Normalized token | Original full permission strings |
|---|---|
| `INSTALL_SHORTCUT` | `android.permission.INSTALL_SHORTCUT`; `com.android.launcher.permission.INSTALL_SHORTCUT` |
| `READ` | `com.sec.android.provider.badge.permission.READ`; `com.whatsapp.sticker.READ` |
| `READ_SETTINGS` | `com.htc.launcher.permission.READ_SETTINGS`; `com.huawei.android.launcher.permission.READ_SETTINGS` |

The original strings remain intact in advanced permission details. New
diagnostics report collisions internally; the normal frontend does not display
collapsed tokens as if they were the original permission names.

The same device snapshot matched 46 of the 241 binary feature names. It also
contained 27 standard Android permissions absent from the old training schema,
including `POST_NOTIFICATIONS`, `BLUETOOTH_CONNECT`, `NEARBY_WIFI_DEVICES`, the
modern media permissions, and foreground-service types. The complete
classification-D inventory is recorded in the JSON audit. These absent modern
permissions remain ignored by the frozen model; inventing columns would change
its contract.

## Runtime capability statement

The internal diagnostic contract is:

```json
{
  "binary_input_contract": "partial",
  "binary_feature_coverage": {
    "expected": 241,
    "available": 208,
    "missing": 33,
    "static_api_features_available": 0,
    "matched_current_input": "per-app value"
  }
}
```

Here, `available` means a model column is reachable by the current manifest
permission normalizer. It does not mean the permission is active for a
particular app. `matched_current_input` is the per-app number of active model
columns.

This object is diagnostic only. It must not be rendered as a normal-user score
or confidence value.

## Why Phase 6 Case B was selected

The following evidence is not available in this project:

1. the original TUANDROMD APK extraction program and version;
2. a definition of `activityCalled`;
3. the API feature matching rule;
4. method descriptors or overload handling;
5. treatment of multidex, embedded libraries, dead code, reflection, and
   obfuscation;
6. a known APK-to-row provenance set with which to validate a replacement
   extractor feature by feature.

Therefore, implementing DEX flags now would be an unvalidated proxy. That would
hide the limitation and could change model behavior without retraining or a
clean validation set.

## Recommended remediation

Choose one future path, with new package-disjoint validation:

1. **Preferred:** train a genuinely permission-only binary model using the
   exact runtime normalizer, a versioned ordered feature list, and modern
   permission coverage.
2. Define and version a reproducible manifest-plus-DEX extractor first, freeze
   its semantics and dependency versions, then retrain a model using exactly
   those produced features.

Do not retrofit guessed API flags into the current estimator, change the 0.50
threshold, whitelist packages, or infer safety from Google Play installation.

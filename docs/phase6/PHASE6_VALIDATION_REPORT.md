# Phase 5 Completion and Phase 6 Final Validation

Date: 2026-08-29

## Outcome

Phase 5 is complete and Phase 6 final consistency testing is complete on the connected physical Android phone (`06134250CI003816`). No production code, backend thresholds, feature contracts, native contracts, or model artifacts were changed during Phase 6.

The system passed the planned integration and consistency checks. The tests also reproduced an important existing prototype limitation: a CIC-labelled Adware APK can still be classified as `Benign` by the unchanged binary permission model. This is an observed model false negative, not a transport or UI failure, and it was not hidden or corrected by package-specific logic.

## Phase 5 completion evidence

- Settings are persisted locally in `files/settings/adshield-settings-v1.json`.
- Privacy Mode was enabled, verified after a cold restart, verified to shorten identifiers, then restored to `OFF`.
- The restored persisted value after the final cold restart was `{"version":1,"privacyMode":false}` and the Settings UI showed `OFF`.
- Notification monitoring reports the real Android special-access state.
- Auto-scan downloads is truthfully labelled `Planned - not active`; the text states that AdShield scans only APKs explicitly chosen by the user.
- Privacy, permission-use, and notification-access information screens are available.

## Automated verification

| Check | Result |
| --- | --- |
| TypeScript (`npm run typecheck`) | Passed |
| Frontend Jest | 33 suites, 199 tests passed |
| Backend pytest | 64 tests passed; 3 framework deprecation warnings only |
| Kotlin/native unit tests | 45 tests passed; 0 failures, errors, or skipped tests |
| Gradle native test task | Build successful; 74 tasks |
| Android debug APK rebuild | Not required because no native source changed |
| Existing Phase 4 APK SHA-256 | `DED006E661FB0612FDB2B319C1CFD3B52CCF21452D1D8533EFE48006F094089F` |

The first native-test attempt reported a missing `ANDROID_HOME`. The same tests were rerun with the installed Android SDK, JDK 17, and the existing short staging-drive configuration; that controlled rerun passed.

## Physical phone verification

### APK analysis

| Scenario | Actual result |
| --- | --- |
| Valid APK | Passed. The real Riskware APK was selected through Android's file picker and returned a full result screen. |
| Invalid APK | Passed. UI displayed `Analysis failed` and `Failed to parse APK: File is not a zip file`. The HTTP endpoint returned 422 with the same detail. |
| Backend unavailable | Passed. UI displayed `Could not reach the APK analysis server. Check the backend address and connection.` |
| Classified category | Passed. `com.hzd.fyyvwq`, 42 permissions, binary `Malicious`, malware probability `0.54`, permission score `54`, overall `74 / High Risk`, category `Riskware`, raw category margin `1.0`, locked threshold `0.7`, 37 matched category features. |
| Uncertain category | Passed. `gdfaslbek.ngnsobbu.rd`, 14 permissions, binary `Malicious`, malware probability `0.56`, permission score `56`, overall `76 / High Risk`, category `Uncertain`, raw category margin `0.1258690476190476`, locked threshold `0.7`, 12 matched category features. |

The category values above are actual responses. Raw Random Forest category scores remain diagnostic and are not described as calibrated confidence.

### Installed-app analysis

| Scenario | Actual result |
| --- | --- |
| Google Play app | Passed with ChatGPT (`com.openai.chatgpt`): Google Play Store installer, 30 declared permissions, `16 / 100`, `Low Permission Concern`. |
| Sideloaded app | Passed with Connect Laundry (`com.connectlaundry.app`): APK sideload installer, 37 declared permissions, `42 / 100`, `Permission Review Recommended`. Sideloading was described as source context, not malware evidence. |
| No declared permissions | Passed with Remote Desktop (`com.google.chromeremotedesktop`): 0 declared permissions; result was `Permission analysis unavailable` with `No declared permissions were available for permission-based analysis.` |
| Backend unavailable | Passed. UI displayed `Analysis failed`, `Network request failed`, and `Try again`. |

For benign installed-app results, the normal UI does not display the technical model word `Benign`. The threat-category panel displays `Not applicable` and `No malicious classification was made.`

### Notification monitoring

| Scenario | Actual result |
| --- | --- |
| Access denied | Passed. UI requested Android Notification Access and provided the settings action. |
| Access granted | Passed. Android listed the AdShield listener and the UI reported active monitoring. |
| Real event captured | Passed. A real test notification posted through Android was persisted as a `com.android.shell` event. |
| Backend classification | Passed. The selected real test event returned `NORMAL`; the UI stated that the result applied only to that notification. |
| No history | Passed. After a confirmed local clear, the UI displayed `No notifications observed yet` and the native history file was absent. |
| Restart persistence | Passed. Restored history reloaded after restart as `Monitoring active | 500 notifications across 15 apps`. |

The notification test text was not called spam because the actual backend response was `NORMAL`.

### History and Home

- Successful APK and installed-app scans appeared in local history and updated Home counts.
- A single saved scan was deleted successfully.
- Clear-all required the `Clear scan history?` confirmation and produced `No completed scans yet`.
- The original state was then restored from the reversible in-app backup.
- After a cold restart, Home returned to the original `10 scans completed`, `2 Safe Results`, and `0 Threats` state.

### Settings

- Cold-restart persistence passed with Privacy Mode restored to `OFF`.
- Notification monitoring displayed `Enabled` and accurately stated that Android notification access is enabled.
- Auto-scan displayed `Planned - not active` and did not claim background Downloads monitoring.
- The Phase 5 on-device check had already verified identifier shortening while Privacy Mode was enabled.

## Regression and integrity checks

- Installed-app discovery still returned real launcher-visible Android applications and their real PackageManager metadata.
- Diagnostic fields such as category score/margin, model names, band ranges, and integration notes remain outside the normal result summary.
- The APK example cards are explicitly labelled `Demonstration examples - not live scans` and state that they never generate analysis results.
- Mock example data is confined to those labelled demonstration cards and is not used by live APK, installed-app, notification, Home, or history results.
- Repeated development-client deep-link launches produced an Expo/React Native development-only LogBox warning about multiple linking handlers. The project has one Expo Router entry, no extra application `NavigationContainer`, and Android `MainActivity` already uses `singleTask`; the warning did not appear as production result content and was dismissed for testing.
- The local backend was stopped only for the two unavailable-service checks and restarted with the unchanged command. Final health returned `status: ok`.
- The three temporary APK test copies were removed from `/sdcard/Download/AdShieldPhase6`; the original dataset files remain on the computer.
- Notification access, notification history, scan history, and Settings were restored after destructive-state tests.

## Protected-file hashes

- Files checked: 33
- Differences between before and after manifests: 0
- Before: `docs/phase6/protected_files_before.sha256`
- After: `docs/phase6/protected_files_after.sha256`

This proves that the protected backend routes, model services, model artifacts, frontend integration files, stores, and native repositories/listener did not change during Phase 6.

## Observed model limitation

An existing CIC-labelled Adware sample (`com.lmobileapp.taskmanager`) returned binary `Benign`, malware probability `0.18`, permission score `18`, website context `+12`, and overall `30 / Safe`. Because the binary detector did not classify it as malicious, the secondary category classifier correctly did not run.

This result confirms that permission-only static models can miss malicious applications whose supported permission pattern resembles benign software. Phase 6 did not retrain, tune, replace, whitelist, or override the model. The current system should continue to be presented as an FYP prototype assessment tool, not a production-security certification.

## Final state

- Backend: running and healthy on port 8000.
- Metro: running on port 8081.
- ADB reverse: ports 8000 and 8081 restored.
- Notification listener: enabled.
- Phone data: original 10-scan history, original notification history, and Privacy Mode `OFF` restored.
- Production/model/native edits made in Phase 6: none.


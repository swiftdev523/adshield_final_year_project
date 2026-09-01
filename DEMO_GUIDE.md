# Supervisor Demo Guide

This guide demonstrates the existing FastAPI backend through Swagger UI. The
examples below were executed against the current backend and current saved model
artifacts on 20 July 2026. No prediction values have been estimated.

## 1. Start the backend

Open PowerShell in the project root:

```text
D:\beeeen\android adware detection system1
```

Start the server with:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Keep this terminal open during the demonstration. A successful startup includes
`Uvicorn running on http://127.0.0.1:8000`.

## 2. Open Swagger

Open this URL in a browser:

```text
http://127.0.0.1:8000/docs
```

For each request, expand the endpoint, select **Try it out**, enter the supplied
body or form values, and select **Execute**. Point out the HTTP `200` response
before explaining the result.

## 3. Recommended demonstration order

1. `GET /health` - prove that the backend and installed-app model are available.
2. `POST /analyze/install-source` - introduce install-source risk.
3. `POST /analyze/apk` with the safe sample - demonstrate permission analysis.
4. `POST /analyze/apk` with the high-risk sample - contrast the safe result.
5. `POST /analyze-notification` with normal text - demonstrate a Ham result.
6. `POST /analyze-notification` with spam text - demonstrate a Spam result.
7. `GET /monitor/notifications/com.example.freeprizes` - show that supplying a
   package name records the notification for monitoring.
8. `GET /monitor/notifications/alerts` - explain that one event is below the
   alert thresholds, so the list is empty.
9. `POST /upload-apk` - finish with real APK extraction and scoring. Keep this
   last because file selection and APK parsing are the most environment-sensitive
   parts of the demonstration.

The `/predict-apk` and `/explain` routes are supporting routes and do not need to
be shown in this short demo: `/analyze/apk` already demonstrates scoring and the
explanation engine together.

## 4. Health check

Endpoint: `GET /health`

Actual response:

```json
{
  "status": "ok",
  "model": "HistGradientBoosting (balanced)",
  "n_features": 157,
  "decision_threshold": 0.22999999999999998
}
```

Explain: the API is running, its installed-app model is loaded, the model expects
157 features, and it is using the saved tuned threshold. This endpoint does not
classify an app.

## 5. Install-source analysis

Endpoint: `POST /analyze/install-source`

Request body:

```json
{
  "install_source": "apk_sideload"
}
```

Actual response:

```json
{
  "install_source": "apk_sideload",
  "install_source_display": "APK sideload",
  "source_risk_level": "High",
  "source_risk_points": 20,
  "source_explanation": "Installed by sideloading an APK file manually. Sideloaded apps bypass store review and are a common adware distribution method."
}
```

Explain: this endpoint evaluates only where the app came from. Sideloading is
assigned 20 additional risk points because it bypasses store review. It does not
inspect permissions or make a model prediction by itself.

## 6. Safe-app permission demonstration

Endpoint: `POST /analyze/apk`

This is a realistic small utility-app profile: internet access, network-state
checking, and vibration, with Google Play as the install source.

Request body:

```json
{
  "package": "com.example.flashlight",
  "permissions": [
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.VIBRATE"
  ],
  "install_source": "google_play_store"
}
```

Actual response:

```json
{
  "install_source": "google_play_store",
  "install_source_display": "Google Play Store",
  "source_risk_level": "Low",
  "source_risk_points": 0,
  "source_explanation": "Installed from Google Play Store. Official store distribution generally lowers install-source risk, though permissions should still be reviewed.",
  "package": "com.example.flashlight",
  "risk_score": 0,
  "prediction": "Safe",
  "band_range": "0-30",
  "confidence": 1.0,
  "explanation": "This app can check network connectivity It also has full internet access..",
  "reasons": [
    "This app can check network connectivity.",
    "This app has full internet access.",
    "This app can control the vibrator.",
    "Overall, this app appears low risk based on its permissions (score 0/100).",
    "The permission profile is consistent with typical safe applications.",
    "Installed from Google Play Store. Official store distribution generally lowers install-source risk, though permissions should still be reviewed.",
    "Install source (Google Play Store) did not increase the permission-based risk score."
  ],
  "permission_risk_score": 0,
  "permission_risk_level": "Safe",
  "integration_note": "Install source (Google Play Store) did not increase the permission-based risk score.",
  "probability_malware": 0.0,
  "dangerous_permission_count": 1,
  "safe_permission_count": 2,
  "permissions_detected": 3,
  "model_name": "RandomForestClassifier",
  "mode": "APK Analysis Mode"
}
```

Explain: the permission-only model returned a score of 0 and the `Safe` band.
Google Play added zero source-risk points, so the overall score stayed 0. Also
point out that `Safe` means low risk according to this model; it is not a promise
that an app can never be harmful.

## 7. High-risk permission demonstration

Endpoint: `POST /analyze/apk`

This sample represents an aggressive utility/adware profile: boot persistence,
overlay access, SMS access, phone identity, location, storage, camera, and system
control permissions. Its stated source is unknown.

Request body:

```json
{
  "package": "com.example.aggressivecleaner",
  "permissions": [
    "android.permission.RECEIVE_BOOT_COMPLETED",
    "android.permission.GET_TASKS",
    "android.permission.WAKE_LOCK",
    "android.permission.KILL_BACKGROUND_PROCESSES",
    "android.permission.READ_PHONE_STATE",
    "android.permission.DISABLE_KEYGUARD",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.CHANGE_WIFI_STATE",
    "android.permission.ACCESS_WIFI_STATE",
    "android.permission.VIBRATE",
    "android.permission.RECEIVE_SMS",
    "android.permission.CAMERA",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.SEND_SMS",
    "android.permission.READ_SMS",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.WRITE_SETTINGS",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.INTERNET"
  ],
  "install_source": "unknown_source"
}
```

Actual response:

```json
{
  "install_source": "unknown_source",
  "install_source_display": "Unknown source",
  "source_risk_level": "Very High",
  "source_risk_points": 28,
  "source_explanation": "Install source is unknown or untrusted. Unknown-origin apps carry the highest install-source risk and should be treated with caution.",
  "package": "com.example.aggressivecleaner",
  "risk_score": 98,
  "prediction": "High Risk",
  "band_range": "71-100",
  "confidence": 0.7,
  "explanation": "This app can send and read SMS messages. Install source is unknown or untrusted. Unknown-origin apps carry the highest install-source risk and should be treated with caution.",
  "reasons": [
    "Send + read SMS together is a common pattern in SMS fraud and premium-rate adware.",
    "SMS sending combined with auto-start at boot is frequently seen in SMS-fraud adware.",
    "Drawing over other apps plus auto-start lets adware show ads even when the app is not open.",
    "Reading SMS with internet access can be used to leak verification codes or personal messages.",
    "Continuous location tracking plus internet access is common in tracking and adware apps.",
    "This app can track your approximate location.",
    "This app can check network connectivity.",
    "This app can check Wi-Fi status.",
    "This app can use the camera.",
    "This app can see what other apps are running.",
    "This app can read files on your storage.",
    "This app can read phone state and device identity.",
    "This app can receive SMS messages.",
    "This app can control the vibrator.",
    "This app can prevent the phone from sleeping.",
    "This app can modify or delete files on your storage.",
    "It requests 15 dangerous permissions, more than a typical app needs.",
    "This app shows moderate risk indicators (score 70/100) - review before installing.",
    "Some sensitive permissions or combinations warrant a closer look.",
    "Install source is unknown or untrusted. Unknown-origin apps carry the highest install-source risk and should be treated with caution.",
    "Overall risk raised from Suspicious to High Risk due to install source (Unknown source)."
  ],
  "permission_risk_score": 70,
  "permission_risk_level": "Suspicious",
  "integration_note": "Overall risk raised from Suspicious to High Risk due to install source (Unknown source).",
  "probability_malware": 0.7,
  "dangerous_permission_count": 15,
  "safe_permission_count": 5,
  "permissions_detected": 21,
  "model_name": "RandomForestClassifier",
  "mode": "APK Analysis Mode"
}
```

Explain: the model-derived permission score is 70. The unknown source contributes
28 points, producing a capped overall score of 98 and raising the overall band
from `Suspicious` to `High Risk`. Highlight the combinations in `reasons`, such
as SMS read/send, boot persistence, overlays, location, and internet access.

## 8. Normal-notification demonstration

Endpoint: `POST /analyze-notification`

Request body:

```json
{
  "text": "Your verification code is 482913. Do not share it with anyone.",
  "package": "com.example.messages"
}
```

Actual response:

```json
{
  "prediction": "Ham",
  "confidence": 73.6
}
```

Explain: `Ham` means normal/non-spam notification text. Confidence is reported
as a percentage for this endpoint. Supplying a package name also records the
event in the five-minute in-memory notification monitor.

## 9. Spam-notification demonstration

Endpoint: `POST /analyze-notification`

Request body:

```json
{
  "text": "Congratulations! You have won a free iPhone. Click here now to claim your prize!",
  "package": "com.example.freeprizes"
}
```

Actual response:

```json
{
  "prediction": "Spam",
  "confidence": 77.5
}
```

Explain: the notification model labels the prize-and-click wording as `Spam`
with 77.5% confidence. This event is also recorded against the supplied package.

Immediately demonstrate `GET /monitor/notifications/com.example.freeprizes`.
The actual response after the single spam request above was:

```json
{
  "package": "com.example.freeprizes",
  "total_in_window": 1,
  "spam_in_window": 1,
  "ham_in_window": 0,
  "rate_per_minute": 0.2,
  "window_seconds": 300,
  "unusual_volume": false,
  "spam_heavy": false,
  "alert_message": null
}
```

Explain: one spam event is recorded, but one event does not meet either alert
threshold. Monitoring data is in memory and resets when the backend restarts.

Then demonstrate `GET /monitor/notifications/alerts`. After the requests above,
the actual response was:

```json
{
  "alerts": [],
  "window_seconds": 300
}
```

Explain: the empty list is expected because the configured alert thresholds
have not been reached. Do not repeatedly submit requests merely to force an alert.

## 10. Real APK upload demonstration

Endpoint: `POST /upload-apk`

In Swagger:

1. Select **Try it out**.
2. Set `install_source` to `apk_sideload`.
3. Choose the included `youcine (1).apk` file from the project root.
4. Select **Execute** and wait for manifest parsing and model scoring.

The real upload returned HTTP `200`. Important fields from the actual response:

```json
{
  "install_source": "apk_sideload",
  "install_source_display": "APK sideload",
  "source_risk_level": "High",
  "source_risk_points": 20,
  "package": "com.world.youcinemobile",
  "filename": "youcine (1).apk",
  "risk_score": 34,
  "risk_level": "Suspicious",
  "permission_risk_score": 14,
  "permission_risk_level": "Safe",
  "permissions_detected": 31,
  "dangerous_permission_count": 12,
  "safe_permission_count": 4,
  "confidence": 0.86,
  "band_range": "31-70",
  "model_name": "RandomForestClassifier",
  "mode": "APK Analysis Mode",
  "integration_note": "Overall risk raised from Safe to Suspicious due to install source (APK sideload)."
}
```

Explain: the backend extracted 31 manifest permissions from a real APK. Its
permission-model score was 14 (`Safe`), but the sideload source added 20 points,
making the combined score 34 (`Suspicious`). This is a useful demonstration that
the final assessment integrates model output with install-source context. Do not
describe this result as proof that the APK is malicious.

### If Swagger reports an error parsing the body

The response below occurs before `/upload-apk` runs and means Swagger's
multipart form body was not parsed successfully:

```json
{
  "detail": "There was an error parsing the body"
}
```

The backend is configured to spool multipart data and temporary APKs under
`.runtime/tmp` on the project drive. If the server was already running before
this configuration was added, use this recovery procedure once:

1. Stop Uvicorn with `Ctrl+C`.
2. Confirm the upload dependency with
   `python -m pip show python-multipart`. The pinned version is `0.0.32`.
3. Restart without auto-reload for the demo:
   `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`.
4. Hard-refresh Swagger at `http://127.0.0.1:8000/docs` with `Ctrl+F5`.
5. Open `POST /upload-apk`, select **Try it out**, use the file chooser to
   reselect `youcine (1).apk`, and enter `apk_sideload` as the source. Do not
   paste the file path into a text field or manually set a content-type header.
6. Select **Execute** once and wait for the response.

If the same parser error remains, proceed immediately to the fallback below so
the upload does not interrupt the rest of the presentation.

## 11. APK upload fallback

If file selection, multipart upload, or APK parsing fails during the live demo:

1. State that APK upload performs two stages: manifest permission extraction,
   followed by the existing permission-model and explanation pipeline.
2. Show `GET /health` again to establish that the API and models remain loaded.
3. Return to `POST /analyze/apk`.
4. Paste the high-risk JSON from section 7 and execute it.
5. Explain the real `permission_risk_score` of 70, the 28 unknown-source points,
   and the real combined `High Risk` score of 98.
6. Continue with the notification examples if they have not yet been shown.

This fallback bypasses only file transfer and manifest parsing. It still
demonstrates the actual APK permission model, risk integration, and explanation
engine using the current backend and saved model artifacts.

## Presentation wording

Use phrases such as "the current model classified this sample as..." and "the
current rules added source-risk points...". Avoid claiming that any single result
proves an app is completely safe or definitely malicious. The system is a
decision-support prototype based on permissions, notification text, and install
source.

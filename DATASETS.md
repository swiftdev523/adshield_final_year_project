# Datasets for the Android Risk Analyzer

## Already added to this workspace

### 1. APK permission/risk dataset
- Source file: `computer and security_2.xlsx`
- Purpose: baseline APK risk classification using permission and related static features.
- Labels used in the current pipeline:
  - `Google play store` -> benign (`0`)
  - `Malware Applications` -> malicious (`1`)
  - `Third party` -> malicious (`1`)

### 2. Notification spam baseline dataset
- Source file: `data/sms_spam_collection/SMSSpamCollection`
- Origin: UCI SMS Spam Collection.
- Purpose: baseline text classifier for suspicious notification content, phishing-style prompts, and message spam.
- Important note: this is useful as an initial notification-spam proxy, but it is not a true Android notification dataset. For production-quality notification detection, you should later collect real notification text samples from device logs or app telemetry with user consent.

## What your APK dataset needs

For an explainable APK pre-installation risk analyzer, the dataset should ideally include:

- `apk_id`: package name or sample id.
- `label`: benign, adware, riskware, trojan, etc.
- `source`: Google Play, third-party market, malware feed, internal collection.
- Static permissions: requested permissions and permission groups.
- Manifest signals: receivers, services, exported components, intent filters.
- Code/API signals: sensitive API usage, reflection, dynamic loading, SMS/call/location use.
- Network signals: domains, sockets, URLs, ad SDK indicators if available.
- Family/category labels: especially useful for explanation and threat grouping.
- Timestamp or collection period: important for temporal split evaluation.

## What your notification-spam dataset needs

For non-technical users, the dataset should ideally include:

- `text`: the notification content shown to the user.
- `title`: notification title.
- `app_name` or `package_name`: source app.
- `label`: safe, promotional, suspicious, phishing, scam, malware-related, urgent/deceptive.
- `language`: useful if you expect multilingual users.
- `actionability`: whether the notification tries to trigger install, payment, login, permission grant, or external download.
- Optional explanation fields: scam cue, urgency cue, impersonation cue, money cue, credential-harvest cue.

## Recommended next external datasets

### 1. Drebin
- Strong fit for explainable Android malware research.
- Includes malware samples and is widely used in explainable Android malware papers.
- Access is controlled, so you must request it from the maintainers.

### 2. CCCS-CIC-AndMal-2020
- Large Android malware dataset with 400K apps and malware family/category information.
- Particularly useful if you want stronger malware category coverage such as adware, trojan-sms, riskware, and ransomware.

### 3. AndroZoo
- Very large APK collection useful for sourcing benign apps and broader APK metadata.
- Access requires an API key, and downloads are done by SHA256.

## Suggested model split for your project

- APK risk model:
  - Inputs: permissions, manifest features, API groups, app metadata.
  - Outputs: benign vs risky, plus optional subclass such as adware/riskware/trojan.
  - Explainability: top permissions/APIs and human-readable reasons.

- Notification spam model:
  - Inputs: title + body text + app name.
  - Outputs: safe, promo, suspicious, phishing/scam.
  - Explainability: suspicious phrases, urgency words, financial bait, impersonation cues.

## Local workflow now available

- Build cached APK dataset:
  - `python prepare_apk_dataset.py`
- Build cached APK dataset from the full workbook:
  - `set FULL_DATASET=1 && python prepare_apk_dataset.py`
- Train APK model:
  - `python train_model1.py`
- Train notification spam model:
  - `python train_notification_spam_model.py`

If the full workbook is used, run the cache step first so training does not repeatedly parse the Excel file.

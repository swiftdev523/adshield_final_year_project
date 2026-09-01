# Kali Banking/SMS Static-Extraction Handoff

## Scope and evidence boundary

This report hands off the Banking Malware and SMS Malware static-extraction results produced in the isolated Kali Linux project. Its purpose is to provide package-unseen, manifest-permission candidate pools for later holdout construction without executing Android code or generating malware-category predictions.

Here, **package-unseen** means absent from the supplied historical split manifest under the recorded historical-comparison normalization. It does not claim that a package is globally unseen outside this project.

The report is based only on these generated artifacts:

- `output/audit_summary.json`
- `output/apk_audit.csv`
- `output/banking_unique_candidates.csv`
- `output/sms_unique_candidates.csv`
- `output/unique_candidate_summary.json`
- Generated artifact hash records

No raw APK was accessed or parsed while creating this report.

## Extraction and candidate results

| Category | Eligible APK rows before package deduplication | Unique eligible packages and retained candidate rows | Rows removed by package deduplication |
|---|---:|---:|---:|
| Banking Malware | 514 | 157 | 357 |
| SMS Malware | 59 | 49 | 10 |
| Combined | 573 | 206 | 367 |

The combined unique candidate pool therefore contains **206 rows representing 206 normalized packages**. Banking and SMS normalized-package sets have an intersection of zero.

## Eligibility and integrity verification

### Historical package overlap

- Banking unique candidates with historical overlap: **0**
- SMS unique candidates with historical overlap: **0**
- Combined historical-overlap candidate rows: **0**

Historical overlap was evaluated during the audit against all 4,000 rows in `split_manifest.csv`, containing 3,022 distinct nonblank historical packages. The historical comparison contract stripped surrounding whitespace and preserved case. Only audit rows already marked `eligible_holdout=true` were admitted to the unique pools.

### Duplicate SHA-256

- Banking duplicate SHA-256 values in the unique pool: **0**
- SMS duplicate SHA-256 values in the unique pool: **0**
- Duplicate SHA-256 values across both unique outputs: **0**

The full audit identified 74 rows belonging to duplicate-hash groups. Those rows were not eligible and do not appear in either unique candidate pool. Every retained candidate has a nonblank lowercase 64-hex SHA-256 value.

### Cross-category conflicts

- Cross-category package-conflict rows in the Banking unique pool: **0**
- Cross-category package-conflict rows in the SMS unique pool: **0**
- Case-folded package identities shared by the two unique pools: **0**
- Cross-category hash-conflict rows in either unique pool: **0**
- SHA-256 values shared by the two unique pools: **0**

For context, the full audit recorded 240 cross-category package-conflict rows and zero cross-category hash-conflict rows. Conflict rows were excluded by the eligibility rules and are absent from the transferred candidate pools.

### Feature-vector verification

Both candidate CSVs retain the same 176-column layout as `apk_audit.csv`: 23 audit metadata fields followed by the exact ordered 153 permission-feature columns. All retained feature values are binary, all vectors contain exactly 153 ordered values, and every vector sum matches `matched_schema_permission_count`.

## Normalization and representative selection

### Permission normalization

The exact permission normalization rule recorded by the audit is:

```python
permission.strip().rsplit('.', 1)[-1].upper()
```

The ordered feature contract contains 153 unique permission columns. Its source-contract SHA-256 is:

```text
9bbbdbf826db7957a0335baefa93eb8bc3440c4edcf7f5825cccf949a105a4fd
```

### Package normalization

Two package-normalization contexts must remain distinct:

1. Historical-overlap auditing used: **strip surrounding whitespace and preserve case**.
2. Unique candidate identity used exactly:

```python
package.strip().casefold()
```

The `normalized_package` value in each unique-candidate output is the second, case-folded identity.

### Representative selection

Only rows already marked `eligible_holdout=true` were considered. For each category and each `package.strip().casefold()` identity, exactly one representative was retained. If multiple eligible rows shared that identity, the retained representative was the row with the **lexicographically smallest SHA-256**. Output ordering is deterministic by normalized package and then SHA-256.

## Exact ordered 153-feature schema

The following is the exact feature order preserved as the final 153 columns of both candidate CSVs:

```text
001. android.permission.ACCESS_ALL_DOWNLOADS
002. android.permission.ACCESS_CACHE_FILESYSTEM
003. android.permission.ACCESS_CHECKIN_PROPERTIES
004. android.permission.ACCESS_COARSE_LOCATION
005. android.permission.ACCESS_COARSE_UPDATES
006. android.permission.ACCESS_FINE_LOCATION
007. android.permission.ACCESS_LOCATION_EXTRA_COMMANDS
008. android.permission.ACCESS_MOCK_LOCATION
009. android.permission.ACCESS_MTK_MMHW
010. android.permission.ACCESS_NETWORK_STATE
011. android.permission.ACCESS_SUPERUSER
012. android.permission.ACCESS_SURFACE_FLINGER
013. android.permission.ACCESS_WIFI_STATE
014. android.permission.ACCOUNT_MANAGER
015. android.permission.AUTHENTICATE_ACCOUNTS
016. android.permission.BATTERY_STATS
017. android.permission.BILLING
018. android.permission.BIND_ACCESSIBILITY_SERVICE
019. android.permission.BIND_APPWIDGET
020. android.permission.BIND_DEVICE_ADMIN
021. android.permission.BIND_INPUT_METHOD
022. android.permission.BIND_REMOTEVIEWS
023. android.permission.BIND_WALLPAPER
024. android.permission.BLUETOOTH
025. android.permission.BLUETOOTH_ADMIN
026. android.permission.BLUETOOTH_PRIVILEGED
027. android.permission.BODY_SENSORS
028. android.permission.BRICK
029. android.permission.BROADCAST_PACKAGE_REMOVED
030. android.permission.BROADCAST_SMS
031. android.permission.BROADCAST_STICKY
032. android.permission.BROADCAST_WAP_PUSH
033. android.permission.C2D_MESSAGE
034. android.permission.CALL_PHONE
035. android.permission.CALL_PRIVILEGED
036. android.permission.CAMERA
037. android.permission.CAPTURE_AUDIO_OUTPUT
038. android.permission.CAPTURE_SECURE_VIDEO_OUTPUT
039. android.permission.CAPTURE_VIDEO_OUTPUT
040. android.permission.CHANGE_COMPONENT_ENABLED_STATE
041. android.permission.CHANGE_CONFIGURATION
042. android.permission.CHANGE_NETWORK_STATE
043. android.permission.CHANGE_WIFI_MULTICAST_STATE
044. android.permission.CHANGE_WIFI_STATE
045. android.permission.CLEAR_APP_CACHE
046. android.permission.CLEAR_APP_USER_DATA
047. android.permission.CONTROL_LOCATION_UPDATES
048. android.permission.DELETE_CACHE_FILES
049. android.permission.DELETE_PACKAGES
050. android.permission.DEVICE_POWER
051. android.permission.DISABLE_KEYGUARD
052. android.permission.DUMP
053. android.permission.EXPAND_STATUS_BAR
054. android.permission.FLASHLIGHT
055. android.permission.FORCE_BACK
056. android.permission.GET_ACCOUNTS
057. android.permission.GET_PACKAGE_SIZE
058. android.permission.GET_TASKS
059. android.permission.GET_TOP_ACTIVITY_INFO
060. android.permission.GLOBAL_SEARCH
061. android.permission.HARDWARE_TEST
062. android.permission.INJECT_EVENTS
063. android.permission.INSTALL_LOCATION_PROVIDER
064. android.permission.INSTALL_PACKAGES
065. android.permission.INSTALL_SHORTCUT
066. android.permission.INTERACT_ACROSS_USERS
067. android.permission.INTERNAL_SYSTEM_WINDOW
068. android.permission.INTERNET
069. android.permission.KILL_BACKGROUND_PROCESSES
070. android.permission.MANAGE_ACCOUNTS
071. android.permission.MANAGE_APP_TOKENS
072. android.permission.MANAGE_DOCUMENTS
073. android.permission.MASTER_CLEAR
074. android.permission.MEDIA_CONTENT_CONTROL
075. android.permission.MODIFY_AUDIO_SETTINGS
076. android.permission.MODIFY_PHONE_STATE
077. android.permission.MOUNT_FORMAT_FILESYSTEMS
078. android.permission.MOUNT_UNMOUNT_FILESYSTEMS
079. android.permission.NFC
080. android.permission.PERSISTENT_ACTIVITY
081. android.permission.PROCESS_OUTGOING_CALLS
082. android.permission.READ_CALENDAR
083. android.permission.READ_CALL_LOG
084. android.permission.READ_CONTACTS
085. android.permission.READ_EXTERNAL_STORAGE
086. android.permission.READ_FRAME_BUFFER
087. android.permission.READ_HISTORY_BOOKMARKS
088. android.permission.READ_INPUT_STATE
089. android.permission.READ_LOGS
090. android.permission.READ_OWNER_DATA
091. android.permission.READ_PHONE_STATE
092. android.permission.READ_PROFILE
093. android.permission.READ_SETTINGS
094. android.permission.READ_SMS
095. android.permission.READ_SOCIAL_STREAM
096. android.permission.READ_SYNC_SETTINGS
097. android.permission.READ_SYNC_STATS
098. android.permission.READ_USER_DICTIONARY
099. android.permission.REBOOT
100. android.permission.RECEIVE_BOOT_COMPLETED
101. android.permission.RECEIVE_MMS
102. android.permission.RECEIVE_SMS
103. android.permission.RECEIVE_USER_PRESENT
104. android.permission.RECEIVE_WAP_PUSH
105. android.permission.RECORD_AUDIO
106. android.permission.REORDER_TASKS
107. android.permission.RESTART_PACKAGES
108. android.permission.SEND_RESPOND_VIA_MESSAGE
109. android.permission.SEND_SMS
110. android.permission.SET_ACTIVITY_WATCHER
111. android.permission.SET_ALWAYS_FINISH
112. android.permission.SET_ANIMATION_SCALE
113. android.permission.SET_DEBUG_APP
114. android.permission.SET_ORIENTATION
115. android.permission.SET_POINTER_SPEED
116. android.permission.SET_PREFERRED_APPLICATIONS
117. android.permission.SET_PROCESS_LIMIT
118. android.permission.SET_TIME
119. android.permission.SET_TIME_ZONE
120. android.permission.SET_WALLPAPER
121. android.permission.SET_WALLPAPER_HINTS
122. android.permission.SIGNAL_PERSISTENT_PROCESSES
123. android.permission.STATUS_BAR
124. android.permission.STORAGE
125. android.permission.SUBSCRIBED_FEEDS_READ
126. android.permission.SUBSCRIBED_FEEDS_WRITE
127. android.permission.SYSTEM_ALERT_WINDOW
128. android.permission.TRANSMIT_IR
129. android.permission.UPDATE_DEVICE_STATS
130. android.permission.USES_POLICY_FORCE_LOCK
131. android.permission.USE_CREDENTIALS
132. android.permission.USE_FINGERPRINT
133. android.permission.USE_SIP
134. android.permission.VIBRATE
135. android.permission.WAKE_LOCK
136. android.permission.WRITE
137. android.permission.WRITE_APN_SETTINGS
138. android.permission.WRITE_CALENDAR
139. android.permission.WRITE_CALL_LOG
140. android.permission.WRITE_CONTACTS
141. android.permission.WRITE_EXTERNAL_STORAGE
142. android.permission.WRITE_GSERVICES
143. android.permission.WRITE_HISTORY_BOOKMARKS
144. android.permission.WRITE_INTERNAL_STORAGE
145. android.permission.WRITE_MEDIA_STORAGE
146. android.permission.WRITE_OWNER_DATA
147. android.permission.WRITE_PROFILE
148. android.permission.WRITE_SECURE_SETTINGS
149. android.permission.WRITE_SETTINGS
150. android.permission.WRITE_SMS
151. android.permission.WRITE_SOCIAL_STREAM
152. android.permission.WRITE_SYNC_SETTINGS
153. android.permission.WRITE_USER_DICTIONARY
```

## Safety statement

The generated audit records the following:

- No APK code was executed.
- No APK was installed.
- No Android runtime or emulator was invoked.
- APK files were not modified.
- No archive member was extracted to disk.
- Only the root `AndroidManifest.xml` archive member was statically parsed.
- No malware-category ML model was loaded.
- No category prediction was generated.

The candidate-pool stage accessed only the generated audit CSV. It did not reopen raw APKs.

## Files to transfer to the Windows project

Transfer only the safe generated artifacts, scripts, reference metadata, and reproducibility records. Do **not** transfer the raw `Banking/`, `SMS/`, or `raw/` APK directories.

### Required candidate handoff

- `output/banking_unique_candidates.csv`
- `output/sms_unique_candidates.csv`
- `output/unique_candidate_summary.json`
- `output/audit_summary.json`
- `output/KALI_BANKING_SMS_HANDOFF.md`

### Recommended audit provenance

- `output/apk_audit.csv`
- `output/eligible_holdout_candidates.csv`
- `output/failed_apks.csv`
- `output/audit_summary.json`
- `output/full_audit_outputs_sha256.txt`
- `scripts/audit_apks.py`
- `scripts/build_unique_candidates.py`
- `scripts/requirements-audit.txt`
- `permission_features.json`
- `split_manifest.csv`
- `permission_mapping.py`
- `output/kali_candidate_artifacts_sha256.txt`
- Environment records and `SHA256SUMS.txt` from the timestamped `output/final_candidate_backup/` directory, if that backup has been created

The project-level `kali_candidate_artifacts_sha256.txt` lists a complete set of output, script, and reference paths. Strict `sha256sum -c` verification of that file therefore requires transferring all files it lists while preserving their project-relative layout. For a smaller candidate-only bundle, the candidate CSV hashes are also recorded in `unique_candidate_summary.json`.

Verify hashes before opening or resaving a CSV in spreadsheet software, which may change quoting, encodings, or line endings.

After transfer, verify the transferred backup from inside its directory with:

```bash
sha256sum -c SHA256SUMS.txt
```

## Current project status

No category-model predictions were generated. The Banking and SMS files described here are candidate pools only. The final balanced four-class holdout has **not** been selected.

## Artifact identifiers

- Source audit CSV SHA-256: `d97055c6a4b41afbd1b1bcb0d6bd7ac656b0020937e150e4fc1987ff72d220cc`
- Banking unique-candidate CSV SHA-256: `d491457a1bed4d00715f3132b8ad17b945c670678397fa1cb09a735cade14c49`
- SMS unique-candidate CSV SHA-256: `ea0b4a5136b878744aa7055592df9fae3da49325f62c472c209a937c5b3c2160`
- Permission-feature contract SHA-256: `9bbbdbf826db7957a0335baefa93eb8bc3440c4edcf7f5825cccf949a105a4fd`
- Historical split manifest SHA-256: `d14dd5eaece6b4772981aab800f17d919ee3dfb45abe00adb440b062ffa4cced`

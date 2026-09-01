package expo.modules.installedappmonitor

internal data class InstalledAppRecord(
  val appName: String,
  val packageName: String,
  val versionName: String?,
  val versionCode: Long,
  val firstInstallTime: Long,
  val lastUpdateTime: Long,
  val isSystemApp: Boolean,
  val isEnabled: Boolean,
  val requestedPermissions: List<String>,
  val installerPackageName: String?,
  val installSource: String,
  val installSourceDisplay: String,
) {
  val isUserInstalledApp: Boolean
    get() = !isSystemApp
}

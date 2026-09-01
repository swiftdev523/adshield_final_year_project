package expo.modules.installedappmonitor

internal object InstalledAppSerializer {
  fun serialize(app: InstalledAppRecord): Map<String, Any?> = mapOf(
    "appName" to app.appName,
    "packageName" to app.packageName,
    "versionName" to app.versionName,
    "versionCode" to app.versionCode.toDouble(),
    "firstInstallTime" to app.firstInstallTime.toDouble(),
    "lastUpdateTime" to app.lastUpdateTime.toDouble(),
    "isSystemApp" to app.isSystemApp,
    "isUserInstalledApp" to app.isUserInstalledApp,
    "isEnabled" to app.isEnabled,
    "requestedPermissions" to app.requestedPermissions,
    "installerPackageName" to app.installerPackageName,
    "installSource" to app.installSource,
    "installSourceDisplay" to app.installSourceDisplay,
    "totalPermissionCount" to app.requestedPermissions.size,
  )
}

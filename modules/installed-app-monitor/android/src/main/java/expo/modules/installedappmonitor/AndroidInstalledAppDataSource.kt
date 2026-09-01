package expo.modules.installedappmonitor

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build

internal class AndroidInstalledAppDataSource(
  private val context: Context,
) : InstalledAppDataSource {
  private val packageManager: PackageManager
    get() = context.packageManager

  override fun queryVisibleLauncherApps(): List<InstalledAppRecord> {
    val launcherIntent = Intent(Intent.ACTION_MAIN).apply {
      addCategory(Intent.CATEGORY_LAUNCHER)
    }

    return queryLauncherActivities(launcherIntent)
      .mapNotNull { it.activityInfo?.packageName }
      .distinct()
      .mapNotNull(::readPackage)
  }

  @Suppress("DEPRECATION")
  private fun queryLauncherActivities(intent: Intent) =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
      packageManager.queryIntentActivities(
        intent,
        PackageManager.ResolveInfoFlags.of(PackageManager.MATCH_ALL.toLong()),
      )
    } else {
      packageManager.queryIntentActivities(intent, PackageManager.MATCH_ALL)
    }

  private fun readPackage(packageName: String): InstalledAppRecord? {
    val packageInfo = try {
      getPackageInfo(packageName)
    } catch (_: PackageManager.NameNotFoundException) {
      return null
    }
    val applicationInfo = packageInfo.applicationInfo ?: return null
    val installerPackage = getInstallerPackageName(packageName)
    val installSource = InstallSourceMapper.fromInstaller(installerPackage)
    val isSystemApp = applicationInfo.flags and (
      ApplicationInfo.FLAG_SYSTEM or ApplicationInfo.FLAG_UPDATED_SYSTEM_APP
    ) != 0

    return InstalledAppRecord(
      appName = applicationInfo.loadLabel(packageManager).toString().ifBlank { packageName },
      packageName = packageName,
      versionName = packageInfo.versionName,
      versionCode = getVersionCode(packageInfo),
      firstInstallTime = packageInfo.firstInstallTime,
      lastUpdateTime = packageInfo.lastUpdateTime,
      isSystemApp = isSystemApp,
      isEnabled = applicationInfo.enabled,
      requestedPermissions = packageInfo.requestedPermissions
        ?.asSequence()
        ?.filter { it.isNotBlank() }
        ?.distinct()
        ?.sorted()
        ?.toList()
        ?: emptyList(),
      installerPackageName = installerPackage,
      installSource = installSource.value,
      installSourceDisplay = installSource.display,
    )
  }

  @Suppress("DEPRECATION")
  private fun getPackageInfo(packageName: String): PackageInfo =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
      packageManager.getPackageInfo(
        packageName,
        PackageManager.PackageInfoFlags.of(PackageManager.GET_PERMISSIONS.toLong()),
      )
    } else {
      packageManager.getPackageInfo(packageName, PackageManager.GET_PERMISSIONS)
    }

  @Suppress("DEPRECATION")
  private fun getVersionCode(packageInfo: PackageInfo): Long =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
      packageInfo.longVersionCode
    } else {
      packageInfo.versionCode.toLong()
    }

  @Suppress("DEPRECATION")
  private fun getInstallerPackageName(packageName: String): String? = try {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
      packageManager.getInstallSourceInfo(packageName).installingPackageName
    } else {
      packageManager.getInstallerPackageName(packageName)
    }
  } catch (_: Exception) {
    null
  }
}

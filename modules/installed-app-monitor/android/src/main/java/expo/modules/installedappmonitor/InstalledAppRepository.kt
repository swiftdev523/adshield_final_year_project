package expo.modules.installedappmonitor

import java.util.Locale

internal fun interface InstalledAppDataSource {
  fun queryVisibleLauncherApps(): List<InstalledAppRecord>
}

internal class InstalledAppRepository(
  private val dataSource: InstalledAppDataSource,
) {
  fun getInstalledApps(): List<Map<String, Any?>> = dataSource
    .queryVisibleLauncherApps()
    .distinctBy { it.packageName }
    .sortedWith(
      compareBy<InstalledAppRecord> { it.appName.lowercase(Locale.ROOT) }
        .thenBy { it.packageName.lowercase(Locale.ROOT) },
    )
    .map(InstalledAppSerializer::serialize)

  fun getInstalledApp(packageName: String): Map<String, Any?>? {
    val normalizedPackage = packageName.trim()
    if (normalizedPackage.isEmpty()) {
      return null
    }

    return dataSource
      .queryVisibleLauncherApps()
      .firstOrNull { it.packageName == normalizedPackage }
      ?.let(InstalledAppSerializer::serialize)
  }
}

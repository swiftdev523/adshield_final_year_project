package expo.modules.installedappmonitor

internal data class InstallSourceValue(
  val value: String,
  val display: String,
)

internal object InstallSourceMapper {
  private const val GOOGLE_PLAY_INSTALLER = "com.android.vending"

  private val packageInstallerNames = setOf(
    "com.android.packageinstaller",
    "com.google.android.packageinstaller",
    "com.google.android.permissioncontroller",
  )

  fun fromInstaller(installerPackageName: String?): InstallSourceValue {
    val normalized = installerPackageName?.trim()?.lowercase()
    return when {
      normalized == GOOGLE_PLAY_INSTALLER -> InstallSourceValue(
        value = "google_play_store",
        display = "Google Play Store",
      )
      normalized in packageInstallerNames -> InstallSourceValue(
        value = "apk_sideload",
        display = "APK sideload",
      )
      else -> InstallSourceValue(
        value = "unknown_source",
        display = "Unknown source",
      )
    }
  }
}

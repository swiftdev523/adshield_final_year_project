package expo.modules.installedappmonitor

import org.junit.Assert.assertEquals
import org.junit.Test

class InstallSourceMapperTest {
  @Test
  fun `maps Google Play conservatively`() {
    val source = InstallSourceMapper.fromInstaller("com.android.vending")
    assertEquals("google_play_store", source.value)
    assertEquals("Google Play Store", source.display)
  }

  @Test
  fun `maps known package installer to sideload`() {
    val source = InstallSourceMapper.fromInstaller("com.google.android.packageinstaller")
    assertEquals("apk_sideload", source.value)
    assertEquals("APK sideload", source.display)
  }

  @Test
  fun `falls back to unknown for null or unrecognized installers`() {
    assertEquals("unknown_source", InstallSourceMapper.fromInstaller(null).value)
    assertEquals(
      "unknown_source",
      InstallSourceMapper.fromInstaller("com.example.other.store").value,
    )
  }
}

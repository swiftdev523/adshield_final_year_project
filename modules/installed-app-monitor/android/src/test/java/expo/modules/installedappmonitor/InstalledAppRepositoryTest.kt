package expo.modules.installedappmonitor

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class InstalledAppRepositoryTest {
  private fun app(
    appName: String = "Example",
    packageName: String = "com.example.app",
    isSystemApp: Boolean = false,
    permissions: List<String> = listOf("android.permission.INTERNET"),
  ) = InstalledAppRecord(
    appName = appName,
    packageName = packageName,
    versionName = "1.2.3",
    versionCode = 42,
    firstInstallTime = 1_000,
    lastUpdateTime = 2_000,
    isSystemApp = isSystemApp,
    isEnabled = true,
    requestedPermissions = permissions,
    installerPackageName = "com.android.vending",
    installSource = "google_play_store",
    installSourceDisplay = "Google Play Store",
  )

  @Test
  fun `serializes the complete observable contract`() {
    val serialized = InstalledAppSerializer.serialize(app())

    assertEquals("Example", serialized["appName"])
    assertEquals("com.example.app", serialized["packageName"])
    assertEquals("1.2.3", serialized["versionName"])
    assertEquals(42.0, serialized["versionCode"])
    assertEquals(1_000.0, serialized["firstInstallTime"])
    assertEquals(2_000.0, serialized["lastUpdateTime"])
    assertEquals(false, serialized["isSystemApp"])
    assertEquals(true, serialized["isUserInstalledApp"])
    assertEquals(true, serialized["isEnabled"])
    assertEquals(listOf("android.permission.INTERNET"), serialized["requestedPermissions"])
    assertEquals("com.android.vending", serialized["installerPackageName"])
    assertEquals("google_play_store", serialized["installSource"])
    assertEquals("Google Play Store", serialized["installSourceDisplay"])
    assertEquals(1, serialized["totalPermissionCount"])
  }

  @Test
  fun `enumerates visible apps in stable order and removes duplicate packages`() {
    val repository = InstalledAppRepository {
      listOf(
        app(appName = "Zulu", packageName = "com.example.zulu"),
        app(appName = "Alpha", packageName = "com.example.alpha"),
        app(appName = "Duplicate", packageName = "com.example.zulu"),
      )
    }

    val result = repository.getInstalledApps()

    assertEquals(2, result.size)
    assertEquals("com.example.alpha", result[0]["packageName"])
    assertEquals("com.example.zulu", result[1]["packageName"])
  }

  @Test
  fun `returns an empty list when no launcher apps are visible`() {
    val repository = InstalledAppRepository { emptyList() }
    assertTrue(repository.getInstalledApps().isEmpty())
  }

  @Test
  fun `propagates data source failure for the native promise`() {
    val repository = InstalledAppRepository {
      throw IllegalStateException("PackageManager unavailable")
    }

    assertThrows(IllegalStateException::class.java) {
      repository.getInstalledApps()
    }
  }

  @Test
  fun `preserves system and user app distinction`() {
    val system = InstalledAppSerializer.serialize(app(isSystemApp = true))
    val user = InstalledAppSerializer.serialize(app(isSystemApp = false))

    assertTrue(system["isSystemApp"] as Boolean)
    assertFalse(system["isUserInstalledApp"] as Boolean)
    assertFalse(user["isSystemApp"] as Boolean)
    assertTrue(user["isUserInstalledApp"] as Boolean)
  }

  @Test
  fun `preserves declared permissions and their count`() {
    val permissions = listOf(
      "android.permission.CAMERA",
      "android.permission.INTERNET",
    )
    val serialized = InstalledAppSerializer.serialize(app(permissions = permissions))

    assertEquals(permissions, serialized["requestedPermissions"])
    assertEquals(2, serialized["totalPermissionCount"])
  }

  @Test
  fun `returns only the selected visible package`() {
    val repository = InstalledAppRepository {
      listOf(
        app(packageName = "com.example.one"),
        app(packageName = "com.example.two"),
      )
    }

    assertEquals("com.example.two", repository.getInstalledApp("com.example.two")?.get("packageName"))
    assertNull(repository.getInstalledApp("com.example.missing"))
    assertNull(repository.getInstalledApp("  "))
  }
}

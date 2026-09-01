package expo.modules.installedappmonitor

import android.content.Context
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.functions.Coroutine
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import kotlinx.coroutines.withContext

class InstalledAppMonitorModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw Exceptions.AppContextLost()

  private fun repository() = InstalledAppRepository(
    AndroidInstalledAppDataSource(context),
  )

  override fun definition() = ModuleDefinition {
    Name("InstalledAppMonitor")

    AsyncFunction("getInstalledApps").Coroutine<List<Map<String, Any?>>> {
      withContext(appContext.backgroundCoroutineScope.coroutineContext) {
        repository().getInstalledApps()
      }
    }

    AsyncFunction("getInstalledApp").Coroutine<Map<String, Any?>?, String> { packageName ->
      withContext(appContext.backgroundCoroutineScope.coroutineContext) {
        repository().getInstalledApp(packageName)
      }
    }

    AsyncFunction("refreshInstalledApps").Coroutine<List<Map<String, Any?>>> {
      withContext(appContext.backgroundCoroutineScope.coroutineContext) {
        repository().getInstalledApps()
      }
    }
  }
}

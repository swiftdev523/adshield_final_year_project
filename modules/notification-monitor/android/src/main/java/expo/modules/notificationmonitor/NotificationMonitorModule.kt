package expo.modules.notificationmonitor

import android.content.Context
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.functions.Coroutine
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import kotlinx.coroutines.withContext

class NotificationMonitorModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw Exceptions.AppContextLost()

  private fun repository(): NotificationHistoryRepository =
    NotificationRepositoryProvider.get(context)

  override fun definition() = ModuleDefinition {
    Name("NotificationMonitor")

    AsyncFunction("hasNotificationAccess") {
      NotificationAccessController.hasAccess(context).also { granted ->
        if (granted) NotificationAccessController.requestRebind(context)
      }
    }

    AsyncFunction("openNotificationAccessSettings") {
      NotificationAccessController.openSettings(context)
    }

    AsyncFunction("getNotificationSummary").Coroutine<List<Map<String, Any?>>> {
      withContext(appContext.backgroundCoroutineScope.coroutineContext) {
        repository().getNotificationSummary().map(NotificationSerializer::serializeSummary)
      }
    }

    AsyncFunction("getRecentNotifications").Coroutine<List<Map<String, Any?>>, Int?> { limit ->
      withContext(appContext.backgroundCoroutineScope.coroutineContext) {
        repository().getRecentNotifications(limit).map(NotificationSerializer::serializeEvent)
      }
    }

    AsyncFunction("getNotificationAnalysisText").Coroutine<Map<String, Any?>, String> { eventKey ->
      withContext(appContext.backgroundCoroutineScope.coroutineContext) {
        val record = repository().getNotificationAnalysisText(eventKey)
          ?: throw IllegalStateException("Notification event is not eligible or is no longer available")
        NotificationSerializer.serializeAnalysisText(record)
      }
    }

    AsyncFunction("clearLocalNotificationHistory").Coroutine<Unit> {
      withContext(appContext.backgroundCoroutineScope.coroutineContext) {
        repository().clearLocalNotificationHistory()
      }
    }
  }
}

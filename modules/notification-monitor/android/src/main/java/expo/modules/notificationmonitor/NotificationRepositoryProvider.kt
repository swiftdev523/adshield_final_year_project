package expo.modules.notificationmonitor

import android.content.Context

internal object NotificationRepositoryProvider {
  @Volatile
  private var repository: NotificationHistoryRepository? = null

  fun get(context: Context): NotificationHistoryRepository = repository ?: synchronized(this) {
    repository ?: NotificationHistoryRepository(
      NotificationHistoryStore(context.applicationContext),
    ).also { repository = it }
  }
}

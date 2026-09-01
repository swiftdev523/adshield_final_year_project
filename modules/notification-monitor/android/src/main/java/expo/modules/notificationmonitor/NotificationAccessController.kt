package expo.modules.notificationmonitor

import android.app.NotificationManager
import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import android.service.notification.NotificationListenerService

internal object NotificationAccessController {
  fun hasAccess(context: Context): Boolean {
    val listener = ComponentName(context, AdShieldNotificationListenerService::class.java)
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
      val manager = context.getSystemService(NotificationManager::class.java)
      return manager?.isNotificationListenerAccessGranted(listener) == true
    }

    val enabled = Settings.Secure.getString(
      context.contentResolver,
      "enabled_notification_listeners",
    )
    return enabled
      ?.split(':')
      ?.asSequence()
      ?.mapNotNull(ComponentName::unflattenFromString)
      ?.any { it == listener }
      ?: false
  }

  fun requestRebind(context: Context) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return

    NotificationListenerService.requestRebind(
      ComponentName(context, AdShieldNotificationListenerService::class.java),
    )
  }

  fun openSettings(context: Context) {
    val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
      addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    try {
      context.startActivity(intent)
    } catch (_: ActivityNotFoundException) {
      context.startActivity(
        Intent(Settings.ACTION_SETTINGS).apply {
          addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        },
      )
    }
  }
}

package expo.modules.notificationmonitor

import android.app.Notification
import android.content.pm.PackageManager
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class AdShieldNotificationListenerService : NotificationListenerService() {
  override fun onNotificationPosted(statusBarNotification: StatusBarNotification?) {
    val posted = statusBarNotification ?: return
    val notification = posted.notification ?: return
    if (
      !NotificationObservationPolicy.shouldObserve(
        sourcePackage = posted.packageName,
        ownPackage = packageName,
      )
    ) return

    val extras = notification.extras
    // Deliberately omit EXTRA_TITLE and messaging sender/person metadata. The
    // classifier receives only the body Android exposes for this one event.
    val text = extras?.getCharSequence(Notification.EXTRA_BIG_TEXT)
      ?.takeIf { it.isNotBlank() }
      ?: extras?.getCharSequence(Notification.EXTRA_TEXT)
    val flags = notification.flags
    val metadata = NotificationSemanticMetadata(
      category = notification.category,
      isOngoing = flags and Notification.FLAG_ONGOING_EVENT != 0,
      isForegroundService = flags and Notification.FLAG_FOREGROUND_SERVICE != 0,
      isGroupSummary = flags and Notification.FLAG_GROUP_SUMMARY != 0,
      hasProgress = extras?.let {
        it.getBoolean(Notification.EXTRA_PROGRESS_INDETERMINATE, false) ||
          (it.containsKey(Notification.EXTRA_PROGRESS_MAX) &&
            it.getInt(Notification.EXTRA_PROGRESS_MAX, 0) > 0)
      } == true,
    )
    val content = NotificationContentSanitizer.sanitize(
      rawText = text?.toString(),
      category = notification.category,
      visibility = notification.visibility,
    )
    val keyHash = NotificationKeyHasher.sha256(posted.key)
    val sourcePackage = posted.packageName
    val sourceAppName = resolveAppName(sourcePackage)

    // Listener callbacks must never crash because local history cannot be read
    // or written. Notification text and keys are deliberately not logged.
    runCatching {
      NotificationRepositoryProvider.get(applicationContext).recordPosted(
        notificationKeyHash = keyHash,
        packageName = sourcePackage,
        appName = sourceAppName,
        content = content,
        metadata = metadata,
        // The hash is internal and lets a redacted or URL-sanitized body
        // revision get a fresh event key without persisting another raw copy.
        revisionFingerprint = text?.toString()?.let(NotificationKeyHasher::sha256),
      )
    }
  }

  override fun onNotificationRemoved(statusBarNotification: StatusBarNotification?) {
    val removed = statusBarNotification ?: return
    if (removed.packageName == packageName) return
    val keyHash = NotificationKeyHasher.sha256(removed.key)

    runCatching {
      NotificationRepositoryProvider.get(applicationContext).recordRemoved(keyHash)
    }
  }

  @Suppress("DEPRECATION")
  private fun resolveAppName(sourcePackage: String): String = try {
    val applicationInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
      packageManager.getApplicationInfo(
        sourcePackage,
        PackageManager.ApplicationInfoFlags.of(0),
      )
    } else {
      packageManager.getApplicationInfo(sourcePackage, 0)
    }
    packageManager.getApplicationLabel(applicationInfo).toString().ifBlank { sourcePackage }
  } catch (_: PackageManager.NameNotFoundException) {
    sourcePackage
  }
}

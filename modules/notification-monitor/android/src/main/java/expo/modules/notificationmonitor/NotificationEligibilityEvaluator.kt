package expo.modules.notificationmonitor

import android.app.Notification
import java.util.Locale

/**
 * Decides whether one notification event contains suitable text for the
 * existing SMS-spam classifier. This is deliberately package-neutral: app
 * identity is never an input.
 */
internal object NotificationEligibilityEvaluator {
  private const val MAX_GENERIC_STATUS_CODE_POINTS = 80

  private val checkingOrSyncing = Regex(
    "^(?:checking|syncing)(?:\\s+for)?\\s+(?:new\\s+)?(?:messages?|mail|notifications?)$",
  )
  private val possibleNewItems = Regex(
    "^you\\s+may\\s+have\\s+(?:new\\s+)?(?:messages?|mail|notifications?)$",
  )
  private val backgroundService = Regex(
    "^(?:running\\s+in\\s+(?:the\\s+)?background|service\\s+(?:is\\s+)?running|background\\s+service\\s+(?:is\\s+)?running)$",
  )
  private val operationInProgress = Regex(
    "^(?:backup|sync)\\s+(?:is\\s+)?in\\s+progress$",
  )
  private val waitingForConnection = Regex(
    "^(?:waiting\\s+for|connecting\\s+to)\\s+(?:the\\s+)?(?:network|internet)$",
  )
  private val connectionState = Regex("^(?:connected|disconnected)$")

  fun evaluate(
    content: SanitizedNotificationContent,
    metadata: NotificationSemanticMetadata?,
  ): NotificationEligibilityReason {
    if (metadata == null) return NotificationEligibilityReason.METADATA_UNAVAILABLE

    if (metadata.isGroupSummary) return NotificationEligibilityReason.GROUP_SUMMARY
    if (metadata.isForegroundService) return NotificationEligibilityReason.FOREGROUND_SERVICE
    if (metadata.hasProgress || metadata.category == Notification.CATEGORY_PROGRESS) {
      return NotificationEligibilityReason.PROGRESS_NOTIFICATION
    }
    if (metadata.isOngoing) return NotificationEligibilityReason.ONGOING_NOTIFICATION
    if (metadata.category == Notification.CATEGORY_SERVICE) {
      return NotificationEligibilityReason.SERVICE_NOTIFICATION
    }

    when (content.state) {
      NotificationContentState.SENSITIVE_REDACTED -> {
        return NotificationEligibilityReason.SENSITIVE_CONTENT
      }
      NotificationContentState.LEGACY_REDACTED -> {
        return NotificationEligibilityReason.METADATA_UNAVAILABLE
      }
      NotificationContentState.EMPTY -> return NotificationEligibilityReason.EMPTY_CONTENT
      NotificationContentState.AVAILABLE -> Unit
    }

    val text = content.analysisText
    if (text.isNullOrBlank()) return NotificationEligibilityReason.EMPTY_CONTENT
    if (isGenericOperationalStatus(text)) {
      return NotificationEligibilityReason.GENERIC_BACKGROUND_STATUS
    }

    return NotificationEligibilityReason.MEANINGFUL_CONTENT
  }

  internal fun isGenericOperationalStatus(text: String): Boolean {
    if (text.codePointCount(0, text.length) > MAX_GENERIC_STATUS_CODE_POINTS) return false

    val canonical = text
      .lowercase(Locale.ROOT)
      .trim()
      .trimEnd('.', '\u2026', '!', ':')
      .trim()

    return checkingOrSyncing.matches(canonical) ||
      possibleNewItems.matches(canonical) ||
      backgroundService.matches(canonical) ||
      operationInProgress.matches(canonical) ||
      waitingForConnection.matches(canonical) ||
      connectionState.matches(canonical)
  }
}

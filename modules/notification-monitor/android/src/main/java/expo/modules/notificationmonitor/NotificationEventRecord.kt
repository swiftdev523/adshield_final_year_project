package expo.modules.notificationmonitor

internal enum class NotificationContentState(val wireValue: String) {
  AVAILABLE("available"),
  EMPTY("empty"),
  SENSITIVE_REDACTED("sensitive_redacted"),
  LEGACY_REDACTED("legacy_redacted");

  companion object {
    fun fromWireValue(value: String): NotificationContentState? = entries
      .firstOrNull { it.wireValue == value }
  }
}

internal data class SanitizedNotificationContent(
  val analysisText: String?,
  val state: NotificationContentState,
)

internal data class NotificationSemanticMetadata(
  val category: String?,
  val isOngoing: Boolean,
  val isForegroundService: Boolean,
  val isGroupSummary: Boolean,
  val hasProgress: Boolean,
)

internal enum class NotificationEligibilityReason(
  val wireValue: String,
  val eligible: Boolean,
) {
  MEANINGFUL_CONTENT("meaningful_content", true),
  EMPTY_CONTENT("empty_content", false),
  SENSITIVE_CONTENT("sensitive_content", false),
  ONGOING_NOTIFICATION("ongoing_notification", false),
  FOREGROUND_SERVICE("foreground_service", false),
  PROGRESS_NOTIFICATION("progress_notification", false),
  GROUP_SUMMARY("group_summary", false),
  SERVICE_NOTIFICATION("service_notification", false),
  GENERIC_BACKGROUND_STATUS("generic_background_status", false),
  METADATA_UNAVAILABLE("metadata_unavailable", false);

  companion object {
    fun fromWireValue(value: String): NotificationEligibilityReason? = entries
      .firstOrNull { it.wireValue == value }
  }
}

internal data class NotificationEventRecord(
  val eventKey: String,
  val notificationKeyHash: String,
  val packageName: String,
  val appName: String,
  val postedAt: Long,
  val updatedAt: Long,
  val removedAt: Long?,
  val analysisText: String?,
  val contentState: NotificationContentState,
  val contentFingerprint: String?,
  val revisionFingerprint: String?,
  val metadata: NotificationSemanticMetadata?,
  val eligibilityReason: NotificationEligibilityReason,
)

internal data class NotificationAppSummaryRecord(
  val packageName: String,
  val appName: String,
  val totalObserved: Int,
  val eligibleCount: Int,
  val skippedCount: Int,
  val latestNotificationAt: Long,
  val latestEligibleEventKey: String?,
)

internal data class NotificationAnalysisTextRecord(
  val eventKey: String,
  val packageName: String,
  val postedAt: Long,
  val updatedAt: Long,
  val contentFingerprint: String,
  val text: String,
)

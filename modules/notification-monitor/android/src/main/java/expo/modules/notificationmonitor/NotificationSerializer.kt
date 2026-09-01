package expo.modules.notificationmonitor

internal object NotificationSerializer {
  fun serializeSummary(summary: NotificationAppSummaryRecord): Map<String, Any?> = mapOf(
    "packageName" to summary.packageName,
    "appName" to summary.appName,
    "totalObserved" to summary.totalObserved,
    "eligibleCount" to summary.eligibleCount,
    "skippedCount" to summary.skippedCount,
    "latestNotificationAt" to summary.latestNotificationAt.toDouble(),
    "latestEligibleEventKey" to summary.latestEligibleEventKey,
  )

  fun serializeEvent(event: NotificationEventRecord): Map<String, Any?> = mapOf(
    "eventKey" to event.eventKey,
    "packageName" to event.packageName,
    "appName" to event.appName,
    "postedAt" to event.postedAt.toDouble(),
    "updatedAt" to event.updatedAt.toDouble(),
    "removedAt" to event.removedAt?.toDouble(),
    "contentState" to event.contentState.wireValue,
    "contentFingerprint" to event.contentFingerprint,
    "eligibility" to mapOf(
      "eligible" to event.eligibilityReason.eligible,
      "reason" to event.eligibilityReason.wireValue,
    ),
  )

  fun serializeAnalysisText(record: NotificationAnalysisTextRecord): Map<String, Any?> = mapOf(
    "eventKey" to record.eventKey,
    "packageName" to record.packageName,
    "postedAt" to record.postedAt.toDouble(),
    "updatedAt" to record.updatedAt.toDouble(),
    "contentFingerprint" to record.contentFingerprint,
    "text" to record.text,
  )
}

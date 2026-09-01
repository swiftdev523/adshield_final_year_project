package expo.modules.notificationmonitor

import java.util.UUID

internal interface NotificationRecordStore {
  fun load(): NotificationRecordSnapshot
  fun save(records: List<NotificationEventRecord>)
  fun clear()
}

internal data class NotificationRecordSnapshot(
  val records: List<NotificationEventRecord>,
  val requiresRewrite: Boolean = false,
)

internal class NotificationHistoryRepository(
  private val store: NotificationRecordStore,
  private val clock: () -> Long = System::currentTimeMillis,
  private val idFactory: () -> String = { UUID.randomUUID().toString() },
) {
  companion object {
    const val MAX_RECORDS = 500
    const val MAX_RETURN_LIMIT = MAX_RECORDS
    const val DEFAULT_RETURN_LIMIT = 50
    const val HISTORY_WINDOW_MILLIS = 24L * 60L * 60L * 1_000L
    private val sha256Pattern = Regex("^[0-9a-f]{64}$")
  }

  @Synchronized
  fun recordPosted(
    notificationKeyHash: String,
    packageName: String,
    appName: String,
    content: SanitizedNotificationContent,
    metadata: NotificationSemanticMetadata,
    revisionFingerprint: String? = content.analysisText?.let(NotificationKeyHasher::sha256),
  ) {
    require(sha256Pattern.matches(notificationKeyHash)) {
      "notificationKeyHash must be a lowercase SHA-256 value"
    }
    require(packageName.isNotBlank()) { "packageName must not be blank" }
    require(appName.isNotBlank()) { "appName must not be blank" }
    require(revisionFingerprint == null || sha256Pattern.matches(revisionFingerprint)) {
      "revisionFingerprint must be null or a lowercase SHA-256 value"
    }
    require(
      (content.state == NotificationContentState.AVAILABLE && !content.analysisText.isNullOrBlank()) ||
        (content.state != NotificationContentState.AVAILABLE && content.analysisText == null),
    ) { "Sanitized content and content state are inconsistent" }

    val now = clock()
    val records = loadPruned(now).toMutableList()
    val activeIndex = records.indexOfLast {
      it.notificationKeyHash == notificationKeyHash && it.removedAt == null
    }
    val eligibilityReason = NotificationEligibilityEvaluator.evaluate(content, metadata)
    // Only eligible text is retained for a later explicit one-event analysis.
    // Skipped events keep the semantic state and a private revision hash, not
    // their body or a public-facing content fingerprint.
    val storedAnalysisText = content.analysisText.takeIf { eligibilityReason.eligible }
    val contentFingerprint = storedAnalysisText?.let(NotificationKeyHasher::sha256)

    if (activeIndex >= 0) {
      val current = records[activeIndex]
      if (
        current.contentState == content.state &&
        current.analysisText == storedAnalysisText &&
        current.contentFingerprint == contentFingerprint &&
        current.revisionFingerprint == revisionFingerprint &&
        current.metadata == metadata &&
        current.eligibilityReason == eligibilityReason
      ) {
        // Android may deliver an identical callback more than once. Preserve
        // event identity and timestamps so an existing event-level result does
        // not become stale merely because of a duplicate callback.
        if (current.packageName != packageName || current.appName != appName) {
          records[activeIndex] = current.copy(
            packageName = packageName,
            appName = appName,
          )
          store.save(records)
        }
        return
      }

      // The same active StatusBarNotification key now carries a different
      // payload or semantic state. End the old revision and create a new
      // opaque event key so its classifier result cannot leak to this revision.
      records[activeIndex] = current.copy(
        removedAt = maxOf(now, current.postedAt),
      )
    }

    val eventKey = idFactory().trim()
    require(eventKey.isNotEmpty()) { "eventKey must not be blank" }
    require(records.none { it.eventKey == eventKey }) { "eventKey must be unique" }

    records += NotificationEventRecord(
      eventKey = eventKey,
      notificationKeyHash = notificationKeyHash,
      packageName = packageName,
      appName = appName,
      postedAt = now,
      updatedAt = now,
      removedAt = null,
      analysisText = storedAnalysisText,
      contentState = content.state,
      contentFingerprint = contentFingerprint,
      revisionFingerprint = revisionFingerprint,
      metadata = metadata,
      eligibilityReason = eligibilityReason,
    )

    store.save(cap(records))
  }

  @Synchronized
  fun recordRemoved(notificationKeyHash: String) {
    val now = clock()
    val records = loadPruned(now).toMutableList()
    val activeIndex = records.indexOfLast {
      it.notificationKeyHash == notificationKeyHash && it.removedAt == null
    }

    if (activeIndex >= 0) {
      val current = records[activeIndex]
      records[activeIndex] = current.copy(
        removedAt = maxOf(now, current.postedAt),
      )
      store.save(records)
    }
  }

  @Synchronized
  fun getNotificationSummary(): List<NotificationAppSummaryRecord> {
    val records = loadPruned(clock())

    return records
      .groupBy(NotificationEventRecord::packageName)
      .map { (packageName, packageEvents) ->
        val newest = packageEvents.maxWithOrNull(
          compareBy<NotificationEventRecord> { it.updatedAt }
            .thenBy { it.postedAt }
            .thenBy { it.eventKey },
        )!!
        val latestEligible = packageEvents
          .asSequence()
          .filter {
            it.eligibilityReason.eligible &&
              it.contentState == NotificationContentState.AVAILABLE &&
              !it.analysisText.isNullOrBlank()
          }
          .maxWithOrNull(
            compareBy<NotificationEventRecord> { it.updatedAt }
              .thenBy { it.postedAt }
              .thenBy { it.eventKey },
          )
        val eligibleCount = packageEvents.count { it.eligibilityReason.eligible }

        NotificationAppSummaryRecord(
          packageName = packageName,
          appName = newest.appName,
          totalObserved = packageEvents.size,
          eligibleCount = eligibleCount,
          skippedCount = packageEvents.size - eligibleCount,
          latestNotificationAt = newest.updatedAt,
          latestEligibleEventKey = latestEligible?.eventKey,
        )
      }
      .sortedWith(
        compareByDescending<NotificationAppSummaryRecord> { it.totalObserved }
          .thenByDescending { it.latestNotificationAt }
          .thenBy { it.appName.lowercase() }
          .thenBy { it.packageName },
      )
  }

  @Synchronized
  fun getRecentNotifications(requestedLimit: Int? = null): List<NotificationEventRecord> {
    val limit = (requestedLimit ?: DEFAULT_RETURN_LIMIT).coerceIn(1, MAX_RETURN_LIMIT)
    return loadPruned(clock())
      .sortedWith(
        compareByDescending<NotificationEventRecord> { it.updatedAt }
          .thenByDescending { it.postedAt }
          .thenBy { it.eventKey },
      )
      .take(limit)
  }

  @Synchronized
  fun getNotificationAnalysisText(eventKey: String): NotificationAnalysisTextRecord? {
    if (eventKey.isBlank()) return null
    val event = loadPruned(clock()).firstOrNull { it.eventKey == eventKey } ?: return null
    // A dismissed event may still be analyzed from the 24-hour local history.
    // Its opaque event key and content fingerprint identify the exact immutable
    // revision, so removal alone does not make the event ambiguous.
    if (!event.eligibilityReason.eligible) return null
    if (event.contentState != NotificationContentState.AVAILABLE) return null

    val text = event.analysisText?.takeIf(String::isNotBlank) ?: return null
    val fingerprint = event.contentFingerprint ?: return null
    if (!sha256Pattern.matches(fingerprint) || NotificationKeyHasher.sha256(text) != fingerprint) {
      return null
    }

    return NotificationAnalysisTextRecord(
      eventKey = event.eventKey,
      packageName = event.packageName,
      postedAt = event.postedAt,
      updatedAt = event.updatedAt,
      contentFingerprint = fingerprint,
      text = text,
    )
  }

  @Synchronized
  fun clearLocalNotificationHistory() {
    store.clear()
  }

  private fun loadPruned(now: Long): List<NotificationEventRecord> {
    val snapshot = store.load()
    val loaded = snapshot.records
    val cutoff = now - HISTORY_WINDOW_MILLIS
    val cleaned = cap(loaded.filter { it.postedAt >= cutoff })
    if (snapshot.requiresRewrite || cleaned != loaded) {
      store.save(cleaned)
    }
    return cleaned
  }

  private fun cap(records: List<NotificationEventRecord>): List<NotificationEventRecord> = records
    .sortedWith(compareBy<NotificationEventRecord> { it.postedAt }.thenBy { it.eventKey })
    .takeLast(MAX_RECORDS)
}

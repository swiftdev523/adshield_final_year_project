package expo.modules.notificationmonitor

import android.app.Notification
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NotificationHistoryRepositoryTest {
  private class MemoryStore(
    initial: List<NotificationEventRecord> = emptyList(),
    var requiresRewrite: Boolean = false,
  ) : NotificationRecordStore {
    var records = initial.toList()
    var clearCount = 0
    var saveCount = 0

    override fun load(): NotificationRecordSnapshot = NotificationRecordSnapshot(
      records = records.toList(),
      requiresRewrite = requiresRewrite,
    )

    override fun save(records: List<NotificationEventRecord>) {
      saveCount += 1
      this.records = records.toList()
      requiresRewrite = false
    }

    override fun clear() {
      clearCount += 1
      records = emptyList()
    }
  }

  private class Fixture(
    initialTime: Long = 2_000_000_000L,
    initialRecords: List<NotificationEventRecord> = emptyList(),
    requiresRewrite: Boolean = false,
  ) {
    var now = initialTime
    var nextId = 0
    val store = MemoryStore(initialRecords, requiresRewrite)
    val repository = NotificationHistoryRepository(
      store = store,
      clock = { now },
      idFactory = { "event-${++nextId}" },
    )
  }

  private val ordinaryMetadata = NotificationSemanticMetadata(
    category = Notification.CATEGORY_MESSAGE,
    isOngoing = false,
    isForegroundService = false,
    isGroupSummary = false,
    hasProgress = false,
  )

  private fun available(text: String = "Save on groceries today") = SanitizedNotificationContent(
    analysisText = text,
    state = NotificationContentState.AVAILABLE,
  )

  private val redacted = SanitizedNotificationContent(
    analysisText = null,
    state = NotificationContentState.SENSITIVE_REDACTED,
  )

  private fun key(value: String) = NotificationKeyHasher.sha256(value)

  private fun seededRecord(
    eventKey: String,
    key: String,
    packageName: String = "com.example.app",
    appName: String = "Example",
    postedAt: Long,
    updatedAt: Long = postedAt,
    removedAt: Long? = null,
    text: String? = "Text",
    state: NotificationContentState = NotificationContentState.AVAILABLE,
    metadata: NotificationSemanticMetadata? = ordinaryMetadata,
    reason: NotificationEligibilityReason = if (metadata == null) {
      NotificationEligibilityReason.METADATA_UNAVAILABLE
    } else {
      NotificationEligibilityEvaluator.evaluate(SanitizedNotificationContent(text, state), metadata)
    },
  ): NotificationEventRecord {
    val storedText = text.takeIf { reason.eligible }
    return NotificationEventRecord(
      eventKey = eventKey,
      notificationKeyHash = key(key),
      packageName = packageName,
      appName = appName,
      postedAt = postedAt,
      updatedAt = updatedAt,
      removedAt = removedAt,
      analysisText = storedText,
      contentState = state,
      contentFingerprint = storedText?.let(NotificationKeyHasher::sha256),
      revisionFingerprint = text?.let(NotificationKeyHasher::sha256),
      metadata = metadata,
      eligibilityReason = reason,
    )
  }

  @Test
  fun `identical active callbacks preserve event key timestamp and classifier identity`() {
    val fixture = Fixture()
    val hash = key("same-key")

    fixture.repository.recordPosted(hash, "com.example.app", "Example", available(), ordinaryMetadata)
    val original = fixture.store.records.single()
    fixture.now += 5_000L
    fixture.repository.recordPosted(hash, "com.example.app", "Example", available(), ordinaryMetadata)

    assertEquals(1, fixture.store.records.size)
    assertEquals(original, fixture.store.records.single())
    assertEquals(1, fixture.store.saveCount)
  }

  @Test
  fun `changed text on same active key ends old revision and creates a new event key`() {
    val fixture = Fixture()
    val hash = key("updated-key")
    fixture.repository.recordPosted(hash, "com.example.app", "Example", available("First body"), ordinaryMetadata)
    val first = fixture.store.records.single()

    fixture.now += 5_000L
    fixture.repository.recordPosted(hash, "com.example.app", "Example", available("Second body"), ordinaryMetadata)

    assertEquals(2, fixture.store.records.size)
    val oldRevision = fixture.store.records.first()
    val newRevision = fixture.store.records.last()
    assertEquals(first.eventKey, oldRevision.eventKey)
    assertEquals(first.updatedAt, oldRevision.updatedAt)
    assertEquals(fixture.now, oldRevision.removedAt)
    assertNotEquals(oldRevision.eventKey, newRevision.eventKey)
    assertNotEquals(oldRevision.contentFingerprint, newRevision.contentFingerprint)
    assertEquals("Second body", fixture.repository.getNotificationAnalysisText(newRevision.eventKey)?.text)
  }

  @Test
  fun `semantic change on same key creates a new event even when text is unchanged`() {
    val fixture = Fixture()
    val hash = key("semantic-key")
    fixture.repository.recordPosted(hash, "com.example", "Example", available(), ordinaryMetadata)

    fixture.now += 1_000L
    fixture.repository.recordPosted(
      hash,
      "com.example",
      "Example",
      available(),
      ordinaryMetadata.copy(isOngoing = true),
    )

    assertEquals(2, fixture.store.records.size)
    assertTrue(fixture.store.records.first().eligibilityReason.eligible)
    assertEquals(
      NotificationEligibilityReason.ONGOING_NOTIFICATION,
      fixture.store.records.last().eligibilityReason,
    )
    assertNotEquals(fixture.store.records.first().eventKey, fixture.store.records.last().eventKey)
  }

  @Test
  fun `changed redacted payload fingerprint creates a new event without storing body`() {
    val fixture = Fixture()
    val hash = key("redacted-key")
    fixture.repository.recordPosted(
      hash,
      "com.example",
      "Example",
      redacted,
      ordinaryMetadata,
      revisionFingerprint = key("first private payload"),
    )

    fixture.now += 1_000L
    fixture.repository.recordPosted(
      hash,
      "com.example",
      "Example",
      redacted,
      ordinaryMetadata,
      revisionFingerprint = key("second private payload"),
    )

    assertEquals(2, fixture.store.records.size)
    assertNotEquals(fixture.store.records.first().eventKey, fixture.store.records.last().eventKey)
    assertTrue(fixture.store.records.all { it.analysisText == null })
    assertTrue(fixture.store.records.all { it.contentFingerprint == null })
  }

  @Test
  fun `removal preserves immutable event identity and key reuse creates a new event`() {
    val fixture = Fixture()
    val hash = key("reused-key")

    fixture.repository.recordPosted(hash, "com.example.app", "Example", available(), ordinaryMetadata)
    val first = fixture.store.records.single()
    fixture.now += 1_000L
    fixture.repository.recordRemoved(hash)
    val removed = fixture.store.records.single()
    assertEquals(fixture.now, removed.removedAt)
    assertEquals(first.updatedAt, removed.updatedAt)
    assertNotNull(fixture.repository.getNotificationAnalysisText(first.eventKey))

    fixture.now += 1_000L
    fixture.repository.recordPosted(hash, "com.example.app", "Example", available(), ordinaryMetadata)

    assertEquals(2, fixture.store.records.size)
    assertEquals(listOf("event-1", "event-2"), fixture.store.records.map { it.eventKey })
    assertNull(fixture.store.records.last().removedAt)
  }

  @Test
  fun `unknown removal does not create an event`() {
    val fixture = Fixture()

    fixture.repository.recordRemoved(key("not-present"))

    assertTrue(fixture.store.records.isEmpty())
    assertEquals(0, fixture.store.saveCount)
  }

  @Test
  fun `summary reports observed eligible and skipped counts without classifier results`() {
    val fixture = Fixture()
    fixture.repository.recordPosted(key("a-1"), "com.alpha", "Alpha", available("Meeting at noon"), ordinaryMetadata)
    fixture.now += 1L
    fixture.repository.recordPosted(key("a-2"), "com.alpha", "Alpha", redacted, ordinaryMetadata)
    fixture.now += 1L
    fixture.repository.recordPosted(key("b-1"), "com.beta", "Beta", available("Sale today"), ordinaryMetadata)

    val summaries = fixture.repository.getNotificationSummary()

    assertEquals(listOf("com.alpha", "com.beta"), summaries.map { it.packageName })
    assertEquals(2, summaries[0].totalObserved)
    assertEquals(1, summaries[0].eligibleCount)
    assertEquals(1, summaries[0].skippedCount)
    assertEquals("event-1", summaries[0].latestEligibleEventKey)
    assertEquals(1, summaries[1].eligibleCount)
  }

  @Test
  fun `single event text getter rejects skipped legacy missing and fingerprint inconsistent rows`() {
    val now = 8_000_000_000L
    val legacy = seededRecord(
      eventKey = "legacy",
      key = "legacy",
      postedAt = now,
      text = null,
      state = NotificationContentState.LEGACY_REDACTED,
      metadata = null,
    )
    val inconsistent = seededRecord(
      eventKey = "inconsistent",
      key = "inconsistent",
      postedAt = now,
    ).copy(contentFingerprint = key("different"))
    val fixture = Fixture(now, listOf(legacy, inconsistent))
    fixture.repository.recordPosted(
      key("generic"),
      "com.example",
      "Example",
      available("Checking for new messages"),
      ordinaryMetadata,
    )
    val skipped = fixture.store.records.single { it.packageName == "com.example" }

    assertNull(skipped.analysisText)
    assertNull(skipped.contentFingerprint)
    assertNotNull(skipped.revisionFingerprint)
    assertNull(fixture.repository.getNotificationAnalysisText("legacy"))
    assertNull(fixture.repository.getNotificationAnalysisText("inconsistent"))
    assertNull(fixture.repository.getNotificationAnalysisText(skipped.eventKey))
    assertNull(fixture.repository.getNotificationAnalysisText("missing"))
  }

  @Test
  fun `records older than 24 hours are pruned and persisted`() {
    val now = 9_000_000_000L
    val old = seededRecord(
      eventKey = "old",
      key = "old-key",
      postedAt = now - NotificationHistoryRepository.HISTORY_WINDOW_MILLIS - 1L,
    )
    val current = seededRecord(eventKey = "current", key = "current-key", postedAt = now)
    val fixture = Fixture(now, listOf(old, current))

    assertEquals(listOf("current"), fixture.repository.getRecentNotifications(10).map { it.eventKey })
    assertEquals(listOf("current"), fixture.store.records.map { it.eventKey })
    assertEquals(1, fixture.store.saveCount)
  }

  @Test
  fun `legacy snapshot is immediately rewritten through the store`() {
    val now = 10_000_000_000L
    val legacy = seededRecord(
      eventKey = "legacy",
      key = "legacy-key",
      postedAt = now,
      text = null,
      state = NotificationContentState.LEGACY_REDACTED,
      metadata = null,
    )
    val fixture = Fixture(
      initialTime = now,
      initialRecords = listOf(legacy),
      requiresRewrite = true,
    )

    assertEquals(listOf("legacy"), fixture.repository.getRecentNotifications(10).map { it.eventKey })
    assertEquals(1, fixture.store.saveCount)
    assertFalse(fixture.store.requiresRewrite)
    val rewritten = NotificationLineSerializer.serialize(fixture.store.records.single())
    assertTrue(rewritten.startsWith("2\t"))
    assertFalse(rewritten.contains("Legacy body"))
  }

  @Test
  fun `history and bridge return limit are capped at 500 events`() {
    val now = 20_000_000_000L
    val initial = (0 until NotificationHistoryRepository.MAX_RECORDS).map { index ->
      seededRecord(
        eventKey = "seed-$index",
        key = "seed-key-$index",
        postedAt = now - NotificationHistoryRepository.MAX_RECORDS + index,
      )
    }
    val fixture = Fixture(now, initial)

    fixture.repository.recordPosted(key("newest"), "com.new", "Newest", available(), ordinaryMetadata)

    assertEquals(NotificationHistoryRepository.MAX_RECORDS, fixture.store.records.size)
    assertTrue(fixture.store.records.none { it.eventKey == "seed-0" })
    assertEquals(
      NotificationHistoryRepository.MAX_RETURN_LIMIT,
      fixture.repository.getRecentNotifications(999).size,
    )
  }

  @Test
  fun `clear deletes only the notification history store`() {
    val fixture = Fixture()
    fixture.repository.recordPosted(key("event"), "com.example", "Example", available(), ordinaryMetadata)

    fixture.repository.clearLocalNotificationHistory()

    assertTrue(fixture.store.records.isEmpty())
    assertEquals(1, fixture.store.clearCount)
  }

  @Test
  fun `public bulk serializer excludes notification body key hash and classifier result`() {
    val event = seededRecord(
      eventKey = "event-public",
      key = "private-key",
      postedAt = 100L,
    )
    val eventMap = NotificationSerializer.serializeEvent(event)

    assertEquals(
      setOf(
        "eventKey",
        "packageName",
        "appName",
        "postedAt",
        "updatedAt",
        "removedAt",
        "contentState",
        "contentFingerprint",
        "eligibility",
      ),
      eventMap.keys,
    )
    assertFalse("analysisText" in eventMap)
    assertFalse("notificationKeyHash" in eventMap)
    assertFalse("revisionFingerprint" in eventMap)
    assertFalse("prediction" in eventMap)
  }
}

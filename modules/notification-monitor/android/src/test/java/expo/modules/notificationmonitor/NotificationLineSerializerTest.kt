package expo.modules.notificationmonitor

import android.app.Notification
import java.net.URLEncoder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NotificationLineSerializerTest {
  private val metadata = NotificationSemanticMetadata(
    category = Notification.CATEGORY_MESSAGE,
    isOngoing = false,
    isForegroundService = false,
    isGroupSummary = false,
    hasProgress = false,
  )

  private fun record(
    contentState: NotificationContentState = NotificationContentState.AVAILABLE,
    analysisText: String? = "Sale now",
    removedAt: Long? = null,
    eventMetadata: NotificationSemanticMetadata? = metadata,
    reason: NotificationEligibilityReason = NotificationEligibilityReason.MEANINGFUL_CONTENT,
  ) = NotificationEventRecord(
    eventKey = "event-1",
    notificationKeyHash = NotificationKeyHasher.sha256("raw-status-bar-key"),
    packageName = "com.example.app",
    appName = "Example App",
    postedAt = 1_000L,
    updatedAt = 2_000L,
    removedAt = removedAt,
    analysisText = analysisText,
    contentState = contentState,
    contentFingerprint = analysisText?.let(NotificationKeyHasher::sha256),
    revisionFingerprint = analysisText?.let(NotificationKeyHasher::sha256),
    metadata = eventMetadata,
    eligibilityReason = reason,
  )

  @Test
  fun `v2 round trips encoded Unicode metadata eligibility and nullable fields`() {
    val original = record().copy(
      eventKey = "event\twith newline\n% value",
      appName = "Caf\u00E9 Deals \uD83D\uDE42",
      packageName = "com.example.percent%app",
      analysisText = "Offer\twith newline\nand 50% off \uD83D\uDE42",
      contentFingerprint = NotificationKeyHasher.sha256(
        "Offer\twith newline\nand 50% off \uD83D\uDE42",
      ),
      removedAt = 2_500L,
      metadata = metadata.copy(category = "message/custom%category"),
    )

    val encoded = NotificationLineSerializer.serialize(original)
    val decoded = NotificationLineSerializer.deserialize(encoded)

    assertEquals(original, decoded)
    assertTrue(encoded.startsWith("2\t"))
    assertFalse(encoded.contains('\n'))
    assertFalse(encoded.contains("raw-status-bar-key"))
    assertTrue(encoded.contains(original.notificationKeyHash))
  }

  @Test
  fun `v2 round trips sensitive record without body or fingerprint`() {
    val original = record(
      contentState = NotificationContentState.SENSITIVE_REDACTED,
      analysisText = null,
      reason = NotificationEligibilityReason.SENSITIVE_CONTENT,
    )

    assertEquals(
      original,
      NotificationLineSerializer.deserialize(NotificationLineSerializer.serialize(original)),
    )
  }

  @Test
  fun `v2 generic status keeps only private revision hash and no body`() {
    val rawBody = "Checking for new messages"
    val original = record(
      contentState = NotificationContentState.AVAILABLE,
      analysisText = null,
      reason = NotificationEligibilityReason.GENERIC_BACKGROUND_STATUS,
    ).copy(revisionFingerprint = NotificationKeyHasher.sha256(rawBody))

    val encoded = NotificationLineSerializer.serialize(original)
    val decoded = NotificationLineSerializer.deserialize(encoded)

    assertEquals(original, decoded)
    assertNull(decoded?.analysisText)
    assertNull(decoded?.contentFingerprint)
    assertFalse(encoded.contains(rawBody))
  }

  @Test
  fun `v1 migration validates then discards body and marks metadata unavailable`() {
    val body = "Old private notification body"
    val legacyLine = listOf(
      "1",
      encode("legacy-event"),
      encode(NotificationKeyHasher.sha256("legacy-key")),
      encode("com.example.legacy"),
      encode("Legacy App"),
      "1000",
      "2000",
      "",
      "available",
      "1${encode(body)}",
    ).joinToString("\t")

    val migrated = NotificationLineSerializer.deserialize(legacyLine)!!

    assertEquals("legacy-event", migrated.eventKey)
    assertEquals(NotificationContentState.LEGACY_REDACTED, migrated.contentState)
    assertEquals(NotificationEligibilityReason.METADATA_UNAVAILABLE, migrated.eligibilityReason)
    assertNull(migrated.analysisText)
    assertNull(migrated.contentFingerprint)
    assertNull(migrated.metadata)
    assertFalse(NotificationLineSerializer.serialize(migrated).contains(encode(body)))
    assertEquals(
      migrated,
      NotificationLineSerializer.deserialize(NotificationLineSerializer.serialize(migrated)),
    )
  }

  @Test
  fun `rejects malformed unsupported or internally inconsistent lines`() {
    val valid = NotificationLineSerializer.serialize(record())
    val malformed = listOf(
      "",
      "3" + valid.drop(1),
      valid.substringBeforeLast('\t'),
      valid.replace(record().notificationKeyHash, "not-a-hash"),
      valid.replace("\tavailable\t", "\tempty\t"),
      valid.replace("\t1000\t2000\t", "\t2000\t1000\t"),
      valid.replace(NotificationEligibilityReason.MEANINGFUL_CONTENT.wireValue, "ongoing_notification"),
      "x".repeat(9_000),
    )

    malformed.forEach { line ->
      assertNull(line, NotificationLineSerializer.deserialize(line))
    }
  }

  @Test
  fun `SHA-256 helper is deterministic and never returns the raw key`() {
    val raw = "0|com.private.app|42|private-channel"
    val first = NotificationKeyHasher.sha256(raw)

    assertEquals(first, NotificationKeyHasher.sha256(raw))
    assertEquals(64, first.length)
    assertTrue(first.matches(Regex("^[0-9a-f]{64}$")))
    assertFalse(first.contains(raw))
  }

  private fun encode(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())
}

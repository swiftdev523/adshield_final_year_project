package expo.modules.notificationmonitor

import android.app.Notification
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NotificationEligibilityEvaluatorTest {
  private val ordinaryMetadata = NotificationSemanticMetadata(
    category = Notification.CATEGORY_MESSAGE,
    isOngoing = false,
    isForegroundService = false,
    isGroupSummary = false,
    hasProgress = false,
  )

  private fun content(text: String) = SanitizedNotificationContent(
    analysisText = text,
    state = NotificationContentState.AVAILABLE,
  )

  @Test
  fun `skips narrow generic operational statuses before classifier invocation`() {
    val statuses = listOf(
      "You may have new messages",
      "Checking for new messages",
      "Syncing messages",
      "Running in background",
      "Backup in progress",
      "Connected",
      "Waiting for network",
      "Service running",
    )

    statuses.forEach { text ->
      assertEquals(
        text,
        NotificationEligibilityReason.GENERIC_BACKGROUND_STATUS,
        NotificationEligibilityEvaluator.evaluate(content(text), ordinaryMetadata),
      )
    }
  }

  @Test
  fun `meaningful Gmail style spam and normal meeting text remain eligible`() {
    val texts = listOf(
      "You have won a free prize. Click here to claim it.",
      "Meeting moved to 4 PM tomorrow",
      "URGENT! You have won GH\u20B55,000. Click this link now to claim.",
    )

    texts.forEach { text ->
      val result = NotificationEligibilityEvaluator.evaluate(content(text), ordinaryMetadata)
      assertEquals(text, NotificationEligibilityReason.MEANINGFUL_CONTENT, result)
      assertTrue(result.eligible)
    }
  }

  @Test
  fun `generic fallback is narrow and does not swallow meaningful extensions`() {
    val result = NotificationEligibilityEvaluator.evaluate(
      content("You may have new messages about a free prize"),
      ordinaryMetadata,
    )

    assertEquals(NotificationEligibilityReason.MEANINGFUL_CONTENT, result)
  }

  @Test
  fun `Android semantics take precedence over otherwise meaningful text`() {
    val meaningful = content("A meaningful sale starts at noon")
    val cases = listOf(
      ordinaryMetadata.copy(isGroupSummary = true) to NotificationEligibilityReason.GROUP_SUMMARY,
      ordinaryMetadata.copy(isForegroundService = true) to NotificationEligibilityReason.FOREGROUND_SERVICE,
      ordinaryMetadata.copy(hasProgress = true) to NotificationEligibilityReason.PROGRESS_NOTIFICATION,
      ordinaryMetadata.copy(isOngoing = true) to NotificationEligibilityReason.ONGOING_NOTIFICATION,
      ordinaryMetadata.copy(category = Notification.CATEGORY_SERVICE) to NotificationEligibilityReason.SERVICE_NOTIFICATION,
    )

    cases.forEach { (metadata, expected) ->
      assertEquals(expected, NotificationEligibilityEvaluator.evaluate(meaningful, metadata))
      assertFalse(expected.eligible)
    }
  }

  @Test
  fun `empty sensitive and legacy metadata states are not eligible`() {
    assertEquals(
      NotificationEligibilityReason.EMPTY_CONTENT,
      NotificationEligibilityEvaluator.evaluate(
        SanitizedNotificationContent(null, NotificationContentState.EMPTY),
        ordinaryMetadata,
      ),
    )
    assertEquals(
      NotificationEligibilityReason.SENSITIVE_CONTENT,
      NotificationEligibilityEvaluator.evaluate(
        SanitizedNotificationContent(null, NotificationContentState.SENSITIVE_REDACTED),
        ordinaryMetadata,
      ),
    )
    assertEquals(
      NotificationEligibilityReason.METADATA_UNAVAILABLE,
      NotificationEligibilityEvaluator.evaluate(content("Legacy body"), null),
    )
  }

  @Test
  fun `eligibility API is package neutral by construction`() {
    val parameterNames = NotificationEligibilityEvaluator::class.java.declaredMethods
      .first { it.name == "evaluate" }
      .parameterTypes
      .map(Class<*>::getSimpleName)

    assertFalse(parameterNames.any { it.contains("Package", ignoreCase = true) })
  }
}

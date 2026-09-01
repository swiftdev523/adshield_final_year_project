package expo.modules.notificationmonitor

import android.app.Notification
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NotificationContentSanitizerTest {
  @Test
  fun `keeps ordinary text while normalizing whitespace`() {
    val result = NotificationContentSanitizer.sanitize(
      rawText = "  Weekend\n sale   starts now  ",
      category = Notification.CATEGORY_PROMO,
      visibility = Notification.VISIBILITY_PRIVATE,
    )

    assertEquals(NotificationContentState.AVAILABLE, result.state)
    assertEquals("Weekend sale starts now", result.analysisText)
  }

  @Test
  fun `replaces full URLs including paths query strings and fragments`() {
    val result = NotificationContentSanitizer.sanitize(
      rawText = "Open https://example.test/deal?user=terry&token=secret#offer now",
      category = Notification.CATEGORY_PROMO,
      visibility = Notification.VISIBILITY_PUBLIC,
    )

    assertEquals(NotificationContentState.AVAILABLE, result.state)
    assertEquals("Open <link> now", result.analysisText)
  }

  @Test
  fun `does not retain URL host path query or fragment content`() {
    val result = NotificationContentSanitizer.sanitize(
      rawText = "Visit www.private.test/user/terry?token=secret#account",
      category = Notification.CATEGORY_PROMO,
      visibility = Notification.VISIBILITY_PUBLIC,
    )

    assertEquals("Visit <link>", result.analysisText)
    assertTrue(result.analysisText?.contains("private.test") == false)
    assertTrue(result.analysisText?.contains("terry") == false)
    assertTrue(result.analysisText?.contains("secret") == false)
  }

  @Test
  fun `keeps meaningful message body but still redacts calls and secret notifications`() {
    val message = NotificationContentSanitizer.sanitize(
      "You have won a free prize. Click here to claim it.",
      Notification.CATEGORY_MESSAGE,
      Notification.VISIBILITY_PRIVATE,
    )
    assertEquals(NotificationContentState.AVAILABLE, message.state)
    assertEquals("You have won a free prize. Click here to claim it.", message.analysisText)

    val inputs = listOf(
      Triple(Notification.CATEGORY_CALL, Notification.VISIBILITY_PUBLIC, "Incoming call"),
      Triple(Notification.CATEGORY_PROMO, Notification.VISIBILITY_SECRET, "Private offer"),
    )

    inputs.forEach { (category, visibility, text) ->
      val result = NotificationContentSanitizer.sanitize(text, category, visibility)
      assertEquals(NotificationContentState.SENSITIVE_REDACTED, result.state)
      assertNull(result.analysisText)
    }
  }

  @Test
  fun `redacts credentials OTP PIN and code-like numeric text`() {
    val sensitiveTexts = listOf(
      "Your OTP is 839201",
      "Password changed successfully",
      "Use PIN 5190 to continue",
      "Your login code is AB12-CD34",
      "Enter 746281 to verify your account",
    )

    sensitiveTexts.forEach { text ->
      val result = NotificationContentSanitizer.sanitize(
        text,
        Notification.CATEGORY_STATUS,
        Notification.VISIBILITY_PRIVATE,
      )
      assertEquals(text, NotificationContentState.SENSITIVE_REDACTED, result.state)
      assertNull(text, result.analysisText)
    }
  }

  @Test
  fun `returns empty state when no body text exists`() {
    listOf(null, "", " \n\t ").forEach { text ->
      val result = NotificationContentSanitizer.sanitize(
        text,
        Notification.CATEGORY_STATUS,
        Notification.VISIBILITY_PRIVATE,
      )
      assertEquals(NotificationContentState.EMPTY, result.state)
      assertNull(result.analysisText)
    }
  }

  @Test
  fun `truncates by Unicode code point without splitting a surrogate pair`() {
    val smile = "\uD83D\uDE42"
    val source = smile.repeat(NotificationContentSanitizer.MAX_ANALYSIS_TEXT_CODE_POINTS + 5)
    val result = NotificationContentSanitizer.sanitize(
      source,
      Notification.CATEGORY_PROMO,
      Notification.VISIBILITY_PUBLIC,
    )

    val text = result.analysisText!!
    assertEquals(
      NotificationContentSanitizer.MAX_ANALYSIS_TEXT_CODE_POINTS,
      text.codePointCount(0, text.length),
    )
    assertTrue(text.endsWith(smile))
  }
}

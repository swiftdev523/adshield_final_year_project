package expo.modules.notificationmonitor

import android.app.Notification

internal object NotificationContentSanitizer {
  const val MAX_ANALYSIS_TEXT_CODE_POINTS = 240

  private val whitespace = Regex("\\s+")
  private val sensitiveKeyword = Regex(
    pattern = """(?i)\b(?:otp|one[\s-]*time|password|passcode|pin|verification(?:\s+code)?|security\s+code|authentication\s+code|login\s+code)\b""",
  )
  private val codeWithValue = Regex(
    pattern = """(?i)\bcode(?:\s+is|\s*[:=-])?\s*[a-z0-9-]{4,12}\b""",
  )
  private val standaloneCodeLikeNumber = Regex("""(?<!\d)\d{4,8}(?!\d)""")
  private val url = Regex("""(?i)\b(?:https?://|www\.)[^\s]+""")

  fun sanitize(
    rawText: String?,
    category: String?,
    visibility: Int,
  ): SanitizedNotificationContent {
    if (category == Notification.CATEGORY_CALL || visibility == Notification.VISIBILITY_SECRET) {
      return SanitizedNotificationContent(
        analysisText = null,
        state = NotificationContentState.SENSITIVE_REDACTED,
      )
    }

    val normalized = rawText.orEmpty().replace(whitespace, " ").trim()
    if (normalized.isEmpty()) {
      return SanitizedNotificationContent(
        analysisText = null,
        state = NotificationContentState.EMPTY,
      )
    }

    if (
      sensitiveKeyword.containsMatchIn(normalized) ||
      codeWithValue.containsMatchIn(normalized) ||
      standaloneCodeLikeNumber.containsMatchIn(normalized)
    ) {
      return SanitizedNotificationContent(
        analysisText = null,
        state = NotificationContentState.SENSITIVE_REDACTED,
      )
    }

    // Even URL paths and fragments can contain user or tracking identifiers.
    // Retain only a neutral marker for classification, never the original URL.
    val queryStripped = url.replace(normalized, "<link>")
      .replace(whitespace, " ")
      .trim()

    if (queryStripped.isEmpty()) {
      return SanitizedNotificationContent(
        analysisText = null,
        state = NotificationContentState.EMPTY,
      )
    }

    return SanitizedNotificationContent(
      analysisText = queryStripped.takeCodePoints(MAX_ANALYSIS_TEXT_CODE_POINTS),
      state = NotificationContentState.AVAILABLE,
    )
  }

  private fun String.takeCodePoints(maxCodePoints: Int): String {
    val count = codePointCount(0, length)
    if (count <= maxCodePoints) return this
    return substring(0, offsetByCodePoints(0, maxCodePoints))
  }
}

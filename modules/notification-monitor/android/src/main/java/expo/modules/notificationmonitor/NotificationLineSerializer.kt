package expo.modules.notificationmonitor

import java.net.URLDecoder
import java.net.URLEncoder

internal object NotificationLineSerializer {
  private const val CURRENT_FORMAT_VERSION = "2"
  private const val LEGACY_FORMAT_VERSION = "1"
  private const val FIELD_SEPARATOR = "\t"
  private const val NULL_VALUE = "0"
  private const val PRESENT_VALUE = "1"
  private const val LEGACY_FIELD_COUNT = 10
  private const val CURRENT_FIELD_COUNT = 18
  private const val MAX_SERIALIZED_LINE_LENGTH = 8_192
  private val sha256Pattern = Regex("^[0-9a-f]{64}$")

  fun serialize(record: NotificationEventRecord): String {
    val metadata = record.metadata
    require(record.revisionFingerprint == null || sha256Pattern.matches(record.revisionFingerprint)) {
      "revisionFingerprint must be null or a lowercase SHA-256 value"
    }
    require(
      isValidPersistedContent(
        record.contentState,
        record.analysisText,
        record.contentFingerprint,
        record.eligibilityReason,
      ),
    ) {
      "Notification content and fingerprint are inconsistent"
    }
    if (metadata == null) {
      require(
        record.eligibilityReason == NotificationEligibilityReason.METADATA_UNAVAILABLE &&
          record.contentState == NotificationContentState.LEGACY_REDACTED &&
          record.analysisText == null &&
          record.contentFingerprint == null &&
          record.revisionFingerprint == null,
      ) { "Metadata-unavailable rows must be privacy-redacted legacy events" }
    } else {
      require(
        isEligibilityConsistent(
          state = record.contentState,
          analysisText = record.analysisText,
          revisionFingerprint = record.revisionFingerprint,
          metadata = metadata,
          reason = record.eligibilityReason,
        ),
      ) { "Notification eligibility is inconsistent with persisted metadata" }
    }
    return listOf(
      CURRENT_FORMAT_VERSION,
      encode(record.eventKey),
      encode(record.notificationKeyHash),
      encode(record.packageName),
      encode(record.appName),
      record.postedAt.toString(),
      record.updatedAt.toString(),
      record.removedAt?.toString().orEmpty(),
      record.contentState.wireValue,
      encodeNullable(record.analysisText),
      encodeNullable(record.contentFingerprint),
      encodeNullable(record.revisionFingerprint),
      encodeNullable(metadata?.category),
      encodeBoolean(metadata?.isOngoing == true),
      encodeBoolean(metadata?.isForegroundService == true),
      encodeBoolean(metadata?.isGroupSummary == true),
      encodeBoolean(metadata?.hasProgress == true),
      record.eligibilityReason.wireValue,
    ).joinToString(FIELD_SEPARATOR)
  }

  fun deserialize(line: String): NotificationEventRecord? {
    if (line.isBlank() || line.length > MAX_SERIALIZED_LINE_LENGTH) return null
    return when (line.substringBefore(FIELD_SEPARATOR)) {
      CURRENT_FORMAT_VERSION -> deserializeCurrent(line)
      LEGACY_FORMAT_VERSION -> deserializeLegacy(line)
      else -> null
    }
  }

  fun isLegacyLine(line: String): Boolean =
    line.substringBefore(FIELD_SEPARATOR) == LEGACY_FORMAT_VERSION

  private fun deserializeCurrent(line: String): NotificationEventRecord? = runCatching {
    val fields = line.split(FIELD_SEPARATOR, limit = CURRENT_FIELD_COUNT + 1)
    if (fields.size != CURRENT_FIELD_COUNT || fields[0] != CURRENT_FORMAT_VERSION) return null

    val eventKey = decode(fields[1])
    val keyHash = decode(fields[2])
    val packageName = decode(fields[3])
    val appName = decode(fields[4])
    val postedAt = fields[5].toLong()
    val updatedAt = fields[6].toLong()
    val removedAt = fields[7].takeIf(String::isNotEmpty)?.toLong()
    val contentState = NotificationContentState.fromWireValue(fields[8]) ?: return null
    val analysisText = decodeNullable(fields[9])
    val contentFingerprint = decodeNullable(fields[10])
    val revisionFingerprint = decodeNullable(fields[11])
    val category = decodeNullable(fields[12])
    val isOngoing = decodeBoolean(fields[13])
    val isForegroundService = decodeBoolean(fields[14])
    val isGroupSummary = decodeBoolean(fields[15])
    val hasProgress = decodeBoolean(fields[16])
    val eligibilityReason = NotificationEligibilityReason.fromWireValue(fields[17]) ?: return null
    val metadata = if (eligibilityReason == NotificationEligibilityReason.METADATA_UNAVAILABLE) {
      if (category != null || isOngoing || isForegroundService || isGroupSummary || hasProgress) {
        return null
      }
      null
    } else {
      NotificationSemanticMetadata(
        category = category,
        isOngoing = isOngoing,
        isForegroundService = isForegroundService,
        isGroupSummary = isGroupSummary,
        hasProgress = hasProgress,
      )
    }
    if (
      !isValidCommon(
        eventKey = eventKey,
        keyHash = keyHash,
        packageName = packageName,
        appName = appName,
        postedAt = postedAt,
        updatedAt = updatedAt,
        removedAt = removedAt,
      ) ||
      !isValidPersistedContent(
        contentState,
        analysisText,
        contentFingerprint,
        eligibilityReason,
      ) ||
      (revisionFingerprint != null && !sha256Pattern.matches(revisionFingerprint)) ||
      (metadata == null &&
        (contentState != NotificationContentState.LEGACY_REDACTED ||
          analysisText != null ||
          contentFingerprint != null ||
          revisionFingerprint != null)) ||
      (metadata != null &&
        !isEligibilityConsistent(
          state = contentState,
          analysisText = analysisText,
          revisionFingerprint = revisionFingerprint,
          metadata = metadata,
          reason = eligibilityReason,
        ))
    ) {
      return null
    }

    NotificationEventRecord(
      eventKey = eventKey,
      notificationKeyHash = keyHash,
      packageName = packageName,
      appName = appName,
      postedAt = postedAt,
      updatedAt = updatedAt,
      removedAt = removedAt,
      analysisText = analysisText,
      contentState = contentState,
      contentFingerprint = contentFingerprint,
      revisionFingerprint = revisionFingerprint,
      metadata = metadata,
      eligibilityReason = eligibilityReason,
    )
  }.getOrNull()

  private fun deserializeLegacy(line: String): NotificationEventRecord? = runCatching {
    val fields = line.split(FIELD_SEPARATOR, limit = LEGACY_FIELD_COUNT + 1)
    if (fields.size != LEGACY_FIELD_COUNT || fields[0] != LEGACY_FORMAT_VERSION) return null

    val eventKey = decode(fields[1])
    val keyHash = decode(fields[2])
    val packageName = decode(fields[3])
    val appName = decode(fields[4])
    val postedAt = fields[5].toLong()
    val updatedAt = fields[6].toLong()
    val removedAt = fields[7].takeIf(String::isNotEmpty)?.toLong()
    val legacyContentState = NotificationContentState.fromWireValue(fields[8]) ?: return null
    val legacyAnalysisText = decodeNullable(fields[9])

    if (
      !isValidCommon(
        eventKey = eventKey,
        keyHash = keyHash,
        packageName = packageName,
        appName = appName,
        postedAt = postedAt,
        updatedAt = updatedAt,
        removedAt = removedAt,
      ) ||
      (legacyContentState == NotificationContentState.AVAILABLE && legacyAnalysisText.isNullOrBlank()) ||
      (legacyContentState != NotificationContentState.AVAILABLE && legacyAnalysisText != null)
    ) {
      return null
    }

    // V1 did not persist Android semantic metadata. Keep the row for local
    // history, but never send its old body to the classifier.
    NotificationEventRecord(
      eventKey = eventKey,
      notificationKeyHash = keyHash,
      packageName = packageName,
      appName = appName,
      postedAt = postedAt,
      updatedAt = updatedAt,
      removedAt = removedAt,
      analysisText = null,
      contentState = NotificationContentState.LEGACY_REDACTED,
      contentFingerprint = null,
      revisionFingerprint = null,
      metadata = null,
      eligibilityReason = NotificationEligibilityReason.METADATA_UNAVAILABLE,
    )
  }.getOrNull()

  private fun isValidCommon(
    eventKey: String,
    keyHash: String,
    packageName: String,
    appName: String,
    postedAt: Long,
    updatedAt: Long,
    removedAt: Long?,
  ): Boolean = eventKey.isNotBlank() &&
    sha256Pattern.matches(keyHash) &&
    packageName.isNotBlank() &&
    appName.isNotBlank() &&
    postedAt >= 0L &&
    updatedAt >= postedAt &&
    (removedAt == null || removedAt >= postedAt)

  private fun isValidPersistedContent(
    state: NotificationContentState,
    analysisText: String?,
    contentFingerprint: String?,
    reason: NotificationEligibilityReason,
  ): Boolean = if (reason.eligible) {
    state == NotificationContentState.AVAILABLE &&
      !analysisText.isNullOrBlank() &&
      contentFingerprint != null &&
      sha256Pattern.matches(contentFingerprint) &&
      NotificationKeyHasher.sha256(analysisText) == contentFingerprint
  } else {
    analysisText == null && contentFingerprint == null
  }

  private fun isEligibilityConsistent(
    state: NotificationContentState,
    analysisText: String?,
    revisionFingerprint: String?,
    metadata: NotificationSemanticMetadata,
    reason: NotificationEligibilityReason,
  ): Boolean {
    if (reason == NotificationEligibilityReason.METADATA_UNAVAILABLE) return false

    if (reason == NotificationEligibilityReason.GENERIC_BACKGROUND_STATUS) {
      // The generic body is intentionally not persisted. Verify that the
      // private source hash exists and that Android semantics would otherwise
      // permit meaningful content; the repository made the narrow text match
      // before discarding the body.
      return state == NotificationContentState.AVAILABLE &&
        revisionFingerprint != null &&
        NotificationEligibilityEvaluator.evaluate(
          SanitizedNotificationContent(
            analysisText = "Meaningful notification placeholder",
            state = NotificationContentState.AVAILABLE,
          ),
          metadata,
        ) == NotificationEligibilityReason.MEANINGFUL_CONTENT
    }

    return NotificationEligibilityEvaluator.evaluate(
      SanitizedNotificationContent(analysisText, state),
      metadata,
    ) == reason
  }

  private fun encode(value: String): String = URLEncoder.encode(value, Charsets.UTF_8.name())

  private fun decode(value: String): String = URLDecoder.decode(value, Charsets.UTF_8.name())

  private fun encodeNullable(value: String?): String = if (value == null) {
    NULL_VALUE
  } else {
    PRESENT_VALUE + encode(value)
  }

  private fun decodeNullable(value: String): String? = when {
    value == NULL_VALUE -> null
    value.startsWith(PRESENT_VALUE) -> decode(value.drop(1))
    else -> throw IllegalArgumentException("Invalid nullable field")
  }

  private fun encodeBoolean(value: Boolean): String = if (value) PRESENT_VALUE else NULL_VALUE

  private fun decodeBoolean(value: String): Boolean = when (value) {
    PRESENT_VALUE -> true
    NULL_VALUE -> false
    else -> throw IllegalArgumentException("Invalid boolean field")
  }
}

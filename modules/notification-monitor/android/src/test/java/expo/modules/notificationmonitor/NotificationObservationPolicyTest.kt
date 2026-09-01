package expo.modules.notificationmonitor

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NotificationObservationPolicyTest {
  @Test
  fun `excludes notifications posted by AdShield itself`() {
    assertFalse(
      NotificationObservationPolicy.shouldObserve(
        sourcePackage = "com.anonymous.adshield",
        ownPackage = "com.anonymous.adshield",
      ),
    )
  }

  @Test
  fun `observes group summaries so eligibility can record them as skipped`() {
    assertTrue(
      NotificationObservationPolicy.shouldObserve(
        sourcePackage = "com.example.app",
        ownPackage = "com.anonymous.adshield",
      ),
    )
  }

  @Test
  fun `accepts a normal notification from another package`() {
    assertTrue(
      NotificationObservationPolicy.shouldObserve(
        sourcePackage = "com.example.app",
        ownPackage = "com.anonymous.adshield",
      ),
    )
  }
}

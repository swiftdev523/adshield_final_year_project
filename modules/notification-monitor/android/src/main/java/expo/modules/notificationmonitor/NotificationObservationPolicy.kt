package expo.modules.notificationmonitor

internal object NotificationObservationPolicy {
  fun shouldObserve(
    sourcePackage: String,
    ownPackage: String,
  ): Boolean = sourcePackage != ownPackage
}

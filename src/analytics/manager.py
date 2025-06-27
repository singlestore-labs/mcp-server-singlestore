import segment.analytics as segment_analytics

from ..logger import get_logger

# Get logger for this module
logger = get_logger()


class AnalyticsManager:
    def __init__(self, segment_write_key=None, debug=False, enabled=True):
        self.enabled = enabled
        self.analytics = None
        self.segment_write_key = segment_write_key
        self.debug = debug
        self._init_analytics()

    def _init_analytics(self):
        # Analytics are not enabled for local instances
        if not self.enabled:
            logger.debug("Analytics are not available for local instances.")
            return
        try:
            if self.segment_write_key:
                segment_analytics.write_key = self.segment_write_key
                segment_analytics.debug = self.debug
                segment_analytics.on_error = self._on_error
                self.analytics = segment_analytics
                self.enabled = True
        except Exception as e:
            logger.warning(f"Analytics not enabled: {e}")
            self.enabled = False

    def _on_error(self, error, items):
        logger.error("Analytics error:", error)

    def track_event(
        self, user_id: str, event_name: str, properties: dict | None = None
    ):
        try:
            if not self.enabled:
                return
            self.analytics.track(
                user_id=user_id, event=event_name, properties=properties or {}
            )
        except Exception as e:
            logger.error(f"Failed to track event: {e}")

    def identify(self, user_id: str, traits: dict | None = None):
        try:
            if not self.enabled:
                return
            self.analytics.identify(user_id=user_id, traits=traits or {})
        except Exception as e:
            logger.error(f"Failed to identify user: {e}")

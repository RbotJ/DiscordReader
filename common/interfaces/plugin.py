class FeaturePlugin:
    """Base interface for application feature plugins."""

    def register(self, app):
        """Register the feature with the given Flask app."""
        pass

    def get_routes(self):
        """Return additional routes to register."""
        return []

    def get_events(self):
        """Return events the feature wants to subscribe to."""
        return []

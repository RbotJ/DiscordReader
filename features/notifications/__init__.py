"""Notifications feature plugin."""
from common.interfaces.plugin import FeaturePlugin

class NotificationsPlugin(FeaturePlugin):
    pass

def get_plugin():
    return NotificationsPlugin()

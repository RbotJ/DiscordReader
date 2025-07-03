"""Options selector feature plugin."""
from common.interfaces.plugin import FeaturePlugin

class OptionsSelectorPlugin(FeaturePlugin):
    pass

def get_plugin():
    return OptionsSelectorPlugin()

"""Setups feature plugin."""
from importlib import import_module
from features.blueprint_registry import BLUEPRINT_REGISTRY, SPECIAL_BLUEPRINTS
from common.interfaces.plugin import FeaturePlugin

class SetupsPlugin(FeaturePlugin):
    def register(self, app):
        prefix = __name__
        for name, module_path, attr in BLUEPRINT_REGISTRY + SPECIAL_BLUEPRINTS:
            if module_path.startswith(prefix):
                try:
                    module = import_module(module_path)
                    blueprint = getattr(module, attr, None)
                    if blueprint:
                        app.register_blueprint(blueprint)
                except Exception:
                    pass

def get_plugin():
    return SetupsPlugin()

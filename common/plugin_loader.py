import importlib
import logging
from typing import List, Optional, Type

logger = logging.getLogger(__name__)


def discover_class(class_name: str, module_paths: List[str]) -> Optional[Type]:
    """Dynamically discover a class from a list of module paths.

    Args:
        class_name: Name of the class to locate.
        module_paths: Modules to search for the class.

    Returns:
        The class object if found, otherwise None.
    """
    for module_path in module_paths:
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, class_name):
                return getattr(module, class_name)
        except ImportError as e:
            logger.debug("Plugin module %s not found: %s", module_path, e)
        except Exception as e:
            logger.warning("Error loading plugin %s: %s", module_path, e)
    logger.warning("%s not found in plugins: %s", class_name, module_paths)
    return None

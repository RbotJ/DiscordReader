"""
Route Registry

Centralized route registration system to eliminate duplicate register_routes 
functions across feature modules and provide consistent route management.
"""

import logging
from typing import Dict, List, Callable, Any
from flask import Flask

logger = logging.getLogger(__name__)


class RouteRegistry:
    """
    Centralized registry for managing route registration across all features.
    
    Eliminates the need for individual register_routes functions in each 
    feature module by providing a unified registration system.
    """
    
    def __init__(self):
        self.feature_modules: Dict[str, Any] = {}
        self.registered_routes: List[str] = []
        self.registration_functions: List[Callable] = []
    
    def register_feature(self, feature_name: str, module_or_function: Any):
        """
        Register a feature module or registration function.
        
        Args:
            feature_name: Name of the feature (e.g., 'setups', 'discord')
            module_or_function: Either a module with register_routes function 
                               or a direct registration function
        """
        logger.info(f"Registering feature: {feature_name}")
        
        if hasattr(module_or_function, 'register_routes'):
            # Module with register_routes function
            self.feature_modules[feature_name] = module_or_function
            self.registration_functions.append(module_or_function.register_routes)
        elif callable(module_or_function):
            # Direct registration function
            self.feature_modules[feature_name] = module_or_function
            self.registration_functions.append(module_or_function)
        else:
            logger.warning(f"Feature {feature_name} has no register_routes function")
    
    def bootstrap(self, app: Flask):
        """
        Bootstrap all registered features by calling their registration functions.
        
        Args:
            app: Flask application instance
        """
        logger.info("Bootstrapping route registry...")
        
        for i, register_func in enumerate(self.registration_functions):
            try:
                # Call the registration function with the app
                register_func(app)
                
                # Track registered routes for verification
                feature_name = list(self.feature_modules.keys())[i]
                logger.info(f"Successfully registered routes for: {feature_name}")
                
            except Exception as e:
                feature_name = list(self.feature_modules.keys())[i] if i < len(self.feature_modules) else f"function_{i}"
                logger.error(f"Failed to register routes for {feature_name}: {e}")
                raise
        
        # Log summary
        total_routes = len([rule for rule in app.url_map.iter_rules()])
        logger.info(f"Route registration complete. Total routes: {total_routes}")
        
        # Store registered routes for testing
        self.registered_routes = [str(rule.rule) for rule in app.url_map.iter_rules()]
    
    def get_registered_routes(self) -> List[str]:
        """Get list of all registered routes for testing/verification."""
        return self.registered_routes.copy()
    
    def get_registered_features(self) -> List[str]:
        """Get list of all registered feature names."""
        return list(self.feature_modules.keys())
    
    def verify_feature_routes(self, app: Flask, expected_routes: Dict[str, List[str]]) -> Dict[str, bool]:
        """
        Verify that expected routes are registered for each feature.
        
        Args:
            app: Flask application instance
            expected_routes: Dict mapping feature names to expected route patterns
            
        Returns:
            Dict mapping feature names to verification status
        """
        verification_results = {}
        actual_routes = [str(rule.rule) for rule in app.url_map.iter_rules()]
        
        for feature_name, expected in expected_routes.items():
            missing_routes = []
            for expected_route in expected:
                if not any(expected_route in actual_route for actual_route in actual_routes):
                    missing_routes.append(expected_route)
            
            verification_results[feature_name] = len(missing_routes) == 0
            
            if missing_routes:
                logger.warning(f"Feature {feature_name} missing routes: {missing_routes}")
            else:
                logger.info(f"Feature {feature_name} routes verified successfully")
        
        return verification_results


# Global registry instance
registry = RouteRegistry()


def register_feature(feature_name: str, module_or_function: Any):
    """
    Convenience function to register a feature with the global registry.
    
    Args:
        feature_name: Name of the feature
        module_or_function: Module or function to register
    """
    registry.register_feature(feature_name, module_or_function)


def bootstrap_routes(app: Flask):
    """
    Convenience function to bootstrap all routes with the global registry.
    
    Args:
        app: Flask application instance
    """
    registry.bootstrap(app)
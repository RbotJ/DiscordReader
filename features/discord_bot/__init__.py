"""
Discord Bot Feature Module

Vertical slice for Discord bot functionality including:
- Real-time message monitoring
- Integration with existing ingestion pipeline
- Bot health monitoring and management
"""

__version__ = '1.0.0'


def register_routes(app):
    """Register Discord bot routes including live metrics API."""
    from .api import discord_api_bp
    from .dashboard import discord_bp
    
    # Register API endpoints for live metrics
    app.register_blueprint(discord_api_bp)
    
    # Register dashboard routes
    app.register_blueprint(discord_bp)
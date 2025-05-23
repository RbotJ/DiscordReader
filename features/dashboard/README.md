
# Dashboard Feature

This feature provides a unified dashboard system for the A+ Trading application, following vertical slice architecture principles.

## Components

The dashboard feature is organized into:

- **components/** - Reusable UI components (charts, tables, forms)
- **services/** - Business logic for data retrieval and processing
- **views/** - Different dashboard views for specific use cases
- **api_routes.py** - API endpoints for dashboard data

## Available Views

- **Main Dashboard** - Overview of account status, positions, and performance
- **Discord Stats** - Statistics about Discord messages and trading setups
- **Trade Monitor** - Real-time monitoring of active trades
- **Setup Monitor** - Tracking of trade setups and market signals
- **Daily Performance** - Analysis of daily ticker performance

## Usage

The dashboard is served through the main Flask application.

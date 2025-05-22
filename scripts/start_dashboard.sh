#!/bin/bash
# Unified A+ Trading Dashboard Launcher
# Usage: ./scripts/start_dashboard.sh [mode] [options]

MODES="main|trading|flask|monitor|discord|workflow"
DEFAULT_PORT=8501
DEFAULT_ADDRESS="0.0.0.0"

# Display usage information
show_usage() {
    echo "A+ Trading Dashboard Launcher"
    echo "Usage: $0 [mode]"
    echo ""
    echo "Available modes:"
    echo "  main      - Main trading application (streamlit_app.py)"
    echo "  trading   - Trading dashboard (streamlit_dashboard.py)"
    echo "  flask     - Flask-connected dashboard (flask_streamlit_dashboard.py)"
    echo "  monitor   - Monitoring dashboard (monitoring_dashboard.py)"
    echo "  discord   - Discord stats dashboard (discord_stats_dashboard.py)"
    echo "  workflow  - Workflow mode with headless settings (streamlit_app.py)"
    echo ""
    echo "If no mode is specified, 'main' will be used."
}

# Mode-specific configurations
case "$1" in
    "main"|"")
        echo "Starting Main Trading Application..."
        APP_FILE="streamlit_app.py"
        PORT=8501
        ADDRESS=$DEFAULT_ADDRESS
        EXTRA_FLAGS=""
        ;;
    "trading")
        echo "Starting Trading Dashboard..."
        APP_FILE="streamlit_dashboard.py"
        PORT=8501
        ADDRESS=$DEFAULT_ADDRESS
        EXTRA_FLAGS=""
        ;;
    "flask")
        echo "Starting Flask-connected Streamlit Trading Dashboard..."
        APP_FILE="flask_streamlit_dashboard.py"
        PORT=8501
        ADDRESS=$DEFAULT_ADDRESS
        EXTRA_FLAGS=""
        ;;
    "monitor")
        echo "Starting A+ Trading monitoring dashboard..."
        APP_FILE="monitoring_dashboard.py"
        PORT=8501
        ADDRESS=$DEFAULT_ADDRESS
        EXTRA_FLAGS=""
        ;;
    "discord")
        echo "Starting Discord Stats Dashboard..."
        APP_FILE="discord_stats_dashboard.py"
        PORT=8502
        ADDRESS=$DEFAULT_ADDRESS
        EXTRA_FLAGS=""
        ;;
    "workflow")
        echo "Starting Streamlit Trading Dashboard in workflow mode..."
        APP_FILE="streamlit_app.py"
        PORT=8501
        ADDRESS=$DEFAULT_ADDRESS
        EXTRA_FLAGS="--server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false"
        ;;
    "help"|"-h"|"--help")
        show_usage
        exit 0
        ;;
    *)
        echo "Error: Unknown mode '$1'"
        echo ""
        show_usage
        exit 1
        ;;
esac

# Check if the target file exists
if [ ! -f "$APP_FILE" ]; then
    echo "Error: Dashboard file not found: $APP_FILE"
    echo "Please ensure the file exists in the current directory."
    exit 1
fi

# Build the streamlit command
STREAMLIT_CMD="streamlit run $APP_FILE --server.port=$PORT --server.address=$ADDRESS"

# Add extra flags if specified
if [ -n "$EXTRA_FLAGS" ]; then
    STREAMLIT_CMD="$STREAMLIT_CMD $EXTRA_FLAGS"
fi

# Display the command being executed
echo "Executing: $STREAMLIT_CMD"
echo ""

# Run the streamlit command
exec $STREAMLIT_CMD
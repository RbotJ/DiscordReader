# A+ Trading Dashboard Scripts

This directory contains unified launch scripts for the A+ Trading application.

## Unified Dashboard Launcher

The `start_dashboard.sh` script replaces all individual dashboard launch scripts and provides a single entry point for all dashboard modes.

### Usage

```bash
./scripts/start_dashboard.sh [mode]
```

### Available Modes

| Mode | Description | Target File | Port |
|------|-------------|-------------|------|
| `main` (default) | Main trading application | `streamlit_app.py` | 8501 |
| `trading` | Trading dashboard | `streamlit_dashboard.py` | 8501 |
| `flask` | Flask-connected dashboard | `flask_streamlit_dashboard.py` | 8501 |
| `monitor` | Monitoring dashboard | `monitoring_dashboard.py` | 8501 |
| `discord` | Discord stats dashboard | `discord_stats_dashboard.py` | 8502 |
| `workflow` | Workflow mode (headless) | `streamlit_app.py` | 8501 |

### Examples

```bash
# Start main trading application (default)
./scripts/start_dashboard.sh

# Start specific mode
./scripts/start_dashboard.sh trading
./scripts/start_dashboard.sh monitor
./scripts/start_dashboard.sh discord

# Get help
./scripts/start_dashboard.sh help
```

### Migration from Old Scripts

The following scripts have been replaced and marked with `.old` extension:

- `run_streamlit_dashboard.sh.old` → `./scripts/start_dashboard.sh trading`
- `start_streamlit.sh.old` → `./scripts/start_dashboard.sh main`
- `run_flask_streamlit.sh.old` → `./scripts/start_dashboard.sh flask`
- `run_monitoring.sh.old` → `./scripts/start_dashboard.sh monitor`
- `run_trade_monitor.sh.old` → `./scripts/start_dashboard.sh monitor`
- `start_trade_monitor.sh.old` → `./scripts/start_dashboard.sh monitor`
- `run_discord_stats.sh.old` → `./scripts/start_dashboard.sh discord`
- `start_streamlit_workflow.sh.old` → `./scripts/start_dashboard.sh workflow`

The `.old` files can be safely removed after verifying the new unified script works correctly.
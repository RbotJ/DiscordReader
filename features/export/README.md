# Export Feature

The export feature allows administrators to download ingested Discord messages as
JSON for compliance or backup purposes. Messages can be filtered by channel,
author, and date range. A small CLI tool is provided for offline exports.

## API
`GET /api/export/messages`
Query parameters:
- `channel`: filter by channel ID
- `author`: filter by author ID
- `start`: start datetime (ISO format)
- `end`: end datetime (ISO format)
- `limit`: maximum number of messages (default 1000)

The endpoint returns a downloadable JSON file. To receive raw JSON without the
download header, use `/api/export/messages.json`.

## Dashboard
An "Export" button was added to the system status dashboard. It links to a
simple form at `/dashboard/export` where exports can be initiated.

## CLI
Run `python -m features.export.cli --help` for command usage.

# Ingestion Slice

This slice ingests Discord messages and stores them for further processing.

### Submodules:
- `fetcher.py` – Retrieves messages from Discord
- `processor.py` – Normalizes and routes messages
- `store.py` – Persistence layer
- `validator.py` – Schema validation

### Interfaces:
- Listens to Discord events
- Publishes `message.stored`

### TODO:
- Optimize message batching
- Expand validation rules

# Setups Slice

This slice persists parsed trading setups and exposes them via API.

### Submodules:
- `api.py` – HTTP endpoints for setup data
- `models.py` – Database models
- `service.py` – Logic for creating and querying setups

### Interfaces:
- Publishes `setup.created`
- Consumed by dashboard and strategy slices

### TODO:
- Add pagination to APIs
- Implement cleanup of stale setups

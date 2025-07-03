# Account Slice

This slice manages user account information and related API endpoints.

### Submodules:
- `api_routes.py` – HTTP routes for account actions
- `info.py` – Data retrieval and account models
- `service.py` – Business logic for account management

### Interfaces:
- Exposes `/account` API routes
- Used by other slices to fetch account details

### TODO:
- Persist account preferences
- Add unit tests

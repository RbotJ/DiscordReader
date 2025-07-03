# Parsing Slice

This slice handles all logic for parsing A+ trade setups from Discord messages.

### Submodules:
- `aplus_parser.py` – Logic specific to A+ format
- `parser.py` – Core parsing utilities
- `store.py` – Persistence for parsed setups

### Interfaces:
- Listens to `message.stored`
- Publishes `setup.parsed`

### TODO:
- Refactor shared logic to `common/parsing`
- Add more LLM parsing strategies

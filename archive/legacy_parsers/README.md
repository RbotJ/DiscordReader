# Legacy Parser Archive

This directory contains deprecated parser components that have been replaced by the refactored A+ parser system.

## Archived Components

### ParsedSetupDTO
- **Original Location**: `features/parsing/parser.py`
- **Replacement**: `features/parsing/setup_converter.py` with `TradeSetup` dataclass
- **Reason**: Replaced by direct TradeSetup model usage for better data flow

### Legacy Test Files
- **Original Location**: `tests/legacy_mirror/`
- **Status**: Comparison tests for legacy vs new parser implementations

## Migration Notes

The new parser system eliminates DTOs in favor of direct model usage:
- `ParsedSetupDTO` → `TradeSetup` dataclass
- Direct database model integration
- Enhanced field mappings (label, direction, target_prices, keywords)
- Token-based parsing instead of regex patterns

## Archival Date
June 16, 2025
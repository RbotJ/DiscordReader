# Archive Directory

This directory contains legacy code that has been replaced during the A+ parser refactoring project.

## Archived Components

### DTOs (Data Transfer Objects)
- `ParsedSetupDTO` - Legacy setup data transfer object
- `APlusSetupDTO` - Legacy A+ specific setup DTO
- Related DTO validation logic

### Parsers
- Legacy `parser.py` implementations
- Old regex-based parsing logic
- Brittle full-line pattern matching code

## Archive Date
Archived on: 2025-06-16

## Replacement
These components have been replaced with:
- `TradeSetup` dataclass (features/parsing/models.py)
- Token-based parsing approach (features/parsing/aplus_parser.py)
- Structured field mappings and enhanced data flow

## Note
These files are preserved for reference only and should not be used in new development.
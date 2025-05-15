# A+ Trading App Documentation

This directory contains documentation for the A+ Trading App, including architecture decisions, database schema, and development guidelines.

## Contents

- [`architecture.md`](./architecture.md) - Detailed architecture overview
- [`schema.sql`](./schema.sql) - Database schema definition
- [`adr/`](./adr/) - Architecture Decision Records

## Architecture Decision Records (ADRs)

The `adr/` directory contains Architecture Decision Records (ADRs), which document significant architectural decisions made during the development of the application. Each ADR includes:

- **Context**: The situation that called for a decision
- **Decision**: The decision that was made
- **Status**: Whether the decision is proposed, accepted, or superseded
- **Consequences**: What effects (positive and negative) the decision has

ADRs help maintain a historical record of key decisions and their rationale, which is valuable for understanding why certain architectural choices were made.

## Database Schema

The [`schema.sql`](./schema.sql) file defines the PostgreSQL database schema used by the application. It includes tables for:

- Setups and signals
- Options contracts
- Orders and positions
- Market data and watchlists
- Notifications and system events

The schema is designed to support the vertical-slice architecture of the application, with each feature having access to the tables it needs.

## Architecture Overview

The [`architecture.md`](./architecture.md) document provides a comprehensive overview of the application's architecture, including:

- Architectural principles
- Component structure
- Event and data flow
- Technologies used
- Security considerations
- Deployment architecture
- Future enhancements

This document is the main reference for understanding how the different components of the application work together.

## Development Guidelines

The following guidelines should be followed when contributing to the A+ Trading App:

1. **Feature-First Organization**: New code should be organized by feature, not by layer
2. **Event-Driven Communication**: Components should communicate via Redis pub/sub events
3. **Clear Documentation**: All new features should include documentation in their respective README.md files
4. **API Design**: RESTful API endpoints should follow consistent naming and response patterns
5. **Testing**: All new features should include unit tests
6. **Database Changes**: Database schema changes should be documented in schema.sql and include migration notes
# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the A+ Trading App.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR includes the following sections:

1. **Title**: A descriptive title
2. **Status**: Proposed, Accepted, Rejected, Deprecated, or Superseded
3. **Context**: The forces at play, including technological, political, social, and project constraints
4. **Decision**: The decision that was made
5. **Consequences**: The resulting context after applying the decision, including trade-offs

## List of ADRs

1. [001-vertical-slice-architecture.md](001-vertical-slice-architecture.md) - Adoption of Vertical Slice Architecture
2. [002-redis-event-orchestration.md](002-redis-event-orchestration.md) - Redis for Event Orchestration

## Creating New ADRs

When creating a new ADR, follow these steps:

1. Create a new file in this directory with the format `NNN-title-with-hyphens.md`, where `NNN` is the next available number.
2. Use the template below as a starting point.
3. Fill in the sections with relevant information.
4. Update this README.md file to include the new ADR in the list.

## ADR Template

```markdown
# ADR NNN: Title

## Status

Proposed | Accepted | Rejected | Deprecated | Superseded

## Context

Describe the forces at play, including technological, political, social, and project constraints.
These forces are probably in tension, and the purpose of this section is to describe them.

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?
List both positive and negative consequences of the decision.

## Implementation Details

How will this decision be implemented? Include any specific technical details
or steps that need to be taken to realize this decision.
```
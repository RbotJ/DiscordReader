
# ADR 002: PostgreSQL Event Orchestration

## Status

Accepted

## Context

With our decision to adopt a Vertical Slice Architecture (see [ADR-001](001-vertical-slice-architecture.md)), we needed to determine how different feature slices would communicate with each other. The communication mechanism should:

1. Support loose coupling between features
2. Allow for asynchronous processing of events
3. Be reliable and performant
4. Support different message patterns (request-response, pub-sub)
5. Be simple to implement and maintain

We considered several options:

- Direct method calls between features
- HTTP REST APIs between features
- Message brokers (Redis, RabbitMQ, Kafka)
- Shared database as an event store

## Decision

We have decided to use **PostgreSQL** for event orchestration between feature slices.

PostgreSQL provides a robust, persistent event store that allows for decoupled communication between components. Each feature can publish events to the events table, and other features can poll or subscribe to those events through database queries.

Key aspects of our implementation:

1. **Event Table**: We store events in a dedicated `events` table with columns for:
   ```sql
   CREATE TABLE events (
     id SERIAL PRIMARY KEY,
     channel VARCHAR(50) NOT NULL,
     data JSONB NOT NULL,
     created_at TIMESTAMP NOT NULL DEFAULT NOW()
   );
   ```

2. **Event Format**: Events are JSON objects stored in the data column with a standard structure:
   ```json
   {
     "event_type": "signal.triggered",
     "timestamp": "2025-05-15T10:30:45Z",
     "data": {
       // Event-specific data
     },
     "metadata": {
       // Optional metadata
     }
   }
   ```

3. **Event Client**: We use a wrapper around SQLAlchemy to standardize event publishing and subscription:
   ```python
   # Publishing events
   event_client.publish("signal.triggered", signal_data)
   
   # Retrieving events
   events = event_client.get_latest_events("setup.received")
   ```

4. **Event Channels**: Events are categorized by channel names stored in the channel column

## Consequences

Positive:

- **Durability**: Events are automatically persisted and can be replayed
- **Transactional**: Events can participate in database transactions
- **Queryable**: Full SQL querying capabilities for event analysis
- **Simplicity**: Single system for both storage and messaging
- **Consistency**: ACID properties ensure reliable event delivery

Negative:

- **Polling Required**: No native pub/sub mechanism
- **Latency**: Slightly higher latency compared to in-memory systems
- **Resource Usage**: Database connections needed for event monitoring
- **Scaling**: Limited by database performance

## Implementation Details

Our PostgreSQL event system includes:

1. **Event Models**: SQLAlchemy models defining event structure and relationships

2. **Event Client**: A client wrapper handling event operations and error cases

3. **Event Documentation**: Clear documentation of supported event types

4. **Error Handling**: Robust error handling including event validation

5. **Monitoring**: Database monitoring for event table performance

This approach provides a reliable, persistent foundation for communication between our vertical feature slices while simplifying our infrastructure by removing Redis as a dependency.

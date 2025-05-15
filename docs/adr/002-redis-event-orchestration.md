# ADR 002: Redis Event Orchestration

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
- Message broker (Redis, RabbitMQ, Kafka)
- Shared database as an event store

## Decision

We have decided to use **Redis Pub/Sub** for event orchestration between feature slices.

Redis Pub/Sub provides a lightweight, in-memory message broker that allows for decoupled communication between components. Each feature can publish events to specific channels, and other features can subscribe to those channels to receive events.

Key aspects of our implementation:

1. **Event Channels**: We will define a set of standardized event channels for different types of events (e.g., `setup.received`, `market.price_update`, `signal.triggered`, etc.)

2. **Event Format**: Events will be JSON-serialized objects with a standard structure:
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

3. **Redis Client Wrapper**: We will create a wrapper around the Redis client to standardize event publishing and subscription:
   ```python
   # Publishing events
   redis_client.publish("signal.triggered", signal_data)
   
   # Subscribing to events
   redis_client.subscribe(["setup.received", "market.price_update"])
   ```

4. **Durable Events**: For critical events that need persistence, we will also store them in the database in addition to publishing them via Redis.

## Consequences

Positive:

- **Loose Coupling**: Features are decoupled and can evolve independently
- **Scalability**: Can easily scale by adding more subscribers to process events
- **Flexibility**: Easy to add new features by subscribing to relevant events
- **Testability**: Features can be tested in isolation by mocking events
- **Performance**: Redis provides high-performance, in-memory messaging

Negative:

- **Eventual Consistency**: The system is eventually consistent rather than immediately consistent
- **Error Handling**: Need careful error handling for message processing failures
- **Debugging**: Can be harder to debug event-driven systems
- **Learning Curve**: Developers need to understand event-driven architecture

## Implementation Details

Our Redis event orchestration will include:

1. **Common Redis Client**: A shared Redis client wrapper in the `common` directory that handles serialization, connection management, and error handling.

2. **Standard Event Schema**: A standardized schema for all events to ensure consistency.

3. **Event Documentation**: Clear documentation of all event types, their purpose, and their data structure.

4. **Error Handling**: Robust error handling for event processing, including dead-letter queues for failed events.

5. **Monitoring**: Monitoring of event queues and processing to detect bottlenecks or failures.

This approach will provide a flexible, scalable foundation for communication between our vertical feature slices.
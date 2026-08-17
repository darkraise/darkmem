# Capture pipeline

Every capture door enqueues a buffer row and returns 202 with an ack.

The flush worker claims rows with FOR UPDATE SKIP LOCKED.

## Phases

- Content embed runs first and registers the fingerprint.
- Entity dedup probes one candidate per name and type pair.

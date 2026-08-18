# Runbook — break-glass content purge

**Status:** operator procedure, not an application feature. Written 2026-08-06 as rider R2
of T2.59's ruling (option D: accept the residue and document it).

## When this applies

Exactly one case: **content that must not exist anywhere** — a pasted credential, a key, a
token, someone else's personal data. Nothing else. Deleting a memory through the API or UI
is the normal path and is sufficient for ordinary removal.

## Why this is a procedure and not a button

Darkmem's `events` journal is append-only and enforced as such by three trigger kinds (a
row-level UPDATE/DELETE guard on the parent, a statement-level TRUNCATE guard, and a
per-child TRUNCATE guard stamped by `events_ensure_partition`). That is deliberate: the
journal is the record of what the system did, and a consolidation cycle whose evidence can
be edited afterwards describes a history that did not happen.

Giving the application a code path that rewrites the journal would cost more than the
residue it removes — it would put a "make this never have happened" primitive one bug or
one compromised session away from the audit substrate. **The operator already owns the
database.** This procedure just writes down what that ownership means, so the dangerous
capability lives with the human who has the superuser password rather than in the app.

## What the residue actually is

Deleting a memory removes the row, its embeddings (FK cascade), its tags and its graph
contributions. These survive, by design:

| Store | What survives | Bounded? |
|---|---|---|
| `events` payloads | content previews; full refine summaries in `consolidated` / `undone`; contradiction counterpart triples in `verified` | No — append-only |
| `knowledge_triples.fact` | the lifted sentence | No — a fact outlives any one asserting memory |
| `messages.context` | citation snippets, and cited fact rows untrimmed | Until the conversation is deleted |
| `memory_buffer` | raw content on `done` rows | Yes — `buffer_done_retention_hours`, default 24 |

Two remedies already exist and should be tried first: **delete the conversation** (cascades
its snippets and its prose) and **wait out or shorten the buffer retention** (a config row).

## The procedure

Read all of it before starting. Steps 1 and 6 are the ones people skip.

1. **Rotate the secret first.** Everything below is slower than an attacker. Purging the
   database does not un-leak a credential that was live; rotating does. If the content is
   not a credential, skip to 2.

2. **Stop the application.** Both the API and any running jobs — a consolidation pass
   mid-flight will re-derive from rows you are about to edit.
   ```
   docker compose down          # or stop the uvicorn process
   ```

3. **Find every occurrence.** Do not guess which stores hold it.
   ```sql
   SELECT id, created_at FROM events WHERE payload::text ILIKE '%<fragment>%';
   SELECT id FROM knowledge_triples WHERE fact ILIKE '%<fragment>%';
   SELECT id FROM messages WHERE context::text ILIKE '%<fragment>%' OR content ILIKE '%<fragment>%';
   SELECT id FROM memory_buffer WHERE content ILIKE '%<fragment>%';
   SELECT id FROM memories WHERE content ILIKE '%<fragment>%';
   ```

4. **Edit as superuser with the guards disabled for the session.** `session_replication_role`
   suppresses the append-only triggers for this connection only.
   ```sql
   BEGIN;
   SET LOCAL session_replication_role = 'replica';
   -- Prefer redaction over deletion where the row's existence is itself the record:
   UPDATE events SET payload = jsonb_set(payload, '{content_preview}', '"[redacted]"')
     WHERE id = '<id>' AND created_at = '<created_at>';   -- both, always: composite PK
   DELETE FROM memory_buffer WHERE id = '<id>';
   COMMIT;
   ```
   **`events` is RANGE-partitioned with a composite `PRIMARY KEY (id, created_at)`.** A bare
   `WHERE id = ...` scans every monthly child; always carry the `created_at` bound.

5. **Reclaim the pages.** An `UPDATE` leaves the old tuple readable on disk until vacuumed.
   ```sql
   VACUUM FULL events;      -- takes an exclusive lock; size it against your downtime
   VACUUM FULL messages;
   ```

6. **Deal with backups.** This is the step that makes the rest meaningful. Any dump or
   volume snapshot taken before the purge still contains the content. Rotate or destroy
   them per your retention policy, and record that you did.

7. **Restart, and verify.** Re-run the step-3 queries and confirm zero rows.

## After

Write down what happened and when — ideally as a memory in a project you keep for
operations. A break-glass purge is the one action in this system with no audit trail by
construction, because the audit trail is what it edited.

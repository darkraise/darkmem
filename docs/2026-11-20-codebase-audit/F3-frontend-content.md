# F3 — frontend content features

Reviewer findings for the 2026-11-20 audit, as returned. Summary first where the reviewer gave one, then one entry per finding. Index and verification status: `docs/2026-11-20-codebase-audit.md`.

**Counts:** 1 high, 7 medium, 11 low (finding 8 is graded medium).

**Notes mirror vs `block_verbs.py`:** it matches rule for rule. The only gaps are refusals the client can't see:
- A block id taken in another page or document gets 409, which the engine reports as "changed somewhere else".
- Missing attachment references and size limits get 422.
- No test pins the TypeScript copy to the Python one.

**Findings:**
1. **High:** sending in a second chat conversation silently aborts the first one's stream (`chat/hooks/use-chat-stream.ts:61`, with the stream state hidden for other conversations at `:202-211`). The server saves the answer only when the stream completes (`backend/app/services/chat.py:251-296`), so that answer is lost.
2. **Medium:** the documents block editor throws away the typed text on any refused or failed write (`documents/components/block-editor.tsx:189-207`, `:282-287`).
3. **Medium:** hygiene queue checkbox selections survive project and page changes, so a prune can retire rows the user can't see (`knowledge/components/hygiene-queue.tsx:87-98`, `:438-443`). "Supersede instead" acts only on the visible page, then clears every selection (`:651-660`).
4. **Medium (unconfirmed):** after the 24 h token expires mid-edit, the next save redirects to `/login`, and in-memory drafts from both editors are lost (`lib/api.ts:10-23`, `notes/lib/page-sync.ts:35-40`).
5. **Medium:** every chat token re-parses the markdown of every earlier message (`chat-messages.tsx:353-374`).
6. **Medium:** a task filter on an open workstream re-downloads the whole ledger every 5 s (`hooks/api/use-worklog-api.ts:199-223`).
7. **Medium:** after a refusal, the documents write queue re-reads the hash and sends the next write anyway, which defeats the conflict check (`documents/lib/mutation-queue.ts:22,28-31`).
8. **Medium:** a failed page title rename is silent (`notes/page-pane.tsx:58-62`).
9. **Low:**
   - Dead code: `MemoryCommandPalette` (only a test imports the module), `useBlockMove` (only a test imports it), and `rank_note`/`consequence` in `knowledge/use-review-queue.ts`, which are computed but never shown.
   - The pager is hand-written twice although darkraise-ui ships `pagination`, and the two knowledge queues use different list patterns.
   - The two block editors duplicate the hash-precondition plumbing and handle conflicts differently.
   - A first chat turn that never completes leaves an "Untitled" conversation the client never learns about.
   - Deleting a conversation has no error handling.
   - Two quick board edits to one register conflict with each other.
   - Notes does a full-document conversion on every keystroke.
   - The facts list's filter options cover only the pages already loaded.

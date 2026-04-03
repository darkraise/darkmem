# Chat Frontend Design

**Date:** 2026-04-04
**Branch:** feat/backend-foundation
**Scope:** Sub-project 2 of 2 — frontend only. Backend (sub-project 1) is already implemented.

## Summary

Add a dedicated `/chat` page with sidebar conversation list and chat area, a floating bottom-right overlay on the graph page for contextual questions, SSE streaming with markdown rendering, and collapsible source badges. Consumes the chat backend API built in sub-project 1.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chat page layout | Sidebar + chat area | Familiar pattern, always-visible conversation list |
| Graph overlay | Bottom-right floating panel | Minimal graph obstruction, quick toggle |
| @-mention autocomplete | None for v1 | Significant complexity, backend parses raw syntax regardless |
| Response rendering | Markdown via react-markdown + source badges | LLM outputs markdown, badges match existing graph panel patterns |

## 1. Components and File Structure

### New files

| File | Purpose |
|------|---------|
| `frontend/src/pages/Chat.tsx` | Dedicated `/chat` page with sidebar + chat area |
| `frontend/src/components/chat/ChatSidebar.tsx` | Conversation list with "New" button, active selection |
| `frontend/src/components/chat/ChatMessages.tsx` | Scrollable message list with markdown and source badges |
| `frontend/src/components/chat/ChatInput.tsx` | Auto-growing textarea with send button |
| `frontend/src/components/chat/ChatOverlay.tsx` | Floating bottom-right panel + toggle bubble for graph page |
| `frontend/src/components/chat/SourceBadges.tsx` | Collapsible source chips (memories/entities) |

### Modified files

| File | Change |
|------|--------|
| `frontend/src/hooks/useApi.ts` | Add conversation CRUD hooks and `useChatStream` |
| `frontend/src/pages/UnifiedGraph.tsx` | Add `ChatOverlay` component |
| Router config (App.tsx or similar) | Add `/chat` route |
| Sidebar navigation | Add "Chat" link |

### New dependency

- `react-markdown` — renders LLM markdown responses

## 2. Chat Page Layout

### Left Sidebar (280px fixed)

- Header: "Conversations" title + "+ New" button
- Scrollable list of conversations from `GET /api/v1/chat/conversations`
- Each item shows: truncated title (or "Untitled"), relative timestamp
- Active conversation highlighted with `bg-primary/20`
- Click selects and loads messages
- Trash icon on hover to delete (calls `DELETE /api/v1/chat/conversations/{id}`)

### Right Chat Area (flex-1)

- **Header bar (sticky):** Conversation title, editable on click (calls `PATCH`)
- **Messages area (scrollable):** Auto-scrolls to bottom on new messages
  - User messages: right-aligned, `bg-muted` bubble
  - Assistant messages: left-aligned, rendered as markdown via `react-markdown`
  - `SourceBadges` component below each assistant message
- **Input area (sticky bottom):** Auto-growing `textarea` (max 4 lines), send button. Disabled while streaming. "Stop" button during active stream. Placeholder: "Ask about your memories... (@ to mention)"

### Empty State

When no conversation is selected: centered welcome message "Ask anything about your memories" with suggested prompt chips (e.g., "What do I know about Docker?", "Summarize recent decisions").

## 3. SSE Streaming Hook

Added to `frontend/src/hooks/useApi.ts`:

### `useChatStream` hook

```typescript
interface ChatStreamState {
  sendMessage: (conversationId: string | null, content: string, context?: object) => void;
  isStreaming: boolean;
  streamingContent: string;
  sources: { memories: object[]; entities: object[] } | null;
  error: string | null;
  abort: () => void;
}
```

**Flow:**
1. `sendMessage` POSTs to `/api/v1/chat/completions` with `fetch`
2. Reads `response.body` as a `ReadableStream` via `getReader()`
3. Parses `data: {...}\n\n` SSE lines from the text decoder
4. `"sources"` event → sets `sources` state
5. `"token"` event → appends to `streamingContent`
6. `"done"` event → clears streaming state, invalidates React Query cache for this conversation
7. `"error"` event → sets `error` state
8. `abort` calls `AbortController.abort()` on the fetch

### Conversation CRUD hooks

Standard React Query hooks following existing patterns in `useApi.ts`:

- `useConversations(archived?)` — `GET /api/v1/chat/conversations`
- `useConversation(id)` — `GET /api/v1/chat/conversations/{id}`
- `useCreateConversation()` — mutation, `POST /api/v1/chat/conversations`
- `useUpdateConversation()` — mutation, `PATCH /api/v1/chat/conversations/{id}`
- `useDeleteConversation()` — mutation, `DELETE /api/v1/chat/conversations/{id}`

## 4. Graph Overlay

### Toggle Bubble

- 40px purple circle button with chat icon (from lucide-react: `MessageCircle`)
- Fixed position: `bottom-4 right-4`, `z-40`
- Click toggles the panel open/closed
- Hidden when the right detail panel is open (to avoid overlap)

### Floating Panel (when open)

- 320px wide, 400px tall
- Position: `bottom-16 right-4`
- Contains:
  - **Header:** "Chat" title, "Open ↗" link (navigates to `/chat` with current conversation), close button
  - **Messages:** Same `ChatMessages` component, compact variant
  - **Input:** Same `ChatInput` component

### Automatic Context Injection

When the graph overlay is open and a node/entity is selected:
- The overlay reads `selectedNodeId` and `selectedEntityId` from the graph page state
- Includes them in the `context` field of the next message sent
- A context pill above the input shows what's referenced: "Context: PostgreSQL ×"
- Clearing the pill removes the context from the next message

### Shared Conversation

The overlay creates/uses a single conversation titled "Graph Chat". The "Open ↗" link navigates to `/chat` with that conversation's ID as a URL parameter, so the user can continue the conversation on the full page.

## 5. Source Badges

### Collapsed State (default)

A single row of compact chips below the assistant message:
- "📄 3 memories" — count of retrieved memories
- "🔷 2 entities" — count of referenced entities
- Styled as small `bg-muted` rounded badges
- Click to expand

### Expanded State

Full list of sources:
- **Memories:** Card per memory with content preview (first 80 chars), source label, tags, similarity score
- **Entities:** Name with diamond icon, entity type badge

### Data Source

- During live streaming: from the `"sources"` SSE event
- For loaded conversations: from the `context` JSONB on the assistant message

## 6. Message Rendering

Assistant messages rendered with `react-markdown`:
- Supports: headings, bold/italic, lists, code blocks (inline and fenced), links
- Code blocks with syntax highlighting (use `rehype-highlight` or similar if desired, otherwise plain `<pre>`)
- Dark theme styling matching the app's existing text colors
- Entity names mentioned with `@` could be styled distinctly in a future iteration

User messages rendered as plain text in a bubble.

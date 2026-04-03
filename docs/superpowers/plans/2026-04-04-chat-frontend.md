# Chat Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a chat UI with a dedicated `/chat` page (sidebar + chat area), a floating overlay on the graph page, SSE streaming with markdown rendering, and collapsible source badges.

**Architecture:** React components consuming the chat backend API. SSE streaming via native `fetch` + `ReadableStream`. React Query for conversation CRUD. Markdown rendering via `react-markdown`.

**Tech Stack:** React 19, React Router v7, React Query, shadcn/ui, Tailwind CSS, react-markdown, lucide-react

**Spec:** `docs/superpowers/specs/2026-04-04-chat-frontend-design.md`

---

### Task 1: Install Dependencies and Add Route/Nav

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/pages/Chat.tsx` (placeholder)

- [ ] **Step 1: Install react-markdown**

Run: `cd frontend && npm install react-markdown`

- [ ] **Step 2: Create placeholder Chat page**

```tsx
// frontend/src/pages/Chat.tsx
export default function Chat() {
  return (
    <div className="flex h-full">
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Chat page — coming soon
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add route in App.tsx**

Add import after the other page imports (after line 18):
```tsx
import Chat from "@/pages/Chat";
```

Add route after the `/pipeline` route (after line 45):
```tsx
            <Route path="/chat" element={<Chat />} />
```

- [ ] **Step 4: Add nav link in Sidebar.tsx**

Add `MessageCircle` to the lucide-react import:
```tsx
import {
  LayoutDashboard,
  Brain,
  Network,
  Hexagon,
  Atom,
  Search,
  MessageCircle,
  BarChart3,
  Cpu,
  Activity,
  Settings,
  LogOut,
} from "lucide-react";
```

Add the chat nav item after the Search entry (line 31):
```tsx
  { to: "/chat", label: "Chat", icon: MessageCircle },
```

- [ ] **Step 5: Verify**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/App.tsx frontend/src/components/Sidebar.tsx frontend/src/pages/Chat.tsx
git commit -m "feat(chat): add chat route, nav link, and react-markdown dependency"
```

---

### Task 2: Chat API Hooks

**Files:**
- Modify: `frontend/src/hooks/useApi.ts`

- [ ] **Step 1: Add conversation types and CRUD hooks**

Add at the end of the file:

```typescript
// ── Chat ─────────────────────────────────────────────

export interface ChatConversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  context: {
    memories?: { id: string; score: number }[];
    entities?: { id: string; name: string }[];
  } | null;
  created_at: string;
}

export interface ChatConversationDetail {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export function useConversations(archived = false) {
  return useQuery<{ conversations: ChatConversation[] }>({
    queryKey: ["conversations", archived],
    queryFn: () => apiFetch(`/chat/conversations?archived=${archived}`),
  });
}

export function useConversation(id: string | null) {
  return useQuery<ChatConversationDetail>({
    queryKey: ["conversation", id],
    queryFn: () => apiFetch(`/chat/conversations/${id}`),
    enabled: !!id,
  });
}

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { title?: string }) =>
      apiFetch<ChatConversation>("/chat/conversations", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export function useUpdateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; title?: string; is_archived?: boolean }) =>
      apiFetch<ChatConversation>(`/chat/conversations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/chat/conversations/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useApi.ts
git commit -m "feat(chat): add conversation CRUD hooks and types"
```

---

### Task 3: SSE Streaming Hook

**Files:**
- Create: `frontend/src/hooks/useChatStream.ts`

- [ ] **Step 1: Create the streaming hook**

```tsx
// frontend/src/hooks/useChatStream.ts
import { useState, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAuthToken } from "@/lib/api";

interface ChatSources {
  memories: { index: number; content: string; source: string; tags: string[]; score: number }[];
  entities: { id?: string; name?: string; entity_type?: string; [key: string]: unknown }[];
}

interface ChatStreamState {
  isStreaming: boolean;
  streamingContent: string;
  sources: ChatSources | null;
  error: string | null;
}

export function useChatStream() {
  const [state, setState] = useState<ChatStreamState>({
    isStreaming: false,
    streamingContent: "",
    sources: null,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const qc = useQueryClient();

  const sendMessage = useCallback(
    async (
      conversationId: string | null,
      content: string,
      context?: Record<string, unknown>,
    ) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setState({ isStreaming: true, streamingContent: "", sources: null, error: null });

      try {
        const token = getAuthToken();
        const res = await fetch("/api/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            conversation_id: conversationId,
            content,
            context: context ?? null,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const err = await res.text();
          setState((s) => ({ ...s, isStreaming: false, error: err }));
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          setState((s) => ({ ...s, isStreaming: false, error: "No stream" }));
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let accumulated = "";
        let resultConversationId: string | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const json = line.slice(6);
            try {
              const event = JSON.parse(json);
              switch (event.type) {
                case "sources":
                  setState((s) => ({
                    ...s,
                    sources: { memories: event.memories, entities: event.entities },
                  }));
                  break;
                case "token":
                  accumulated += event.content;
                  setState((s) => ({ ...s, streamingContent: accumulated }));
                  break;
                case "done":
                  resultConversationId = event.conversation_id;
                  break;
                case "error":
                  setState((s) => ({ ...s, error: event.message }));
                  break;
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }

        setState((s) => ({ ...s, isStreaming: false }));
        if (resultConversationId) {
          qc.invalidateQueries({ queryKey: ["conversation", resultConversationId] });
          qc.invalidateQueries({ queryKey: ["conversations"] });
        }

        return resultConversationId;
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setState((s) => ({ ...s, isStreaming: false, error: (err as Error).message }));
        }
      }
    },
    [qc],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  return {
    ...state,
    sendMessage,
    abort,
  };
}
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useChatStream.ts
git commit -m "feat(chat): add SSE streaming hook for chat completions"
```

---

### Task 4: SourceBadges Component

**Files:**
- Create: `frontend/src/components/chat/SourceBadges.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/chat/SourceBadges.tsx
import { useState } from "react";

interface SourceBadgesProps {
  memories: { index?: number; content?: string; source?: string; tags?: string[]; score?: number; id?: string }[];
  entities: { id?: string; name?: string; entity_type?: string }[];
}

export function SourceBadges({ memories, entities }: SourceBadgesProps) {
  const [expanded, setExpanded] = useState(false);

  if (memories.length === 0 && entities.length === 0) return null;

  return (
    <div className="mt-2">
      <div
        className="flex gap-2 flex-wrap cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        {memories.length > 0 && (
          <span className="text-xs bg-muted px-2 py-0.5 rounded-full text-muted-foreground">
            📄 {memories.length} {memories.length === 1 ? "memory" : "memories"}
          </span>
        )}
        {entities.filter((e) => !e.id?.startsWith("_")).length > 0 && (
          <span className="text-xs bg-muted px-2 py-0.5 rounded-full text-muted-foreground">
            🔷 {entities.filter((e) => !e.id?.startsWith("_")).length} {entities.filter((e) => !e.id?.startsWith("_")).length === 1 ? "entity" : "entities"}
          </span>
        )}
        <span className="text-xs text-muted-foreground/50">
          {expanded ? "▲" : "▼"}
        </span>
      </div>

      {expanded && (
        <div className="mt-2 space-y-1.5 text-xs">
          {memories.map((m, i) => (
            <div
              key={m.id ?? i}
              className="bg-muted/50 rounded-md p-2 border border-border"
            >
              <div className="text-foreground line-clamp-2">
                {m.content?.slice(0, 120) ?? `Memory ${m.id?.slice(0, 8)}`}
              </div>
              <div className="flex gap-2 mt-1 text-muted-foreground">
                {m.source && <span>{m.source}</span>}
                {m.score != null && <span>relevance: {m.score}</span>}
                {m.tags && m.tags.length > 0 && (
                  <span>{m.tags.slice(0, 3).join(", ")}</span>
                )}
              </div>
            </div>
          ))}
          {entities
            .filter((e) => e.name && !e.id?.startsWith("_"))
            .map((e, i) => (
              <div
                key={e.id ?? i}
                className="flex items-center gap-2 bg-muted/50 rounded-md p-2 border border-border"
              >
                <span
                  className="w-2.5 h-2.5 shrink-0"
                  style={{ clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)", backgroundColor: "#fb923c" }}
                />
                <span className="text-foreground">{e.name}</span>
                {e.entity_type && (
                  <span className="text-muted-foreground capitalize">{e.entity_type}</span>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/SourceBadges.tsx
git commit -m "feat(chat): add collapsible SourceBadges component"
```

---

### Task 5: ChatInput Component

**Files:**
- Create: `frontend/src/components/chat/ChatInput.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/chat/ChatInput.tsx
import { useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { SendHorizonal, Square } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
  contextLabel?: string | null;
  onClearContext?: () => void;
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  placeholder = "Ask about your memories... (@ to mention)",
  contextLabel,
  onClearContext,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const value = textareaRef.current?.value.trim();
    if (!value || isStreaming || disabled) return;
    onSend(value);
    if (textareaRef.current) textareaRef.current.value = "";
    autoResize();
  }, [onSend, isStreaming, disabled]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  return (
    <div className="border-t border-border p-3">
      {contextLabel && (
        <div className="flex items-center gap-1.5 mb-2 text-xs text-muted-foreground">
          <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full">
            Context: {contextLabel}
          </span>
          <button className="hover:text-foreground" onClick={onClearContext}>×</button>
        </div>
      )}
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder={placeholder}
          onInput={autoResize}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className="flex-1 bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:border-primary min-h-[36px] max-h-[120px]"
        />
        {isStreaming ? (
          <Button size="sm" variant="outline" className="h-9 w-9 p-0" onClick={onStop}>
            <Square className="w-3.5 h-3.5" />
          </Button>
        ) : (
          <Button size="sm" className="h-9 w-9 p-0" onClick={handleSubmit} disabled={disabled}>
            <SendHorizonal className="w-3.5 h-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/ChatInput.tsx
git commit -m "feat(chat): add ChatInput component with auto-resize and send"
```

---

### Task 6: ChatMessages Component

**Files:**
- Create: `frontend/src/components/chat/ChatMessages.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/chat/ChatMessages.tsx
import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { SourceBadges } from "@/components/chat/SourceBadges";
import type { ChatMessage } from "@/hooks/useApi";

interface ChatMessagesProps {
  messages: ChatMessage[];
  streamingContent?: string;
  streamingSources?: {
    memories: { index?: number; content?: string; source?: string; tags?: string[]; score?: number; id?: string }[];
    entities: { id?: string; name?: string; entity_type?: string }[];
  } | null;
  isStreaming?: boolean;
}

export function ChatMessages({
  messages,
  streamingContent = "",
  streamingSources = null,
  isStreaming = false,
}: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent]);

  return (
    <div className="flex-1 overflow-auto p-4 space-y-4">
      {messages.map((msg) => (
        <div key={msg.id}>
          {msg.role === "user" ? (
            <div className="flex justify-end">
              <div className="bg-muted rounded-lg px-3 py-2 text-sm max-w-[80%]">
                {msg.content}
              </div>
            </div>
          ) : (
            <div>
              <div className="prose prose-invert prose-sm max-w-none text-sm">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
              {msg.context && (
                <SourceBadges
                  memories={msg.context.memories ?? []}
                  entities={msg.context.entities ?? []}
                />
              )}
            </div>
          )}
        </div>
      ))}

      {isStreaming && streamingContent && (
        <div>
          <div className="prose prose-invert prose-sm max-w-none text-sm">
            <ReactMarkdown>{streamingContent}</ReactMarkdown>
          </div>
          {streamingSources && (
            <SourceBadges
              memories={streamingSources.memories}
              entities={streamingSources.entities}
            />
          )}
        </div>
      )}

      {isStreaming && !streamingContent && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
          Thinking...
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/chat/ChatMessages.tsx
git commit -m "feat(chat): add ChatMessages component with markdown and sources"
```

---

### Task 7: ChatSidebar Component

**Files:**
- Create: `frontend/src/components/chat/ChatSidebar.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/chat/ChatSidebar.tsx
import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";
import type { ChatConversation } from "@/hooks/useApi";

interface ChatSidebarProps {
  conversations: ChatConversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: ChatSidebarProps) {
  return (
    <div className="w-[280px] shrink-0 border-r border-border flex flex-col h-full">
      <div className="p-3 border-b border-border flex items-center justify-between">
        <span className="text-sm font-semibold">Conversations</span>
        <Button size="sm" variant="ghost" className="h-7 text-xs gap-1" onClick={onCreate}>
          <Plus className="w-3.5 h-3.5" /> New
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-0.5">
        {conversations.length === 0 && (
          <p className="text-xs text-muted-foreground p-3 text-center">
            No conversations yet
          </p>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-center gap-2 rounded-md px-3 py-2 cursor-pointer text-sm transition-colors ${
              conv.id === activeId
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
            onClick={() => onSelect(conv.id)}
          >
            <span className="flex-1 truncate">
              {conv.title || "Untitled"}
            </span>
            <span className="text-xs opacity-50 shrink-0 group-hover:hidden">
              {timeAgo(conv.updated_at)}
            </span>
            <button
              className="hidden group-hover:block text-muted-foreground hover:text-destructive shrink-0"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/chat/ChatSidebar.tsx
git commit -m "feat(chat): add ChatSidebar component with conversation list"
```

---

### Task 8: Chat Page — Full Assembly

**Files:**
- Modify: `frontend/src/pages/Chat.tsx` (replace placeholder)

- [ ] **Step 1: Build the full Chat page**

```tsx
// frontend/src/pages/Chat.tsx
import { useState, useCallback } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatMessages } from "@/components/chat/ChatMessages";
import { ChatInput } from "@/components/chat/ChatInput";
import {
  useConversations,
  useConversation,
  useCreateConversation,
  useDeleteConversation,
} from "@/hooks/useApi";
import { useChatStream } from "@/hooks/useChatStream";
import { MessageCircle } from "lucide-react";

export default function Chat() {
  const [activeId, setActiveId] = useState<string | null>(null);

  const { data: convList } = useConversations();
  const { data: convDetail } = useConversation(activeId);
  const createConv = useCreateConversation();
  const deleteConv = useDeleteConversation();
  const stream = useChatStream();

  const conversations = convList?.conversations ?? [];
  const messages = convDetail?.messages ?? [];

  const handleCreate = useCallback(async () => {
    const conv = await createConv.mutateAsync({});
    setActiveId(conv.id);
  }, [createConv]);

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteConv.mutateAsync(id);
      if (activeId === id) setActiveId(null);
    },
    [deleteConv, activeId],
  );

  const handleSend = useCallback(
    async (content: string) => {
      const resultId = await stream.sendMessage(activeId, content);
      if (!activeId && resultId) {
        setActiveId(resultId);
      }
    },
    [activeId, stream],
  );

  return (
    <div className="flex h-full">
      <ChatSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onCreate={handleCreate}
        onDelete={handleDelete}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {activeId || stream.isStreaming ? (
          <>
            <div className="px-4 py-3 border-b border-border shrink-0">
              <h2 className="text-sm font-semibold truncate">
                {convDetail?.title || "New Chat"}
              </h2>
            </div>
            <ChatMessages
              messages={messages}
              streamingContent={stream.streamingContent}
              streamingSources={stream.sources}
              isStreaming={stream.isStreaming}
            />
            <ChatInput
              onSend={handleSend}
              onStop={stream.abort}
              isStreaming={stream.isStreaming}
            />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-muted-foreground">
            <MessageCircle className="w-12 h-12 opacity-20" />
            <div className="text-center">
              <p className="text-lg font-medium text-foreground mb-1">
                Ask anything about your memories
              </p>
              <p className="text-sm">
                Start a new conversation or select one from the sidebar
              </p>
            </div>
            <div className="flex gap-2 mt-2">
              {["What do I know about Docker?", "Summarize recent decisions", "Network topology overview"].map((prompt) => (
                <button
                  key={prompt}
                  className="text-xs bg-muted hover:bg-muted/80 px-3 py-1.5 rounded-full text-foreground transition-colors"
                  onClick={async () => {
                    const resultId = await stream.sendMessage(null, prompt);
                    if (resultId) setActiveId(resultId);
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Chat.tsx
git commit -m "feat(chat): build full Chat page with sidebar, messages, and streaming"
```

---

### Task 9: ChatOverlay Component for Graph Page

**Files:**
- Create: `frontend/src/components/chat/ChatOverlay.tsx`
- Modify: `frontend/src/pages/UnifiedGraph.tsx`

- [ ] **Step 1: Create the overlay component**

```tsx
// frontend/src/components/chat/ChatOverlay.tsx
import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MessageCircle, X, ExternalLink } from "lucide-react";
import { ChatMessages } from "@/components/chat/ChatMessages";
import { ChatInput } from "@/components/chat/ChatInput";
import { useConversation, useCreateConversation } from "@/hooks/useApi";
import { useChatStream } from "@/hooks/useChatStream";

interface ChatOverlayProps {
  selectedNodeId?: string | null;
  selectedEntityId?: string | null;
}

export function ChatOverlay({ selectedNodeId, selectedEntityId }: ChatOverlayProps) {
  const [open, setOpen] = useState(false);
  const [convId, setConvId] = useState<string | null>(null);
  const [contextLabel, setContextLabel] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data: convDetail } = useConversation(convId);
  const createConv = useCreateConversation();
  const stream = useChatStream();

  const messages = convDetail?.messages ?? [];

  useEffect(() => {
    if (selectedEntityId) {
      setContextLabel(`Entity: ${selectedEntityId.slice(0, 12)}…`);
    } else if (selectedNodeId) {
      setContextLabel(`Memory: ${selectedNodeId.slice(0, 12)}…`);
    } else {
      setContextLabel(null);
    }
  }, [selectedNodeId, selectedEntityId]);

  const handleSend = useCallback(
    async (content: string) => {
      const context: Record<string, unknown> = {};
      if (selectedEntityId) context.selected_entity_id = selectedEntityId;
      else if (selectedNodeId) context.selected_node_id = selectedNodeId;

      const resultId = await stream.sendMessage(convId, content, context);
      if (!convId && resultId) setConvId(resultId);
    },
    [convId, selectedNodeId, selectedEntityId, stream],
  );

  if (!open) {
    return (
      <button
        className="fixed bottom-4 right-4 z-40 w-10 h-10 bg-primary rounded-full flex items-center justify-center text-primary-foreground shadow-lg hover:opacity-90 transition-opacity"
        onClick={() => setOpen(true)}
      >
        <MessageCircle className="w-5 h-5" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-16 right-4 z-40 w-[320px] h-[400px] bg-card border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <span className="text-sm font-semibold">Chat</span>
        <div className="flex items-center gap-1.5">
          {convId && (
            <button
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              onClick={() => navigate(`/chat?id=${convId}`)}
            >
              Open <ExternalLink className="w-3 h-3" />
            </button>
          )}
          <button
            className="text-muted-foreground hover:text-foreground p-0.5"
            onClick={() => setOpen(false)}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <ChatMessages
        messages={messages}
        streamingContent={stream.streamingContent}
        streamingSources={stream.sources}
        isStreaming={stream.isStreaming}
      />

      <ChatInput
        onSend={handleSend}
        onStop={stream.abort}
        isStreaming={stream.isStreaming}
        contextLabel={contextLabel}
        onClearContext={() => setContextLabel(null)}
        placeholder="Ask about selection..."
      />
    </div>
  );
}
```

- [ ] **Step 2: Add ChatOverlay to UnifiedGraph page**

Add import at the top of `frontend/src/pages/UnifiedGraph.tsx`:
```tsx
import { ChatOverlay } from "@/components/chat/ChatOverlay";
```

Add `<ChatOverlay>` inside the graph container `<div>`, just before the closing `</div>` of the `memoryCount > 0` block. It needs access to `selectedNodeId` and `selectedEntityId`:

```tsx
            <ChatOverlay
              selectedNodeId={selectedNodeId}
              selectedEntityId={selectedEntityId}
            />
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/ChatOverlay.tsx frontend/src/pages/UnifiedGraph.tsx
git commit -m "feat(chat): add floating ChatOverlay to graph page"
```

---

### Task 10: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

Expected: No errors.

- [ ] **Step 2: Production build**

Run: `cd frontend && npx vite build 2>&1 | tail -10`

Expected: Build succeeds.

- [ ] **Step 3: Visual verification**

Start dev server and verify:
1. `/chat` page loads with sidebar and empty state
2. "Chat" link appears in sidebar navigation
3. Creating a new conversation works
4. On Unified Graph page, the purple chat bubble appears at bottom-right
5. Clicking the bubble opens the overlay panel

- [ ] **Step 4: Commit any fixes**

```bash
git add -u frontend/
git commit -m "chore(chat): final fixes from verification"
```

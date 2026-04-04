# Chat UI Visual Polish — Ambient Glow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply an "Ambient Glow" visual polish to all chat UI components — deep dark base with restrained indigo/violet luminance on interactive elements.

**Architecture:** Pure visual reskin. Update CSS theme tokens first (foundation), then add utility classes and keyframes, then reskin each component file one at a time. No API, hook, or structural changes. Each task produces a working commit.

**Tech Stack:** Tailwind CSS 4, React 19, shadcn/ui (base-nova). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-04-chat-ui-visual-polish-design.md`

---

### Task 1: Update Theme Tokens

**Files:**
- Modify: `frontend/src/index.css:55-87` (the `.dark` block)

- [ ] **Step 1: Replace the `.dark` color block**

Replace the entire `.dark { ... }` block with:

```css
.dark {
  --background: #0a0e14;
  --foreground: #e2e8f0;
  --card: #0f1318;
  --card-foreground: #e2e8f0;
  --popover: #0f1318;
  --popover-foreground: #e2e8f0;
  --primary: #818cf8;
  --primary-foreground: #0a0e14;
  --secondary: #1e1b4b;
  --secondary-foreground: #e2e8f0;
  --muted: #12161d;
  --muted-foreground: #64748b;
  --accent: #1e1b4b;
  --accent-foreground: #e2e8f0;
  --destructive: #f87171;
  --border: rgba(99,102,241,0.12);
  --input: rgba(99,102,241,0.12);
  --ring: #6366f1;
  --chart-1: #818cf8;
  --chart-2: #34d399;
  --chart-3: #c4b5fd;
  --chart-4: #fbbf24;
  --chart-5: #f472b6;
  --sidebar: #0f1318;
  --sidebar-foreground: #e2e8f0;
  --sidebar-primary: #818cf8;
  --sidebar-primary-foreground: #e2e8f0;
  --sidebar-accent: #1e1b4b;
  --sidebar-accent-foreground: #e2e8f0;
  --sidebar-border: rgba(99,102,241,0.12);
  --sidebar-ring: #6366f1;
  --glow-primary: rgba(99,102,241,0.15);
  --glow-primary-subtle: rgba(99,102,241,0.06);
}
```

- [ ] **Step 2: Verify the app still renders**

Run: `cd frontend && npm run dev`
Open browser. The entire app should now show the new indigo-tinted dark palette. All borders should have a faint purple tint. Primary-colored elements (buttons, links) should be indigo instead of blue.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "style(theme): update dark palette to indigo/violet ambient glow"
```

---

### Task 2: Add CSS Utilities and Keyframes

**Files:**
- Modify: `frontend/src/index.css` (append after the scrollbar section, lines 117-134)

- [ ] **Step 1: Add the `.chat-prose` class**

Append the following after the `.scrollbar-thin::-webkit-scrollbar-thumb:hover` block:

```css
/* Chat markdown prose styling */
.chat-prose {
  @apply prose prose-invert prose-sm max-w-none text-sm;

  & pre {
    @apply bg-[#0c1018] border border-border rounded-lg p-3;
  }
  & pre code {
    @apply bg-transparent p-0 text-foreground;
  }
  & code {
    @apply text-indigo-300 bg-muted px-1.5 py-0.5 rounded text-xs;
  }
  & a {
    @apply text-indigo-300 no-underline hover:underline;
  }
  & table {
    @apply border-collapse;
  }
  & th,
  & td {
    @apply border border-border px-3 py-1.5;
  }
  & blockquote {
    @apply border-l-indigo-500/50 text-muted-foreground;
  }
  & hr {
    @apply border-border;
  }
}
```

- [ ] **Step 2: Add the `@keyframes pulse-glow` animation**

Append after the `.chat-prose` block:

```css
/* Streaming indicator pulse */
@keyframes pulse-glow {
  0%, 100% {
    opacity: 0.4;
    transform: scale(1);
    box-shadow: 0 0 4px rgba(99,102,241,0.2);
  }
  50% {
    opacity: 1;
    transform: scale(1.3);
    box-shadow: 0 0 8px rgba(99,102,241,0.5);
  }
}
```

- [ ] **Step 3: Update scrollbar colors**

Replace the existing scrollbar thumb colors:

Change in `.scrollbar-thin::-webkit-scrollbar-thumb`:
```css
  background-color: rgba(99,102,241,0.15);
```

Change in `.scrollbar-thin::-webkit-scrollbar-thumb:hover`:
```css
  background-color: rgba(99,102,241,0.3);
```

Also update `scrollbar-color` in `.scrollbar-thin`:
```css
  scrollbar-color: rgba(99,102,241,0.15) transparent;
```

- [ ] **Step 4: Verify CSS compiles without errors**

Check the running dev server for build errors. No visual changes expected yet since `.chat-prose` isn't consumed and `pulse-glow` isn't referenced.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/index.css
git commit -m "style(chat): add chat-prose class, pulse-glow keyframes, update scrollbar"
```

---

### Task 3: Reskin ChatMessages

**Files:**
- Modify: `frontend/src/components/chat/ChatMessages.tsx`

- [ ] **Step 1: Update the `AssistantAvatar` component**

Replace the current `AssistantAvatar` function:

```tsx
function AssistantAvatar() {
  return (
    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500/15 to-violet-500/10 flex items-center justify-center shrink-0 mt-0.5">
      <Bot className="w-4 h-4 text-indigo-300" />
    </div>
  );
}
```

- [ ] **Step 2: Update the `UserAvatar` component**

Replace the current `UserAvatar` function:

```tsx
function UserAvatar() {
  return (
    <div className="w-7 h-7 rounded-full bg-indigo-500/10 border border-indigo-500/15 flex items-center justify-center shrink-0 mt-0.5">
      <User className="w-4 h-4 text-indigo-300" />
    </div>
  );
}
```

- [ ] **Step 3: Update user message bubble**

In the `messages.map` block, replace the user message bubble `div`:

```tsx
<div className="bg-gradient-to-br from-indigo-500/15 to-violet-500/8 border border-indigo-500/20 text-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
```

- [ ] **Step 4: Update user message timestamp**

Replace the user timestamp `span`:

```tsx
<span className="text-xs text-muted-foreground/40 px-1">
```

- [ ] **Step 5: Update assistant message prose class**

Replace both instances of the long inline prose class string (one in the `messages.map` block, one in the streaming content block) with:

```tsx
<div className="chat-prose">
```

- [ ] **Step 6: Update assistant message timestamp**

Replace the assistant timestamp `span`:

```tsx
<span className="text-xs text-muted-foreground/40">
```

- [ ] **Step 7: Update streaming indicator dots**

Replace the three bouncing dot `span` elements:

```tsx
<span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-[pulse-glow_1.4s_ease-in-out_infinite] [animation-delay:0ms]" />
<span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-[pulse-glow_1.4s_ease-in-out_infinite] [animation-delay:150ms]" />
<span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-[pulse-glow_1.4s_ease-in-out_infinite] [animation-delay:300ms]" />
```

- [ ] **Step 8: Update message list spacing**

Change the outer container `div` from `space-y-5` to `space-y-6`:

```tsx
<div className="flex-1 overflow-auto px-4 py-5 space-y-6">
```

- [ ] **Step 9: Verify messages render correctly**

Open the chat, send a message, and confirm:
- User bubbles have the gradient background with indigo border
- Assistant avatar is a rounded square with gradient
- Markdown renders correctly with the `.chat-prose` class
- Streaming dots pulse with the glow animation
- Timestamps are `text-xs` size

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/chat/ChatMessages.tsx
git commit -m "style(chat): reskin ChatMessages with ambient glow palette"
```

---

### Task 4: Reskin ChatInput

**Files:**
- Modify: `frontend/src/components/chat/ChatInput.tsx`

- [ ] **Step 1: Update the textarea**

Replace the `textarea` element's `className`:

```tsx
className="w-full bg-[#0c1018] border border-[rgba(99,102,241,0.12)] rounded-2xl px-4 py-2.5 pr-12 text-sm text-foreground placeholder:text-muted-foreground/50 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40 focus:shadow-[0_0_20px_rgba(99,102,241,0.06)] transition-all min-h-[40px] max-h-[120px]"
```

- [ ] **Step 2: Update the send button**

Replace the send `Button`:

```tsx
<Button size="sm" className="h-7 w-7 p-0 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 border-0" onClick={handleSubmit} disabled={disabled}>
  <SendHorizonal className="w-3.5 h-3.5 text-white" />
</Button>
```

- [ ] **Step 3: Update the stop button**

Replace the stop `Button`:

```tsx
<Button size="sm" variant="outline" className="h-7 w-7 p-0 rounded-xl" onClick={onStop}>
  <Square className="w-3 h-3" />
</Button>
```

- [ ] **Step 4: Update context label**

Replace the context label `span`:

```tsx
<span className="bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
```

- [ ] **Step 5: Update helper text**

Replace the helper `p` tag:

```tsx
<p className="text-xs text-muted-foreground/30 text-center">
```

- [ ] **Step 6: Verify input area**

Confirm: textarea has dark background, glows on focus, send button has gradient, helper text is `text-xs`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/chat/ChatInput.tsx
git commit -m "style(chat): reskin ChatInput with ambient glow palette"
```

---

### Task 5: Reskin ChatSidebar

**Files:**
- Modify: `frontend/src/components/chat/ChatSidebar.tsx`

- [ ] **Step 1: Update sidebar container**

Replace the outer `div`'s `className`:

```tsx
<div className="w-[280px] shrink-0 border-r border-border flex flex-col h-full bg-gradient-to-b from-[#0f1318] to-[#0a0e14]">
```

- [ ] **Step 2: Update "New" button**

Replace the `Button` component:

```tsx
<Button size="sm" className="h-7 text-xs gap-1 bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 text-white border-0" onClick={onCreate}>
  <Plus className="w-3.5 h-3.5" /> New
</Button>
```

- [ ] **Step 3: Update search input**

Replace the search `input`'s `className`:

```tsx
className="w-full bg-muted/50 border border-border rounded-md pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40"
```

- [ ] **Step 4: Update conversation item styles**

Replace the conversation item `div`'s dynamic `className`:

```tsx
className={`group flex items-center gap-2 rounded-lg px-3 py-2.5 cursor-pointer text-sm transition-all ${
  conv.id === activeId
    ? "bg-[rgba(99,102,241,0.08)] border border-[rgba(99,102,241,0.15)] text-indigo-200 shadow-[0_0_12px_rgba(99,102,241,0.05)]"
    : "text-muted-foreground hover:bg-[rgba(99,102,241,0.04)] hover:text-foreground border border-transparent"
}`}
```

- [ ] **Step 5: Update metadata text sizes**

Replace the timestamp `span`:

```tsx
<span className="text-xs opacity-50">
  {timeAgo(conv.updated_at)}
</span>
```

Replace the message count `span`:

```tsx
<span className="text-xs opacity-40">
  {conv.message_count} msg{conv.message_count !== 1 ? "s" : ""}
</span>
```

- [ ] **Step 6: Update empty state icon**

Replace the `MessageCircle` icon's `className`:

```tsx
<MessageCircle className="w-8 h-8 text-indigo-500/30" />
```

- [ ] **Step 7: Verify sidebar**

Confirm: gradient background, active item has indigo glow, "New" button has gradient, search input glows on focus.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/chat/ChatSidebar.tsx
git commit -m "style(chat): reskin ChatSidebar with ambient glow palette"
```

---

### Task 6: Reskin SourceBadges

**Files:**
- Modify: `frontend/src/components/chat/SourceBadges.tsx`

- [ ] **Step 1: Update memory toggle badge**

Replace the memory count `span`:

```tsx
<span className="inline-flex items-center gap-1 bg-indigo-500/8 border border-indigo-500/15 text-indigo-300 px-2 py-0.5 rounded-md">
  <FileText className="w-3 h-3" />
  {memories.length} {memories.length === 1 ? "memory" : "memories"}
</span>
```

- [ ] **Step 2: Update entity toggle badge**

Replace the entity count `span`:

```tsx
<span className="inline-flex items-center gap-1 bg-violet-500/8 border border-violet-500/15 text-violet-300 px-2 py-0.5 rounded-md">
  <Diamond className="w-3 h-3" />
  {entityCount} {entityCount === 1 ? "entity" : "entities"}
</span>
```

- [ ] **Step 3: Update expanded memory cards**

Replace the memory card `div`:

```tsx
<div
  key={m.id ?? i}
  className="bg-[#0c1018] rounded-lg p-2.5 border border-[rgba(99,102,241,0.1)]"
>
```

Replace the source dot `span`:

```tsx
<span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
```

Replace the metadata container classes (the `div` with `flex gap-3 mt-1.5`):

```tsx
<div className="flex gap-3 mt-1.5 text-xs text-muted-foreground/50">
```

- [ ] **Step 4: Update expanded entity cards**

Replace the entity card `div`:

```tsx
<div
  key={e.id ?? i}
  className="flex items-center gap-2.5 bg-[#0c1018] rounded-lg p-2.5 border border-[rgba(99,102,241,0.1)]"
>
```

Replace the diamond shape `span` — change `backgroundColor` from `#fb923c` to the violet color:

```tsx
<span
  className="w-3 h-3 shrink-0"
  style={{ clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)", backgroundColor: "#a78bfa" }}
/>
```

Replace the entity type badge `span`:

```tsx
<span className="capitalize text-xs bg-violet-500/10 text-violet-300 px-1.5 py-0.5 rounded">
  {e.entity_type}
</span>
```

- [ ] **Step 5: Verify source badges**

Open a conversation with existing assistant messages that have sources. Confirm the toggle badges are indigo/violet, expanded cards have the dark background, and entity diamonds are violet.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/chat/SourceBadges.tsx
git commit -m "style(chat): reskin SourceBadges with indigo/violet palette"
```

---

### Task 7: Reskin Chat Page (Empty State, Header, Quick Prompts)

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`

- [ ] **Step 1: Update empty state icon container**

Replace the icon container `div`:

```tsx
<div
  className="w-20 h-20 rounded-2xl flex items-center justify-center"
  style={{ background: "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)" }}
>
  <Sparkles className="w-8 h-8 text-indigo-400" />
</div>
```

- [ ] **Step 2: Update quick prompt buttons**

Replace the `button` element's `className`:

```tsx
className="text-xs bg-[rgba(99,102,241,0.04)] border border-[rgba(99,102,241,0.1)] hover:bg-[rgba(99,102,241,0.1)] hover:border-[rgba(99,102,241,0.2)] hover:text-indigo-200 px-4 py-2 rounded-full text-slate-300 transition-all"
```

- [ ] **Step 3: Update header title edit input**

Replace the title edit `input`'s `className`:

```tsx
className="text-sm font-semibold bg-transparent border-b border-primary focus:outline-none focus:ring-0 focus:border-indigo-400 flex-1"
```

- [ ] **Step 4: Update header message count**

Replace the message count `span`:

```tsx
<span className="text-xs text-muted-foreground/40 shrink-0">
  {messages.length} message{messages.length !== 1 ? "s" : ""}
</span>
```

- [ ] **Step 5: Verify empty state and header**

Confirm: icon has radial glow, quick prompt buttons are styled, header message count uses `text-xs`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Chat.tsx
git commit -m "style(chat): reskin empty state, header, and quick prompts"
```

---

### Task 8: Reskin ChatOverlay

**Files:**
- Modify: `frontend/src/components/chat/ChatOverlay.tsx`

- [ ] **Step 1: Update the floating action button**

Replace the closed-state `button`'s `className`:

```tsx
className="fixed bottom-4 right-4 z-40 w-10 h-10 bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full flex items-center justify-center text-white shadow-lg hover:from-indigo-400 hover:to-violet-400 transition-all"
```

- [ ] **Step 2: Update the overlay container**

Replace the open-state outer `div`'s `className`:

```tsx
className="fixed bottom-16 right-4 z-40 w-[320px] h-[400px] bg-card border border-[rgba(99,102,241,0.15)] rounded-xl shadow-[0_0_30px_rgba(99,102,241,0.08)] flex flex-col overflow-hidden"
```

- [ ] **Step 3: Verify overlay**

Navigate to the graph page. Confirm: floating button has gradient, overlay panel has indigo border glow. Chat inside overlay inherits the reskinned ChatMessages and ChatInput.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/ChatOverlay.tsx
git commit -m "style(chat): reskin ChatOverlay with ambient glow palette"
```

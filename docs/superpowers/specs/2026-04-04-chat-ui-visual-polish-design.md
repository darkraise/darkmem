# Chat UI Visual Polish — Ambient Glow Design

**Date:** 2026-04-04
**Approach:** Component Reskin + Micro-Animations (Approach 2)
**Direction:** Ambient Glow — deep dark base with indigo/violet luminance on interactive elements
**Intensity:** Restrained — glow effects on key interactive moments only; base UI stays clean

## Scope

Visual-only changes. No functionality changes, no new dependencies, no API changes, no hook changes. All work is in CSS and component markup (Tailwind classes).

**Files modified:**
- `frontend/src/index.css` — theme tokens, new utility class, keyframes, scrollbar
- `frontend/src/pages/Chat.tsx` — empty state, header, quick prompts
- `frontend/src/components/chat/ChatMessages.tsx` — bubbles, avatars, streaming indicator, prose class
- `frontend/src/components/chat/ChatInput.tsx` — textarea glow, button gradient, helper text
- `frontend/src/components/chat/ChatSidebar.tsx` — gradient background, active glow, button style
- `frontend/src/components/chat/SourceBadges.tsx` — indigo/violet badge colors, expanded card style
- `frontend/src/components/chat/ChatOverlay.tsx` — same palette applied to overlay variant

**No new files created.**

## 1. Color Palette & Theme Tokens

Replace values in the `.dark` block of `index.css`:

| Token | Current | New | Rationale |
|---|---|---|---|
| `--background` | `#0d1117` | `#0a0e14` | Deeper base for more contrast with cards |
| `--foreground` | `#c9d1d9` | `#e2e8f0` | Brighter text (Slate-200) |
| `--card` | `#161b22` | `#0f1318` | Darker cards create depth |
| `--card-foreground` | `#c9d1d9` | `#e2e8f0` | Match foreground |
| `--popover` | `#161b22` | `#0f1318` | Match card |
| `--popover-foreground` | `#c9d1d9` | `#e2e8f0` | Match foreground |
| `--primary` | `#58a6ff` | `#818cf8` | Indigo-400 |
| `--primary-foreground` | `#0d1117` | `#0a0e14` | Match background |
| `--secondary` | `#21262d` | `#1e1b4b` | Indigo-950 |
| `--secondary-foreground` | `#c9d1d9` | `#e2e8f0` | Match foreground |
| `--muted` | `#161b22` | `#12161d` | Subtle dark fill |
| `--muted-foreground` | `#8b949e` | `#64748b` | Slate-500 |
| `--accent` | `#1f2937` | `#1e1b4b` | Indigo-950 |
| `--accent-foreground` | `#c9d1d9` | `#e2e8f0` | Match foreground |
| `--destructive` | `#f85149` | `#f87171` | Red-400, softer |
| `--border` | `#21262d` | `rgba(99,102,241,0.12)` | Indigo-tinted borders |
| `--input` | `#21262d` | `rgba(99,102,241,0.12)` | Match border |
| `--ring` | `#58a6ff` | `#6366f1` | Indigo-500 |

Chart colors:
| Token | New |
|---|---|
| `--chart-1` | `#818cf8` (indigo-400) |
| `--chart-2` | `#34d399` (emerald-400) |
| `--chart-3` | `#c4b5fd` (violet-300) |
| `--chart-4` | `#fbbf24` (amber-400) |
| `--chart-5` | `#f472b6` (pink-400) |

Sidebar tokens:
| Token | New |
|---|---|
| `--sidebar` | `#0f1318` |
| `--sidebar-foreground` | `#e2e8f0` |
| `--sidebar-primary` | `#818cf8` |
| `--sidebar-primary-foreground` | `#e2e8f0` |
| `--sidebar-accent` | `#1e1b4b` |
| `--sidebar-accent-foreground` | `#e2e8f0` |
| `--sidebar-border` | `rgba(99,102,241,0.12)` |
| `--sidebar-ring` | `#6366f1` |

Custom properties added to `.dark`:

```css
--glow-primary: rgba(99,102,241,0.15);
--glow-primary-subtle: rgba(99,102,241,0.06);
```

## 2. CSS Additions in index.css

### `.chat-prose` class

Extracted from the inline markdown override string currently repeated in ChatMessages. Contains all the prose styling rules for assistant messages:

- `prose prose-invert prose-sm max-w-none text-sm`
- Code blocks: `bg-[#0c1018]` with indigo-tinted border, `rounded-lg`, `p-3`
- Inline code: `text-indigo-300 bg-muted px-1.5 py-0.5 rounded text-xs`
- Pre>code: transparent background, foreground text
- Links: `text-indigo-300` no underline, underline on hover
- Tables: border-collapse with border-colored cells
- Blockquote: left border `border-l-indigo-500/50`, text `text-muted-foreground`
- hr: `border-border`

### `@keyframes pulse-glow`

For streaming indicator dots:

```css
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

Applied with staggered `animation-delay` (0ms, 150ms, 300ms) on each dot.

### Scrollbar update

Thumb: `rgba(99,102,241,0.15)`, hover: `rgba(99,102,241,0.3)`.

## 3. Chat Messages (`ChatMessages.tsx`)

### User messages
- Bubble: `bg-gradient-to-br from-indigo-500/15 to-violet-500/8`
- Border: `border border-indigo-500/20`
- Shape: `rounded-2xl rounded-tr-sm` (unchanged)
- Max width: `max-w-[75%]` (unchanged)

### User avatar
- `bg-indigo-500/10 border border-indigo-500/15` instead of plain `bg-muted`
- Icon: `text-indigo-300` instead of `text-muted-foreground`

### Assistant avatar
- Shape changes from circle (`rounded-full`) to rounded square (`rounded-lg`)
- Fill: `bg-gradient-to-br from-indigo-500/15 to-violet-500/10`
- Icon: `text-indigo-300`

### Assistant message body
- Replace the long inline class string with the `.chat-prose` class

### Streaming indicator
- Dots: `bg-indigo-400` with `animate-[pulse-glow_1.4s_ease-in-out_infinite]`
- Staggered delays: `[animation-delay:0ms]`, `[animation-delay:150ms]`, `[animation-delay:300ms]`

### Timestamps
- `text-xs text-muted-foreground/40` (was `text-[10px] text-muted-foreground/50`)

### Spacing
- Message gap: `space-y-6` (was `space-y-5`)

## 4. Chat Input (`ChatInput.tsx`)

### Textarea
- Background: `bg-[#0c1018]`
- Border at rest: `border-[rgba(99,102,241,0.12)]`
- Focus: `focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40 focus:shadow-[0_0_20px_rgba(99,102,241,0.06)]`
- Border radius: `rounded-2xl` (was `rounded-xl`)
- Placeholder: `placeholder:text-muted-foreground/50`

### Send button
- Gradient fill: `bg-gradient-to-r from-indigo-500 to-violet-500`
- Hover: `hover:from-indigo-400 hover:to-violet-400`
- Border radius: `rounded-xl` (was `rounded-lg`)

### Stop button
- `variant="outline"` stays, border inherits indigo-tinted border
- Border radius: `rounded-xl`

### Context label
- `bg-indigo-500/10 text-indigo-300 border border-indigo-500/20`

### Helper text
- `text-xs text-muted-foreground/30` (was `text-[10px] text-muted-foreground/40`)

## 5. Chat Sidebar (`ChatSidebar.tsx`)

### Container
- Background: `bg-gradient-to-b from-[#0f1318] to-[#0a0e14]` (was `bg-card/50`)
- Right border inherits indigo-tinted `border-border`

### "New" button
- Switches from `variant="ghost"` to gradient fill: `bg-gradient-to-r from-indigo-500 to-violet-500 text-white`
- Small pill shape, keeps `h-7 text-xs gap-1`

### Search input
- Same focus-glow treatment as chat textarea
- `focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40`

### Conversation items — active state
- `bg-[rgba(99,102,241,0.08)] border border-[rgba(99,102,241,0.15)] text-indigo-200`
- Glow: `shadow-[0_0_12px_rgba(99,102,241,0.05)]`

### Conversation items — hover state
- `hover:bg-[rgba(99,102,241,0.04)]`

### Conversation items — inactive
- `text-muted-foreground` (unchanged)

### Metadata
- Timestamps and message counts: `text-xs` (was `text-[10px]`)

### Empty state (no conversations)
- Icon: `text-indigo-500/30` (was `opacity-20`)

## 6. Source Badges (`SourceBadges.tsx`)

### Toggle button badges
- Memory: `bg-indigo-500/8 border border-indigo-500/15 text-indigo-300`
- Entity: `bg-violet-500/8 border border-violet-500/15 text-violet-300`
- Chevron: inherits text color

### Expanded memory cards
- Background: `bg-[#0c1018]`
- Border: `border border-[rgba(99,102,241,0.1)]`
- Source dot: `bg-indigo-400` (was `bg-primary/40`)
- Score/tags: `text-xs text-muted-foreground/50`

### Expanded entity cards
- Same card background and border
- Diamond shape: `bg-violet-400` (was `bg-[#fb923c]`)
- Type badge: `bg-violet-500/10 text-violet-300`

## 7. Empty State in Chat.tsx

### Icon container
- Replace `bg-primary/10` box with larger radial glow:
  `w-20 h-20 rounded-2xl flex items-center justify-center`
  Background: `radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)`
- Icon: `text-indigo-400` (was `text-primary/60`), size stays `w-8 h-8`

### Quick prompt buttons
- Rest: `bg-[rgba(99,102,241,0.04)] border border-[rgba(99,102,241,0.1)] text-slate-300`
- Hover: `hover:bg-[rgba(99,102,241,0.1)] hover:border-[rgba(99,102,241,0.2)] hover:text-indigo-200`
- Shape: `rounded-full` (unchanged)

## 8. Chat Header in Chat.tsx

- Title: `text-sm font-semibold` (unchanged), color inherits `--foreground`
- Title edit input: same focus-glow as chat textarea
- Message count: `text-xs text-muted-foreground/40` (was `text-[10px] text-muted-foreground/50`)
- Bottom border inherits indigo-tinted `border-border`

## 9. ChatOverlay (`ChatOverlay.tsx`)

Apply the same palette changes — borders, backgrounds, button styles. The overlay is a smaller viewport of the same components, so it inherits the changes naturally. The overlay container border shifts to `border-[rgba(99,102,241,0.15)]` with `shadow-[0_0_30px_rgba(99,102,241,0.08)]` for a soft glow around the floating widget.

## Design Constraints

- **No arbitrary text sizes.** All small text uses `text-xs` (12px). No `text-[10px]` or similar.
- **No new dependencies.** Everything is Tailwind classes + a few CSS additions.
- **No structural changes** to component APIs, props, hooks, or data flow.
- **No new files** except this spec document.
- **Glow effects are restrained** — only on: active sidebar item, focused input, streaming dots, overlay container. Base UI stays clean.

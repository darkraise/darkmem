# Login / Guest Auth Revamp — Design Spec

Date: 2026-06-02
Status: Approved direction; revised after codebase-grounded self-review.
Visual source of truth: prototype at
`.superpowers/brainstorm/24880-1780407969/content/login-interactive-v4.html`.

## Goal

Replace the plain centered login (`PageHeader` + `LoginForm` on a flat
background) with a branded, atmospheric signed-out experience: a frosted
glass auth card floating over a smooth aurora mesh gradient with an
interactive, mouse-reactive knowledge-graph particle network behind it. The
first-run setup wizard shares the same backdrop.

## Scope

- **In scope:** the whole guest (signed-out) shell — `/login` and the
  first-run `/setup` wizard both live under `routes/_guest.tsx`. Visual only.
- **Non-goals:**
  - No change to sign-in behavior. Auth stays **password-only**; `useLogin`,
    `loginSchema`, and form submission are untouched. Preserve `login.tsx`'s
    `useRouter` + `onSuccess` navigation when restructuring.
  - No backend changes, no new auth fields (no username / remember-me).
  - No new runtime dependency — the particle field stays hand-written canvas.
  - No theme/mode switcher on the login.
  - Keep the darkraise-ui `PasswordInput` composition; restyle via
    `className`/CSS only — do not hand-roll a replacement input.

## Existing code (this is a refactor, not a greenfield build)

A `ParticleBackground` component **already exists** and is live. The revamp
**moves and extends it**; it does not create a second one.

- `frontend/src/features/setup/components/ParticleBackground.tsx` (PascalCase,
  ~218 lines) exports `ParticleBackground`. Current props/defaults:
  `density=0.00012`, `linkDistance=140`, `speed=0.8`, `mouseLinkDistance=220`.
  Current behavior diverges from the approved look: grey-blue palette
  (`rgba(120,160,220)` links, `rgba(180,200,240)` nodes), **no** cursor
  repulsion, **no** cyan accent nodes, **no** aurora mesh (just an inline
  `radial-gradient` background + an in-canvas vignette redrawn every frame),
  particles **wrap** at edges, `dpr` is **uncapped**, reduced-motion only
  freezes positions but **keeps the rAF loop running**, there is **no**
  `visibilitychange` pause, and it uses `window` `resize`. It does already
  listen to `mousemove`/`mouseout` **and** `touchmove`/`touchend`.
- `frontend/src/features/setup/components/SetupWizard.tsx:122-125` renders
  `<ParticleBackground />` **and** its own glass surface:
  `<Card className="border-border/60 bg-card/85 flex max-h-[90vh] w-full
  max-w-2xl flex-col shadow-2xl backdrop-blur-md">` with a `CardContent`
  (`overflow-hidden p-8`), an inner `flex-1 overflow-y-auto` scroll region,
  and a sticky footer button row. So the wizard does **not** inherit a
  backdrop from the shell today — it renders its own.
- `frontend/src/styles/globals.css:34` already defines `@keyframes pulse-glow`
  (opacity `0.4→1`, `scale(1)→scale(1.3)`) used by the chat typing indicator.
  **Do not reuse or redefine it** for the button; add a distinct keyframe.
- `frontend/src/main.tsx` wraps the app in `<StrictMode>` (effects mount →
  cleanup → mount again in dev; lifecycle must be idempotent).
- `frontend/vitest.config.ts` uses `environment: "jsdom"` with **no**
  `setupFiles`. jsdom provides neither `HTMLCanvasElement.prototype.getContext`
  (returns `null`) nor `window.matchMedia` (`undefined`). Any test that renders
  `ParticleBackground` (directly or via `_guest`/login) throws today unless
  both are stubbed.

## Approved visual values (from the v4 prototype)

**Base wash (continuous):**
`linear-gradient(160deg, #070a11 0%, #05070d 55%, #03050a 100%)`

**Aurora mesh** — five large Gaussian-blurred, slowly drifting color fields
(true blur over analogous hues = seamless, no banding):

| Blob | Color | Opacity | Blur | Approx position / size |
| --- | --- | --- | --- | --- |
| indigo | `#6366f1` | 0.18 | 115px | top-left, 62vw |
| violet | `#7c3aed` | 0.16 | 120px | bottom-right, 58vw |
| blue | `#2563eb` | 0.13 | 125px | center, 46vw |
| cyan (accent) | `#22d3ee` | 0.09 | 115px | upper-right, 30vw |
| deep indigo | `#4338ca` | 0.15 | 125px | lower-left, 48vw |

Drift keyframes (verbatim from prototype): `floatA` 24s + `floatB` 28s +
`floatC` 32s, plus `floatB` 26s / `floatA` 30s reuse, `ease-in-out infinite
alternate`, `will-change: transform` on the blobs only.

**Vignette veil** (prefer a CSS layer over redrawing in canvas each frame):
`radial-gradient(circle at 50% 42%, rgba(5,7,12,.22) 0%, rgba(3,4,9,.72) 100%)`

**Particle network (canvas):**
- Count: `clamp(round(width*height*0.00012), 70, 170)`.
- Speed ~1.0 px/frame; **bounce off edges** (reflect velocity) — matches the
  approved prototype (note: the existing file wraps; change to bounce).
- Node radius 1.3–2.8px; accent nodes larger with a soft glow (`shadowBlur`).
- Node colors indigo `["#818cf8","#6366f1","#a5b4fc"]`; ~18% cyan accents
  `["#22d3ee","#67e8f9"]`.
- Node links within **128px**: `rgba(129,140,248,(1-d/128)*0.5)`.
- Cursor link within **180px**: `rgba(103,232,249,(1-d/180)*0.75)`.
- Cursor repulsion within **110px** (strength factor ~2.2).
- DPR capped at 2.

**Glass card (unified for login and wizard):** translucent dark surface
(~`rgba(255,255,255,.05)`), `1px` `rgba(255,255,255,.11)` border, `18px`
radius, `backdrop-filter: blur(16px)`, shadow `0 24px 70px rgba(0,0,0,.62)`
plus a faint indigo ring/glow. This intentionally **changes the wizard's
current surface** (`bg-card/85 backdrop-blur-md shadow-2xl`) so both guest
screens match — that is the desired consistency, not a regression.

**Brand block (paste exact values from the prototype):**
- Node-graph glyph: the prototype's 24×24 SVG (4 lines stroke `#67e8f9`
  width 1.6; 4 circles fill `#818cf8` r 2.4).
- Wordmark "darkmem": gradient text fill via `bg-clip-text`
  `linear-gradient(90deg, #c7d2fe, #a5b4fc 55%, #67e8f9)`, weight 800,
  tracking ~`.3px`, sized with a Tailwind heading token (see typography rule).
- Tagline: "Sign in to continue" (no trailing period; current copy has one).
- Submit button: gradient `#818cf8 → #6366f1 → #38bdf8`, dark text, gentle
  glow via a new `btn-pulse-glow` keyframe (box-shadow only).

**Typography & class conventions (load-bearing):** the prototype's inline
**px font-sizes are NOT authoritative for type**. All text uses Tailwind text
tokens (`text-base` default, `text-sm` sparingly; **never** `text-xs` or
arbitrary `text-[Npx]`). Non-typographic px (radius, blur, widths) may stay as
Tailwind arbitrary values; prefer `max-w-sm` (384px) for the ~380px card. The
gradient wordmark uses `bg-clip-text` utilities, not inline styles.

## Architecture

### `ParticleBackground` — moved + extended (canonical backdrop)

Move `features/setup/components/ParticleBackground.tsx` →
`frontend/src/components/particle-background.tsx` (kebab-case per convention),
then extend it into the full drop-in backdrop: it renders a fixed,
behind-content root containing the **mesh gradient layer** and the **particle
canvas**, so one tag yields the whole atmosphere and it is reusable elsewhere.

Canonical prop surface (supersedes the old `{density, linkDistance, speed,
mouseLinkDistance}`):

```ts
interface ParticleBackgroundProps {
  className?: string
  gradient?: boolean      // render the built-in aurora mesh. default true
  interactive?: boolean   // cursor links + repulsion. default true
  density?: number        // particles per px². default 0.00012
  speed?: number          // px/frame. default 1.0
  colors?: {
    nodes?: string[]; accents?: string[]; accentRatio?: number // 0.18
    link?: string; mouseLink?: string
  }
}
```

**Deltas to implement on top of the existing file (MUST, not assumed-done):**
1. Indigo/cyan palette + ~18% accent nodes with `shadowBlur` glow (replace the
   grey-blue constants).
2. Cursor **repulsion** within 110px (new; existing has none).
3. **Bounce** off edges (existing wraps).
4. `dpr = Math.min(2, window.devicePixelRatio || 1)` (existing is uncapped).
5. `document.addEventListener("visibilitychange", …)` → cancel rAF when
   `document.hidden`, restart when visible; remove in cleanup (new).
6. **Reduced-motion = truly static**: draw exactly one frame, then `return`
   without scheduling rAF; do **not** attach mouse/touch listeners; no cursor
   links/repulsion. (Existing keeps the loop running — change it.)
7. Move the vignette out of the per-frame canvas draw into the CSS veil layer.
8. New mesh layer (below) gated by `gradient`.
9. StrictMode idempotency: cleanup cancels rAF, removes **every** listener, and
   resets `particlesRef.current = []` so a re-mount starts clean.
10. Keep `window` `resize` (the canvas is viewport-fixed, so `ResizeObserver`
    adds cost for no gain); debounce/throttle since resize re-seeds count.
11. Keep `touchmove`/`touchend` so touch devices get the interaction (skipped
    under reduced-motion).
12. Defensive `typeof window`/`matchMedia` guards are **required**, not
    optional — jsdom is a real non-browser environment for tests.

**Mesh layer** (un-exported `MeshGradient` helper inside the same file): the
base wash + five blurred blob `<div>`s + the veil, all `pointer-events-none`.
Drift via the `floatA/B/C` keyframes in `globals.css`; disabled under the
reduced-motion media query. `will-change: transform` on blobs only.

**Stacking / positioning (pinned):** the component root is
`fixed inset-0 -z-10 overflow-hidden pointer-events-none`; mesh blobs sit
behind the canvas within it. `_guest.tsx` content sits naturally above the
`-z-10` backdrop (give the centered content `relative z-10` if needed). The
base-wash gradient lives on the mesh layer (the prototype put it on `body`;
the app cannot). Confirm the card wrapper does **not** set
`pointer-events:none`.

### `GlassPanel` — thin wrapper over darkraise-ui `Card`

`frontend/src/components/glass-panel.tsx` (new). Wraps darkraise-ui `Card`
(the idiomatic frosted surface the wizard already uses) and applies the
**unified glass className baseline** (background, white border, `backdrop-blur`,
shadow, indigo ring, `18px` radius). **Styling-only**: it sets no
width/height/flex/overflow/padding — those come from the caller's `className`
so the wizard keeps `flex max-h-[90vh] w-full max-w-2xl flex-col
overflow-hidden` and the login card uses `w-full max-w-sm`. Forwards
`className` + children + rest props to `Card`.

### Keyframes & CSS (`frontend/src/styles/globals.css`)

Tailwind v4 here has no `@theme` keyframe registry; the pattern is raw
`@keyframes` in `globals.css` consumed via `animate-[…]` arbitrary values
(as `chat-messages.tsx` does with the existing `pulse-glow`). Add:
- `floatA` / `floatB` / `floatC` drift keyframes (verbatim from the prototype).
- `btn-pulse-glow` — **box-shadow only** (do not touch the existing
  `pulse-glow`, which scales/fades for the chat dots).
- `@media (prefers-reduced-motion: reduce)` block setting `animation: none` on
  the mesh blobs and the submit button.

## Integration points

1. **`routes/_guest.tsx`** — keep the auth/setup redirect `beforeLoad`
   unchanged. Render `<ParticleBackground />` plus the centered `<Outlet />`
   (content above the `-z-10` backdrop). Note: `autoCodeSplitting` splits at
   route boundaries, so `ParticleBackground` lands in the `_guest` chunk and
   only mounts after `beforeLoad` resolves (it won't animate during a redirect).

2. **`routes/_guest/login.tsx`** — render `<GlassPanel className="w-full
   max-w-sm">` containing the brand block (glyph + gradient wordmark + tagline)
   and the existing `<LoginForm onSuccess=… />`. Drop the `PageHeader` import.
   **Retain** the `useRouter`/`onSuccess` navigation wiring.

3. **`features/auth/components/login-form.tsx`** — restyle the submit `Button`
   (gradient + `btn-pulse-glow`) via `className`; restyle the password field to
   read on glass (apply `bg-black/35`, `border-white/15`, `h-[42px]`,
   `rounded-[10px]` to `PasswordInputControl`; keep `PasswordInputField`
   transparent; style the visibility-trigger/eye for dark glass). **No
   behavioral change.** Spell out **auth states on glass**: the disabled/pending
   button must keep AA contrast (raise text weight or switch to a light text
   token when disabled); the `login.isError` `text-destructive` message must
   stay legible on the translucent card (verify, or use a translucent
   destructive chip); check `FieldWrapper` label/error contrast. Add
   `focus-visible` rings that show on glass (e.g.
   `focus-visible:ring-2 ring-cyan-300/70 ring-offset-2
   ring-offset-transparent`) on the field box and button; confirm tab order
   (field → eye toggle → submit); autofocus the password field on mount.
   darkraise-ui's `PasswordInput` ships its own CSS — if a plain `className`
   loses specificity, scope a local class rather than swapping the component.

4. **`features/setup/components/SetupWizard.tsx`** — **remove** the
   `import { ParticleBackground } from "./ParticleBackground"` and its
   `<ParticleBackground />` render (the backdrop now comes from `_guest.tsx`;
   otherwise `/setup` paints two canvases). Replace the wizard's `<Card …>`
   with `<GlassPanel className="flex max-h-[90vh] w-full max-w-2xl flex-col
   overflow-hidden">`, keeping its `CardContent` (`p-8`), the inner
   `flex-1 overflow-y-auto` scroll region, and the sticky footer intact. The
   wizard's surface adopts the unified glass look (intended).

5. **Delete** `features/setup/components/ParticleBackground.tsx` after the move
   (its only importer is SetupWizard, which no longer needs it).

## Accessibility

- `prefers-reduced-motion`: pinned behavior above (one static canvas frame, no
  rAF, no cursor interaction; mesh drift + button pulse disabled via CSS).
- Canvas is decorative: `aria-hidden`, `pointer-events:none`.
- Visible `focus-visible` rings on the field and gradient button, contrast-safe
  on glass; preserved tab order; autofocus the password field.
- Text/contrast on glass meets WCAG AA, including the **disabled button** and
  **error** states.

## Performance

- The dominant cost is GPU compositing of `backdrop-filter` over an animating
  canvas plus five large-radius blurred blobs — **not** the O(n²) link pass
  (~14k cheap checks at ≤170 nodes is fine). Mitigations: `will-change:
  transform` on blobs only; render the vignette in CSS (not per-frame canvas);
  DPR capped at 2; pause rAF on `visibilitychange`.
- `@supports not (backdrop-filter: blur(1px))` fallback: give the card a more
  opaque solid background so it stays legible where backdrop-filter is
  unsupported/disabled.
- Responsive: card `w-full max-w-sm` with `px-4` page padding so it never
  touches edges; the density clamp bounds particle count on large screens;
  keep touch interaction.

## Testing

Project uses Vitest + RTL (jsdom); gate is `tsc -b`, `vite build`, `vitest`.

- **New shared setup file** (e.g. `src/test/setup.ts`, registered via
  `vitest.config.ts` `test.setupFiles`): stub `window.matchMedia` and
  `HTMLCanvasElement.prototype.getContext` to return a **fake 2D context**
  (not `null`, so the rAF/listener logic actually runs). Without this, any test
  rendering the backdrop throws.
- `particle-background` tests: (a) under reduced-motion, `requestAnimationFrame`
  is called ≤1 time (static frame, no loop); (b) `visibilitychange` to hidden
  calls `cancelAnimationFrame`; (c) unmount removes every listener (spy on
  `removeEventListener`).
- `_guest` renders **exactly one** `<canvas>` on `/setup` (guards the
  double-backdrop regression).
- login render test: wrap in `QueryClientProvider` + a router stub, mock
  `useLogin`/`@/lib/api` and `darkraise-ui/components/sonner` (mirror
  `job-config-form.test.tsx`); assert the wordmark, password field, and submit
  render and submit stays wired.
- The reduced-motion CSS drift-disable is not unit-testable; cover by manual
  check. Manual checks also: `/setup` scroll region still scrolls and the
  Back/Next/Finish row stays pinned; one canvas on both routes.

## File summary

| File | Change |
| --- | --- |
| `src/features/setup/components/ParticleBackground.tsx` | **move → delete** (relocated/rewritten) |
| `src/components/particle-background.tsx` | **new** (moved + extended: mesh, palette, repulsion, DPR cap, visibilitychange, true static reduced-motion, props) |
| `src/components/glass-panel.tsx` | **new** — thin wrapper over darkraise-ui `Card` |
| `src/routes/_guest.tsx` | render `ParticleBackground` + centered outlet |
| `src/routes/_guest/login.tsx` | `GlassPanel` + brand block + `LoginForm`; drop `PageHeader`; keep router wiring |
| `src/features/auth/components/login-form.tsx` | restyle button/field, auth states, focus rings (no behavior change) |
| `src/features/setup/components/SetupWizard.tsx` | remove own `ParticleBackground`; `Card` → `GlassPanel` |
| `src/styles/globals.css` | add `floatA/B/C` + `btn-pulse-glow` keyframes + reduced-motion block |
| `src/test/setup.ts` + `vitest.config.ts` | new shared test setup (matchMedia + canvas stubs) |
| tests | `particle-background`, one-canvas `_guest`, login render |

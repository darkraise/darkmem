## Verdict
verdict: ship 083b5aed6b3e2aed
scores: coverage 18 / fidelity 17 / states 17 / deviations 17

## What I opened

The revised proof report (fingerprint 083b5aed6b3e2aed), including its UI-2, OP-1 and OP-4 rows, and these files:

- `ux-8-focus-1920x1080-light.png` and `ux-8-focus-1280x800-dark.png`, both retaken.
- `board-code--mixed-1920x1080-light.png`, retaken.
- `ux-7-click-select-1920x1080-light.png`, retaken through the new overlay.
- The canvas focus markup in `code-glow-canvas.tsx`. The class string now holds `after:pointer-events-none after:absolute after:inset-0 after:z-10 … focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-ring`.

Everything I verified at fingerprint ab5f5b02f64452b4 still stands:
- Faint rest edges and working edge dimming (UI-3, UX-6).
- The satellite floor (UI-2).
- The full sets at both viewports and in both themes (OP-2).
- `?file=`, the zoom buttons and camera timing (UX-7).
- Settling frames (UX-2) and toolbar rows (UI-4).

## Previous findings, re-checked

1. **Focus ring clipped to one edge (OP-4, UX-8): resolved.**
   - Both focus captures show a 2 px green ring on all four sides of the canvas, inside the 8 px margin, in light at 1920 and in dark at 1280.
   - The ring is an inset `::after` overlay at z-10 with pointer events off, so neither the parent nor sigma's layers can clip or cover it.
   - `ux-7-click-select-1920x1080-light.png` shows a click through the overlay still selects `memory_search`: the panel shows it and the hover reads the full "memory_search · function · api/mcp/mcp_tools.py".
2. **Stray selection on the 1920 light mixed board: resolved.** The retaken board shows the rest state, with no ring or emphasised edges, and faint tinted edges.
3. **Bright halo at 20,000 nodes: disclosed.** The UI-2 row now says the undimmed halo forms a bright ring that reads brighter than the core at the worst case, and ties it to register row 3. I accept the disclosure. The halo constants were deferred by the spec's Riskiest assumption, before this proof.
4. **UI-2 citation: holds.** It now rests on perceivability, with no WCAG 1.4.1 claim. Community colour is the only cluster cue, and additive clipping erased it. The row states plainly that no owner ruling exists.

## Remaining notes (not disputed)

- **UI-2 owner ruling (Minor):** the deviation is cited on an accessibility need, as the criteria allow, but the owner has not ruled. Until they do, the contract's "core 1.0, satellite 0.8" stays unamended in the spec.
- **Ring after a mouse click (Minor, observation):** the focus ring also shows in `ux-7-click-select` after a click. That is harmless to the contract, which asks only for a visible ring on focus. Unknown whether a keypress earlier in that walk triggered focus-visible; a click-only run would settle it.
- **Storybook "Not Found" line (disclosed):** every story still shows it. It is absent from the demo-host captures.

## Scores

- **Every Item Has Evidence: 18.** Every contract item has openable evidence showing that item and state. The memory page's unchanged loading and empty branches rest on a diff argument rather than a capture.
- **Built Matches Promised: 17.** Canvas, nodes, edges, chrome, toolbar and hosts match the contract in both themes. The only departure is the declared density deviation, and at 20,000 nodes the halo still outshines the core.
- **Every State Is Shown: 17.** The data-state matrices, control states (hover, selection, focus, dimming, reduced motion) and the keyboard walk are evidenced at all four viewport and theme pairs. The memory empty and loading states are not captured.
- **Deviations Are Cited: 17.** UI-2 is declared with a valid accessibility need, and the halo brightness and the harness line are disclosed. The owner ruling on UI-2 is still owed.

## Disputed items

None.

Verdict: ship 083b5aed6b3e2aed

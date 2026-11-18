# Constellation graphs — item register

**Source:** owner request 2026-11-18 ("I want to change the memory graph layout and render, also code layout", with graph.jpg as the reference)
**Covers:** docs/dforge/specs/2026-11-18-constellation-graphs-design.md

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | change the memory graph layout and render | docs/dforge/plans/2026-11-18-constellation-graphs.md | A1-A13, A15-A17, A21-A24 | done | plan complete 2026-11-18: final review clean, UI proof ship 51698444ee69244a (0e27bc8a), acceptance 30/30 green at HEAD |
| 2 | also code layout | docs/dforge/plans/2026-11-18-constellation-graphs.md | A1-A9, A11, A14, A18-A20 | done | plan complete 2026-11-18: final review clean, UI proof ship 51698444ee69244a (0e27bc8a), acceptance 30/30 green at HEAD |
| 3 | measure the core/satellite/halo split on the 192.168.0.199 corpus and tune CORE_MIN, CORE_K and HALO_C | docs/dforge/specs/2026-11-18-constellation-real-data-design.md | - | doing | delivered by the real-data spec: cut, placement and halo constants measured on the cloned corpus |
| 4 | owner ruling on UI-2's density deviation: in the dark theme, a role whose discs overlap past what the additive pass can sum is dimmed and, below a floor, drawn smaller | docs/dforge/specs/2026-11-18-constellation-real-data-design.md | - | doing | settled by the real-data spec's UI-2, which states per-role density dimming |
| 5 | final review residual: no test asserts the memory renderer's one-frame deferred runner.start() (graph-2d-renderer.tsx); the acceptance harness's fake requestAnimationFrame could assert no new FA2 worker before the next frame | - | - | deferred | final review residual (ruling fr-2): plan ruling A8 accepted the coverage loss; A23 measures the deferral's effect |
| 6 | final review residual: a code-canvas rebuild that changes the drawn node set (hidden kind, real-host search keystroke) opens at sigma's default camera and does not re-centre a persisting selection (code-glow-canvas.tsx) | - | - | deferred | final review residual (ruling fr-4): a changed node set moves sigma's framing; re-centre on a persisting selection, else fit |
| 7 | final review residual: the code canvas's ring overlay (selection, blast, process), its follow-camera during the core run, and memory-renderer position reseeding across a rebuild have no unit test; the community-dim test asserts only that the colour changed | - | - | deferred | final review residual (ruling fr-5): proven by demo statements A14, A19 and A15 in the UI proof |

#!/usr/bin/env python3
"""Assemble the darkmem UI mockups into one self-contained, Artifact-ready
index.html body. No external deps, no network — inlines the shared CSS and
every fragment. Emits body-content only (style + nav + main, no doctype/
head/body) so it publishes cleanly through the Artifact tool's own skeleton
and still renders offline in any browser.
"""
from pathlib import Path
import re, sys

ROOT = Path(__file__).parent
FRAG = ROOT / "fragments"
ASSETS = ROOT / "assets"

# Deterministic order: G0, then C0*, then S## ascending. Read the numeric
# suffix right after the leading letters — never strip every digit in the
# slug (which would mis-sort e.g. "S18-5-phase-stepper").
def order_key(p: Path):
    name = p.stem
    bucket = {"G": 0, "C": 1, "S": 2}.get(name[0], 9)
    m = re.match(r"[A-Za-z]+(\d+)", name)
    return (bucket, int(m.group(1)) if m else 0)

def main():
    css = "\n".join((ASSETS / f).read_text(encoding="utf-8") for f in ("theme.css", "mockup.css"))
    frags = sorted(FRAG.glob("*.html"), key=order_key)
    if not frags:
        sys.exit("no fragments found")
    bodies, nav = [], []
    for f in frags:
        anchor = f.stem
        nav.append(f'<a href="#{anchor}">{anchor}</a>')
        bodies.append(f'<article id="{anchor}" class="fragment">\n{f.read_text(encoding="utf-8")}\n</article>')
    # Reject any external reference before emitting (allow only the SVG
    # namespace under either scheme; data: URIs have no host and pass).
    joined = css + "".join(bodies)
    bad = [m for m in re.findall(r'https?://[^\s"\')]+', joined) if "www.w3.org" not in m]
    if bad:
        sys.exit(f"external references present, not self-contained: {bad[:5]}")
    out = (
        f"<style>{css}</style>\n"
        f'<nav class="board-index">{"".join(nav)}</nav>\n'
        f'<main>{"".join(bodies)}</main>\n'
    )
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"built index.html from {len(frags)} fragments")

if __name__ == "__main__":
    main()

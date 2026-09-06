import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { DocumentTree } from "../components/document-tree"
import type { DocumentListItem } from "@/hooks/api"

function doc(id: string, uri: string): DocumentListItem {
  return { id, title: null, uri, source_type: "md", project: "p", block_count: 1 }
}

const ITEMS = [
  doc("1", "docs/plans/a.md"),
  doc("2", "docs/spec.md"),
  doc("3", "readme.md"),
]

describe("DocumentTree", () => {
  it("renders folders and leaves from the uri segments", () => {
    render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(screen.getByText("docs")).toBeInTheDocument()
    expect(screen.getByText("readme.md")).toBeInTheDocument()
  })

  it("calls back with the document when a leaf is selected", async () => {
    const onSelect = vi.fn()
    render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={onSelect} truncated={false} />,
    )
    await userEvent.click(screen.getByText("readme.md"))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "3" }))
  })

  it("gives each leaf its extension's icon and each folder both states", () => {
    // The explorer look is CSS over darkraise-ui's parts, so jsdom cannot
    // confirm which folder icon is *visible* -- it performs no layout. What
    // it can confirm is that both are rendered, which is what the
    // `data-state` rule switches between, and that a leaf picked up an icon
    // keyed on its own extension rather than a single generic glyph.
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(container.querySelector(".lucide-folder")).toBeInTheDocument()
    expect(container.querySelector(".lucide-folder-open")).toBeInTheDocument()
    expect(container.querySelector(".lucide-file-text")).toBeInTheDocument()
  })

  it("shows the truncation banner rather than a quietly short tree", () => {
    // Invariant 14: the pagination guard is a real limit and the surface has
    // to say so -- an incomplete tree that looks complete is the defect.
    render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated />,
    )
    expect(screen.getByText(/cut at the pagination guard/i)).toBeInTheDocument()
  })

  it("renders the empty state when the project holds nothing", () => {
    render(
      <DocumentTree items={[]} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(screen.getByText(/No documents filed in this project/i)).toBeInTheDocument()
  })
})

describe("DocumentTree expansion", () => {
  it("shows only what the controlled expanded set opens", () => {
    // The defect this fixes: the component expanded every folder, so 475
    // documents rendered as one wall.
    render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        expanded={["docs"]}
        onExpandedChange={vi.fn()}
      />,
    )
    expect(screen.getByText("spec.md")).toBeInTheDocument()
    expect(screen.queryByText("a.md")).not.toBeInTheDocument()
  })

  it("reports expansion changes as a bare array", async () => {
    const onExpandedChange = vi.fn()
    render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        expanded={[]}
        onExpandedChange={onExpandedChange}
      />,
    )
    await userEvent.click(screen.getByText("docs"))
    expect(onExpandedChange).toHaveBeenCalledWith(expect.any(Array))
  })

  it("keeps expand-everything behaviour when expanded is omitted", () => {
    // Increment 8's editor call site passes neither prop and must be
    // unaffected by the controlled-expansion addition.
    render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(screen.getByText("a.md")).toBeInTheDocument()
    expect(screen.getByText("spec.md")).toBeInTheDocument()
  })
})

describe("DocumentTree — the library's own selection treatment", () => {
  it("carries no local hover fill, so a selected row keeps its selected fill", () => {
    // Tailwind flattens `@layer components` and `@layer utilities` into one
    // sheet with utilities last, so a local `hover:bg-*` on these rows lands
    // after the library's `.dr-tree-view-item:hover` and wins the tie -- the
    // tree then hovers in a colour the rest of the app's trees do not use.
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    for (const row of container.querySelectorAll(
      ".dr-tree-view-item, .dr-tree-view-branch-control",
    )) {
      expect(row.className).not.toMatch(/hover:bg-/)
    }
  })

  it("gives the row its full width, so the highlight is the row and not its text", () => {
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    const rows = container.querySelectorAll(
      ".dr-tree-view-item, .dr-tree-view-branch-control",
    )
    expect(rows.length).toBeGreaterThan(0)
    for (const row of rows) expect(row).toHaveClass("w-full")
  })

  it("keeps the library's own row padding rather than a local override", () => {
    // The padding IS the row height, and the selected fill is drawn on the
    // row -- overriding it to `py-[3px]` made selection read as a thin bar.
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    for (const row of container.querySelectorAll(
      ".dr-tree-view-item, .dr-tree-view-branch-control",
    )) {
      expect(row.className).not.toMatch(/\bp[xy]?-/)
    }
  })
})

describe("DocumentTree — VSCode-shaped rows", () => {
  /** `ITEMS` files documents under folders, so the tree has depth. */
  it("indents inside the row, never on the container", () => {
    // Indenting the child `ul` indents the ROWS: a nested row's box starts
    // further right and is narrower, so its hover and its selected fill are
    // a short bar rather than a full-width one. That was the reported
    // "selection state visual still wrong".
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    const groups = container.querySelectorAll(".dr-tree-view-branch-content")
    expect(groups.length).toBeGreaterThan(0)
    for (const group of groups) {
      expect(group.className).not.toMatch(/\bm[lxs]?-/)
      expect(group.className).not.toMatch(/\bp[lx]-/)
      expect(group.className).not.toMatch(/border-l/)
    }
  })

  it("gives a nested row the same width as a root row", () => {
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    const rows = container.querySelectorAll(
      ".dr-tree-view-item, .dr-tree-view-branch-control",
    )
    // jsdom performs no layout, so width is asserted through the class that
    // produces it plus the absence of any per-depth offset on the row.
    for (const row of rows) {
      expect(row).toHaveClass("w-full")
      expect(row.className).not.toMatch(/\bm[lxs]?-/)
    }
  })

  it("renders a chevron inside the branch indicator", () => {
    // The library's indicator renders only what it is given, so an empty one
    // is a silently invisible expander: the branch still toggles, and nothing
    // on the row says it can be.
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    for (const indicator of container.querySelectorAll(
      ".dr-tree-view-branch-indicator",
    )) {
      expect(indicator.querySelector("svg.lucide-chevron-right")).not.toBeNull()
    }
  })

  it("puts every guide on its owner's chevron centre", () => {
    // A guide descends from the expander that opened the branch: an ancestor
    // at depth `level` has its chevron centred at `level * step + icon / 2`
    // inside every descendant row, which is one whole column left of that
    // row's own chevron, so no guide crosses a glyph. jsdom performs no
    // layout, so the invariant is asserted on the expression that produces
    // it: guide, indent and icon width all have to be written in terms of one
    // `--icon-size`, because a hardcoded pixel icon re-breaks the alignment
    // wherever `--icon-scale` is not its default.
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    const tree = container.querySelector(".dr-tree-view-tree") as HTMLElement
    const step = tree.style.getPropertyValue("--tree-view-indent")
    expect(step).toContain("var(--icon-size)")

    const guides = container.querySelectorAll("span[aria-hidden].absolute")
    expect(guides.length).toBeGreaterThan(0)
    for (const guide of guides) {
      const left = (guide as HTMLElement).style.left
      expect(left).toContain(step)
      expect(left).toContain("var(--icon-size) / 2")
    }

    // Both icon slots are one column wide. A leaf's spacer stands in for the
    // chevron the branch rows spend that width on.
    for (const svg of container.querySelectorAll(
      ".lucide-folder, .lucide-folder-open, .lucide-file-text",
    )) {
      expect(svg.getAttribute("class")).toContain("size-[var(--icon-size)]")
    }
  })

  it("is memoised, so a scroll cannot re-render the whole pane", () => {
    // The artifacts workspace holds the reader's reported heading as its own
    // state, so every heading a long document scrolls past re-renders this
    // pane. Rebuilding the uri tree over a few hundred documents at that rate
    // is what the rail's lag was made of.
    expect((DocumentTree as unknown as { $$typeof: symbol }).$$typeof).toBe(
      Symbol.for("react.memo"),
    )
  })
})

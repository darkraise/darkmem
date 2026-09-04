import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

import { AppMarkdown, CodeBlock, InlineMarkdown, fenceFor } from ".."

describe("AppMarkdown", () => {
  it("opens an external link away from the app, safely", () => {
    render(<AppMarkdown>{"[docs](https://example.com/x)"}</AppMarkdown>)
    const link = screen.getByRole("link", { name: "docs" })
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noopener noreferrer")
  })

  it("leaves an in-page anchor in the same tab", () => {
    // The reader's outline links to `#block-id`. Opening those in a new tab
    // navigates away from the document the reader is showing.
    render(<AppMarkdown>{"[section](#abc123)"}</AppMarkdown>)
    const link = screen.getByRole("link", { name: "section" })
    expect(link).not.toHaveAttribute("target")
  })

  it("renders GFM strikethrough rather than literal tildes", () => {
    // Without remark-gfm this reached the page as `~~gone~~`.
    const { container } = render(<AppMarkdown>{"~~gone~~"}</AppMarkdown>)
    expect(container.querySelector("del")).toBeInTheDocument()
    expect(container.textContent).not.toContain("~~")
  })

  it("linkifies a bare url", () => {
    render(<AppMarkdown>{"see https://example.com/docs now"}</AppMarkdown>)
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "https://example.com/docs",
    )
  })
})

describe("InlineMarkdown", () => {
  it("emits no paragraph, so it is legal inside a heading", () => {
    const { container } = render(<InlineMarkdown>{"a **b**"}</InlineMarkdown>)
    expect(container.querySelector("p")).toBeNull()
    expect(container.querySelector("strong")).toBeInTheDocument()
  })

  it("still renders inline code and links", () => {
    const { container } = render(
      <InlineMarkdown>{"`x` and [y](https://e.com)"}</InlineMarkdown>,
    )
    expect(container.querySelector("code")).toBeInTheDocument()
    expect(container.querySelector("a")).toBeInTheDocument()
  })
})

describe("fenceFor", () => {
  it("uses three backticks for ordinary code", () => {
    expect(fenceFor("x = 1")).toBe("```")
  })

  it("outgrows a fence the code contains", () => {
    // A markdown document quoting a fenced block is exactly the case: a
    // three-backtick fence would close early and spill the rest of the block
    // into the page as prose.
    expect(fenceFor("see ``` here")).toBe("````")
    expect(fenceFor("a ```` b")).toBe("`````")
  })

  it("is unbothered by inline code spans", () => {
    expect(fenceFor("call `f()` twice")).toBe("```")
  })
})

describe("CodeBlock", () => {
  it("labels the stored language", () => {
    render(<CodeBlock code="SELECT 1;" language="sql" />)
    expect(screen.getByText("sql")).toBeInTheDocument()
  })

  it("renders without a label when the fence carried no language", () => {
    const { container } = render(<CodeBlock code="plain" language={null} />)
    expect(container.querySelector("pre")).toBeInTheDocument()
    expect(container.textContent).toContain("plain")
  })

  it("keeps code containing a fence inside the block", () => {
    const code = "before\n```\ninside\n```\nafter"
    const { container } = render(<CodeBlock code={code} />)
    // All of it is in the `pre`; none of it escaped into a sibling.
    expect(container.querySelector("pre")?.textContent).toContain("after")
  })
})

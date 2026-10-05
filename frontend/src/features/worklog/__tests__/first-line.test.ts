import { describe, expect, it } from "vitest"
import { firstLine } from "../components/entry-timeline"

describe("firstLine", () => {
  it("previews the first non-blank line as text, not markdown", () => {
    // The row is plain text; the detail pane renders the markdown.
    expect(firstLine("\n## **State**: `buffer_flush` _done_\nmore")).toBe(
      "State: buffer_flush done",
    )
  })
})

import { describe, expect, it } from "vitest"
import { labelEditorControls } from "../lib/editor-a11y"

function dom(html: string): HTMLElement {
  const root = document.createElement("div")
  root.innerHTML = html
  return root
}

describe("labelEditorControls", () => {
  it("names a checklist box by the action it performs", () => {
    const root = dom(`
      <div data-content-type="checkListItem"><input type="checkbox" /></div>
      <div data-content-type="checkListItem"><input type="checkbox" checked /></div>
    `)
    labelEditorControls(root)
    const [open, done] = root.querySelectorAll("input")
    expect(open!.getAttribute("aria-label")).toBe("Mark as done")
    expect(done!.getAttribute("aria-label")).toBe("Mark as not done")
  })

  it("names a toggle button by the state it will produce", () => {
    const root = dom(`
      <div class="bn-toggle-wrapper" data-show-children="false"><button class="bn-toggle-button"></button></div>
      <div class="bn-toggle-wrapper" data-show-children="true"><button class="bn-toggle-button"></button></div>
    `)
    labelEditorControls(root)
    const [closed, open] = root.querySelectorAll("button")
    expect(closed!.getAttribute("aria-label")).toBe("Expand")
    expect(closed!.getAttribute("aria-expanded")).toBe("false")
    expect(open!.getAttribute("aria-label")).toBe("Collapse")
    expect(open!.getAttribute("aria-expanded")).toBe("true")
  })
})

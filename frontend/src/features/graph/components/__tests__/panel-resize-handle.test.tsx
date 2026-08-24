import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { useState } from "react"
import { PanelResizeHandle } from "../panel-resize-handle"

// Mirrors the real caller (real-memory-graph-page.tsx): `onResize` flows the
// live drag width back in as the next `width` prop, which is what
// `latestRef` in the component actually commits. A test that keeps `width`
// fixed across the drag would commit the wrong value regardless of the bug
// under test.
function Harness({
  initialWidth,
  onCommit,
  widthAt,
}: {
  initialWidth: number
  onCommit: (px: number) => void
  widthAt: (clientX: number) => number
}) {
  const [width, setWidth] = useState(initialWidth)
  return (
    <PanelResizeHandle
      width={width}
      onResize={setWidth}
      onCommit={onCommit}
      widthAt={widthAt}
      min={260}
      max={800}
    />
  )
}

function setup(width = 400) {
  const onCommit = vi.fn()
  const widthAt = vi.fn((clientX: number) => 1000 - clientX)
  render(
    <Harness initialWidth={width} onCommit={onCommit} widthAt={widthAt} />,
  )
  const handle = screen.getByRole("separator")
  return { handle, onCommit, widthAt }
}

// jsdom has no native pointer-capture implementation; stub it the same way
// the component's own runtime environment (a real browser) provides it, so
// dispatching pointerdown does not throw before the behaviour under test runs.
function stubPointerCapture() {
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
}

describe("PanelResizeHandle", () => {
  beforeAll(() => {
    stubPointerCapture()
  })

  it("does not commit on a plain click with no drag", () => {
    const { handle, onCommit } = setup()

    fireEvent.pointerDown(handle, { pointerId: 1 })
    fireEvent.pointerUp(handle, { pointerId: 1 })

    expect(onCommit).not.toHaveBeenCalled()
  })

  it("restores the cursor and text-selection styles on a plain click", () => {
    const { handle } = setup()

    fireEvent.pointerDown(handle, { pointerId: 1 })
    expect(document.body.style.cursor).toBe("col-resize")
    fireEvent.pointerUp(handle, { pointerId: 1 })

    expect(document.body.style.cursor).toBe("")
    expect(document.body.style.userSelect).toBe("")
  })

  it("commits the dragged width once the pointer actually moves", () => {
    const { handle, onCommit } = setup()

    fireEvent.pointerDown(handle, { pointerId: 1 })
    fireEvent.pointerMove(handle, { pointerId: 1, clientX: 700 })
    fireEvent.pointerUp(handle, { pointerId: 1 })

    // widthAt(700) === 1000 - 700 === 300, distinct from the initial 400.
    expect(onCommit).toHaveBeenCalledTimes(1)
    expect(onCommit).toHaveBeenCalledWith(300)
  })

  it("does not commit again on a second no-move release after a real drag", () => {
    const { handle, onCommit } = setup()

    fireEvent.pointerDown(handle, { pointerId: 1 })
    fireEvent.pointerMove(handle, { pointerId: 1, clientX: 700 })
    fireEvent.pointerUp(handle, { pointerId: 1 })
    expect(onCommit).toHaveBeenCalledTimes(1)

    fireEvent.pointerDown(handle, { pointerId: 1 })
    fireEvent.pointerUp(handle, { pointerId: 1 })
    expect(onCommit).toHaveBeenCalledTimes(1)
  })
})

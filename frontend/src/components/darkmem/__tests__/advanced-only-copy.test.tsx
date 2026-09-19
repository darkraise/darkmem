import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"
import { useDetailLevel } from "@/components/darkmem"
import { ListSurface } from "@/features/knowledge/components/list-surface"
import { SurfaceStateChip } from "@/features/activity/components/module-surface"

describe("the populated state word is advanced-only", () => {
  beforeEach(() => useDetailLevel.setState({ level: "simple" }))

  it("ListSurface hides 'populated' in Simple and keeps 'empty'", () => {
    const { rerender } = render(
      <ListSurface title="Facts" populated>
        <div />
      </ListSurface>,
    )
    expect(screen.queryByText("populated")).toBeNull()
    rerender(
      <ListSurface title="Facts" populated={false}>
        <div />
      </ListSurface>,
    )
    expect(screen.getByText("empty")).toBeInTheDocument()
  })

  it("SurfaceStateChip hides 'populated' in Simple and keeps the others", () => {
    const { rerender } = render(<SurfaceStateChip state="populated" />)
    expect(screen.queryByText("populated")).toBeNull()
    rerender(<SurfaceStateChip state="error" />)
    expect(screen.getByText("error")).toBeInTheDocument()
    rerender(<SurfaceStateChip state="empty" />)
    expect(screen.getByText("empty")).toBeInTheDocument()
  })

  it("both show 'populated' in Advanced", () => {
    useDetailLevel.setState({ level: "advanced" })
    render(
      <>
        <ListSurface title="Facts" populated>
          <div />
        </ListSurface>
        <SurfaceStateChip state="populated" />
      </>,
    )
    expect(screen.getAllByText("populated")).toHaveLength(2)
  })
})

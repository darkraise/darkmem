import { act, renderHook } from "@testing-library/react"
import { afterEach, expect, it } from "vitest"
import { useDocumentMode } from "../use-document-mode"

afterEach(() => {
  delete document.documentElement.dataset.mode
})

it("reads the mode the theme provider writes and follows a change", async () => {
  const { result } = renderHook(() => useDocumentMode())
  expect(result.current).toBe("light")
  await act(async () => {
    document.documentElement.dataset.mode = "dark"
  })
  expect(result.current).toBe("dark")
})

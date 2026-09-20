import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiUpload } from "@/lib/api"

const logout = vi.fn()
const getState = vi.fn(() => ({ logout }))
vi.mock("@/features/auth", () => ({ useAuthStore: { getState: () => getState() } }))

type Handler = (xhr: FakeXhr) => void

class FakeXhr {
  static handler: Handler = () => {}
  upload = { onprogress: null as ((e: ProgressEvent) => void) | null }
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  onabort: (() => void) | null = null
  withCredentials = false
  status = 0
  responseText = ""
  method = ""
  url = ""
  headers: Record<string, string> = {}
  aborted = false

  open(method: string, url: string) {
    this.method = method
    this.url = url
  }
  setRequestHeader(key: string, value: string) {
    this.headers[key] = value
  }
  abort() {
    this.aborted = true
    this.onabort?.()
  }
  send(_body: unknown) {
    FakeXhr.handler(this)
  }
}

beforeEach(() => {
  vi.stubGlobal("XMLHttpRequest", FakeXhr)
  logout.mockClear()
  FakeXhr.handler = (xhr) => {
    xhr.status = 201
    xhr.responseText = JSON.stringify({ ok: true })
    xhr.onload?.()
  }
})

describe("apiUpload", () => {
  it("posts to the v1 base with credentials", async () => {
    let seen: FakeXhr | null = null
    FakeXhr.handler = (xhr) => {
      seen = xhr
      xhr.status = 201
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await apiUpload("/pages/import/notion?project=notes", new Blob(["x"]))
    expect(seen!.method).toBe("POST")
    expect(seen!.url).toBe("/api/v1/pages/import/notion?project=notes")
    expect(seen!.withCredentials).toBe(true)
  })

  it("returns the parsed body", async () => {
    const body = await apiUpload<{ ok: boolean }>("/x", new Blob(["x"]))
    expect(body).toEqual({ ok: true })
  })

  it("passes supplied headers through", async () => {
    let seen: FakeXhr | null = null
    FakeXhr.handler = (xhr) => {
      seen = xhr
      xhr.status = 201
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await apiUpload("/x", new Blob(["x"]), {
      headers: { "Content-Type": "application/zip" },
    })
    expect(seen!.headers["Content-Type"]).toBe("application/zip")
  })

  it("reports upload progress as a fraction", async () => {
    const seen: number[] = []
    FakeXhr.handler = (xhr) => {
      xhr.upload.onprogress?.({ lengthComputable: true, loaded: 25, total: 100 } as ProgressEvent)
      xhr.upload.onprogress?.({ lengthComputable: true, loaded: 100, total: 100 } as ProgressEvent)
      xhr.status = 201
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await apiUpload("/x", new Blob(["x"]), { onProgress: (f) => seen.push(f) })
    expect(seen).toEqual([0.25, 1])
  })

  it("ignores a progress event with no total", async () => {
    const seen: number[] = []
    FakeXhr.handler = (xhr) => {
      xhr.upload.onprogress?.({ lengthComputable: false, loaded: 5, total: 0 } as ProgressEvent)
      xhr.status = 201
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await apiUpload("/x", new Blob(["x"]), { onProgress: (f) => seen.push(f) })
    expect(seen).toEqual([])
  })

  it("throws an ApiError carrying the envelope detail", async () => {
    FakeXhr.handler = (xhr) => {
      xhr.status = 422
      xhr.responseText = JSON.stringify({ detail: "re-export as Markdown & CSV" })
      xhr.onload?.()
    }
    await expect(apiUpload("/x", new Blob(["x"]))).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
      message: "re-export as Markdown & CSV",
    })
  })

  it("falls back to a status message when the body is not JSON", async () => {
    FakeXhr.handler = (xhr) => {
      xhr.status = 500
      xhr.responseText = "<html>"
      xhr.onload?.()
    }
    await expect(apiUpload("/x", new Blob(["x"]))).rejects.toBeInstanceOf(ApiError)
  })

  it("logs out and throws on a 401", async () => {
    FakeXhr.handler = (xhr) => {
      xhr.status = 401
      xhr.responseText = "{}"
      xhr.onload?.()
    }
    await expect(apiUpload("/x", new Blob(["x"]))).rejects.toMatchObject({ status: 401 })
    expect(logout).toHaveBeenCalled()
  })

  it("rejects on a transport error", async () => {
    FakeXhr.handler = (xhr) => xhr.onerror?.()
    await expect(apiUpload("/x", new Blob(["x"]))).rejects.toBeInstanceOf(ApiError)
  })

  it("aborts when its signal fires", async () => {
    const controller = new AbortController()
    let seen: FakeXhr | null = null
    FakeXhr.handler = (xhr) => {
      seen = xhr
      controller.abort()
    }
    await expect(
      apiUpload("/x", new Blob(["x"]), { signal: controller.signal }),
    ).rejects.toBeInstanceOf(ApiError)
    expect(seen!.aborted).toBe(true)
  })
})

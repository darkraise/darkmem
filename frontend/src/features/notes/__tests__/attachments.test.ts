import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
  ATTACHMENT_URL,
  isAttachmentUrl,
  isImageType,
  resetUploadsInFlight,
  subscribeUploads,
  uploadAttachment,
  uploadsInFlight,
} from "../lib/attachments"

const CLEANUP_JOB = resolve("..", "backend", "app", "services", "page_attachment_cleanup.py")
const ID = "0123abcd-4567-89ef-0123-456789abcdef"

describe("isAttachmentUrl", () => {
  it("ends in the cleanup job's own character class", () => {
    const source = readFileSync(CLEANUP_JOB, "utf8")
    const pattern = /'\/api\/v1\/pages\/attachments\/\(([^']+)\)'/.exec(source)
    expect(pattern).not.toBeNull()
    expect(ATTACHMENT_URL.source.endsWith(`${pattern![1]}$`)).toBe(true)
  })

  it("accepts a served attachment url", () => {
    expect(isAttachmentUrl(`/api/v1/pages/attachments/${ID}`)).toBe(true)
  })

  it("accepts an uppercase id, which the cleanup job retains", () => {
    expect(isAttachmentUrl(`/api/v1/pages/attachments/${ID.toUpperCase()}`)).toBe(true)
  })

  it("rejects a value of the right length that is not a uuid", () => {
    expect(isAttachmentUrl(`/api/v1/pages/attachments/${"-".repeat(36)}`)).toBe(false)
  })

  it("rejects a different path, a suffix and an empty string", () => {
    expect(isAttachmentUrl(`/api/v1/documents/attachments/${ID}`)).toBe(false)
    expect(isAttachmentUrl(`/api/v1/pages/attachments/${ID}/raw`)).toBe(false)
    expect(isAttachmentUrl("")).toBe(false)
  })
})

const UPLOADED = { id: ID, url: `/api/v1/pages/attachments/${ID}`, filename: "x.png", content_type: "image/png", size_bytes: 3 }

// The parameters are declared even though the body ignores them: the mock's
// call tuple is what the first test destructures, and `noUnusedParameters` is
// on, so they carry the leading underscore.
function stubFetch(body: unknown, status = 201) {
  const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }),
  )
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}

describe("uploadAttachment", () => {
  beforeEach(() => resetUploadsInFlight())
  afterEach(() => vi.unstubAllGlobals())

  it("sends the file as the raw body with an encoded filename", async () => {
    const fetchMock = stubFetch(UPLOADED)
    const file = new File(["abc"], "a b/c.png", { type: "image/png" })
    const result = await uploadAttachment("page-1", file)
    expect(result).toEqual({ url: UPLOADED.url, contentType: "image/png" })
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe("/api/v1/pages/page-1/attachments")
    expect(init!.method).toBe("POST")
    expect(init!.body).toBe(file)
    const headers = init!.headers as Record<string, string>
    expect(headers["X-Filename"]).toBe(encodeURIComponent("a b/c.png"))
    expect(headers["Content-Type"]).toBe("application/octet-stream")
  })

  it("counts an upload in flight and notifies subscribers", async () => {
    stubFetch(UPLOADED)
    const seen: number[] = []
    const stop = subscribeUploads(() => seen.push(uploadsInFlight()))
    await uploadAttachment("page-1", new File(["abc"], "a.png"))
    stop()
    expect(seen).toEqual([1, 0])
    expect(uploadsInFlight()).toBe(0)
  })

  it("decrements the count when the upload is refused", async () => {
    stubFetch({ detail: "attachment exceeds 52428800 bytes" }, 413)
    await expect(uploadAttachment("page-1", new File(["abc"], "a.png"))).rejects.toThrow(
      "attachment exceeds",
    )
    expect(uploadsInFlight()).toBe(0)
  })
})

describe("isImageType", () => {
  it("is the four types the route serves inline", () => {
    for (const t of ["image/png", "image/jpeg", "image/gif", "image/webp"]) {
      expect(isImageType(t)).toBe(true)
    }
    expect(isImageType("image/svg+xml")).toBe(false)
    expect(isImageType("application/octet-stream")).toBe(false)
  })
})

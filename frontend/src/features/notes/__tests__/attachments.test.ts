import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"
import { ATTACHMENT_URL, isAttachmentUrl } from "../lib/attachments"

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

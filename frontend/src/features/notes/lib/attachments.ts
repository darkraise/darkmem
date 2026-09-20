import { apiFetch } from "@/lib/api"

/** The attachment URL, anchored, in the one spelling the whole feature uses.
 *
 *  The character class is `page_attachment_cleanup`'s own: that job scans
 *  `blocks.text` for this shape to decide which files are still referenced,
 *  and it deliberately retains an uppercase id. A looser class would be wrong
 *  in both directions — it would reject a URL the job keeps alive, and accept
 *  a malformed one the serving route answers 422 for. */
export const ATTACHMENT_URL =
  /^\/api\/v1\/pages\/attachments\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/

export function isAttachmentUrl(url: string): boolean {
  return ATTACHMENT_URL.test(url)
}

export interface UploadedAttachment {
  url: string
  contentType: string
}

/** The four types the serving route sniffs and serves inline. Everything else
 *  it stores as `application/octet-stream` and serves as a download, so an
 *  image block pointing at one would render nothing. */
const INLINE_IMAGE_TYPES: ReadonlySet<string> = new Set([
  "image/png",
  "image/jpeg",
  "image/gif",
  "image/webp",
])

export function isImageType(contentType: string): boolean {
  return INLINE_IMAGE_TYPES.has(contentType)
}

/** Uploads in flight, counted across every mounted editor.
 *
 *  It lives outside the sync tree because a block whose upload has not
 *  resolved carries no url and so appears in no tree: without this count the
 *  save engine reports "saved" and the unload warning stays silent while a
 *  file is still going up. Module scope rather than editor scope because the
 *  reader is `use-page-sync`'s `anyPending`, which runs over every engine with
 *  no editor in hand -- and "is any work outstanding" is the question the
 *  unload guard actually asks. */
let inFlight = 0
const listeners = new Set<() => void>()

export function uploadsInFlight(): number {
  return inFlight
}

export function subscribeUploads(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Test hook: forget the count between tests. */
export function resetUploadsInFlight(): void {
  inFlight = 0
  listeners.clear()
}

function setInFlight(next: number) {
  inFlight = next
  for (const listener of listeners) listener()
}

export async function uploadAttachment(pageId: string, file: File): Promise<UploadedAttachment> {
  setInFlight(inFlight + 1)
  try {
    const data = await apiFetch<{ url: string; content_type: string }>(
      `/pages/${pageId}/attachments`,
      {
        method: "POST",
        body: file,
        headers: {
          // The route ignores the request's own type and sniffs the bytes, so
          // this only stops the shared helper's JSON default from being sent.
          "Content-Type": "application/octet-stream",
          "X-Filename": encodeURIComponent(file.name),
        },
      },
    )
    return { url: data.url, contentType: data.content_type }
  } finally {
    setInFlight(inFlight - 1)
  }
}

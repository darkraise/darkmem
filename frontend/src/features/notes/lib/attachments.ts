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

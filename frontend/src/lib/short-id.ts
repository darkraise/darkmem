/** A short label that tells two ids apart on screen.
 *
 *  Ids are UUIDv7 (`backend/app/utils/ids.py`), whose leading 48 bits are a
 *  millisecond timestamp: the first eight hex digits change only every ~65
 *  seconds, so a prefix labelled every memory captured in the same minute
 *  identically ("01a10d4c"). The tail is the random part, so it is what
 *  distinguishes. Strings that are not UUID-shaped come back unchanged. */
export function shortId(id: string | null | undefined): string {
  if (!id) return ""
  const hex = id.replace(/-/g, "")
  return /^[0-9a-f]{32}$/i.test(hex) ? hex.slice(-8) : id
}

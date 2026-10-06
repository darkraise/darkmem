/** The post-login destination, if it is one to honour.
 *
 *  Only an in-app path counts: a scheme or a protocol-relative `//host`
 *  would turn the login form into an open redirect, and the guest pages
 *  themselves would bounce straight back. */
export function safeRedirect(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined
  if (!value.startsWith("/") || value.startsWith("//")) return undefined
  if (/^\/(login|setup)(?=$|[/?#])/.test(value)) return undefined
  return value
}

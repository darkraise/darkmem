// One wording for a failed model probe, shared by the setup wizard and
// Settings → LLM. Both probe routes answer 200 with an `error` string written
// for logs ("API key required for api_kind='openai'", "HTTP 401: …",
// "network error: …"); this turns the shapes they emit into a sentence an
// operator can act on, and passes anything else through unchanged.
export function describeProbeError(error: string): string {
  if (/^API key required\b/.test(error))
    return "This provider needs an API key."
  const http = /^HTTP (\d{3})\b/.exec(error)
  if (http) {
    const code = http[1]
    if (code === "401" || code === "403")
      return `The provider refused the API key (HTTP ${code}).`
    if (code === "404")
      return "The provider has no model list at this base URL (HTTP 404). Check the base URL."
    return `The provider answered with an error (HTTP ${code}).`
  }
  const unreachable = /^(?:network error|probe failed): (.*)$/s.exec(error)
  if (unreachable)
    return `Could not reach the provider${unreachable[1] ? `: ${unreachable[1]}` : "."}`
  return error
}

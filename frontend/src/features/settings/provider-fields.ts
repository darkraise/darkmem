// The provider form's half of `app/schemas/config.py`'s ProviderName and
// ProviderBaseUrl: the same rules and the same words, so the form refuses
// what the server would answer 422 to before anything is sent. Both the setup
// wizard and Settings → LLM read these.

export const PROVIDER_NAME_MAX_LENGTH = 64

// Starting with a letter or digit keeps "." and ".." out; a "/" anywhere made
// a provider no `/config/llm-providers/{name}` route could reach again.
const PROVIDER_NAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/

// Python's urlsplit: an http(s) scheme (any case), then a host that is not
// empty once userinfo and port are taken off, and no whitespace anywhere.
// Written out rather than `new URL()`, which accepts "http:/host" and
// "http:host" that the server refuses.
const BASE_URL_PATTERN =
  /^https?:\/\/(?:[^@/?#\s]*@)?(?:\[[^\]\s]+\]|[^:/?#@\s[\]]+)(?::[^/?#\s]*)?(?:[/?#]\S*)?$/i

export function providerNameError(name: string): string | null {
  if (name === "") return null
  if (name.length > PROVIDER_NAME_MAX_LENGTH)
    return `Use at most ${PROVIDER_NAME_MAX_LENGTH} characters.`
  if (!PROVIDER_NAME_PATTERN.test(name))
    return "Use only letters, digits, dot, dash and underscore, starting with a letter or digit."
  return null
}

export function providerBaseUrlError(url: string): string | null {
  if (url === "") return null
  if (!BASE_URL_PATTERN.test(url))
    return "Enter an http:// or https:// address with a host, for example https://api.openai.com/v1."
  return null
}

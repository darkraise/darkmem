import { describe, expect, it } from "vitest"
import { describeProbeError } from "../probe-error"

describe("describeProbeError", () => {
  it("says a missing key in plain words, without the api_kind repr", () => {
    expect(describeProbeError("API key required for api_kind='openai'")).toBe(
      "This provider needs an API key.",
    )
  })

  it("names a refused key and a wrong base URL", () => {
    expect(describeProbeError('HTTP 401: {"error":"bad key"}')).toBe(
      "The provider refused the API key (HTTP 401).",
    )
    expect(describeProbeError("HTTP 404: Not Found")).toMatch(
      /Check the base URL/,
    )
    expect(describeProbeError("HTTP 500: boom")).toBe(
      "The provider answered with an error (HTTP 500).",
    )
  })

  it("reads both routes' transport failures the same way", () => {
    expect(
      describeProbeError("network error: All connection attempts failed"),
    ).toBe("Could not reach the provider: All connection attempts failed")
    expect(
      describeProbeError("probe failed: All connection attempts failed"),
    ).toBe("Could not reach the provider: All connection attempts failed")
  })

  it("passes an unknown message through", () => {
    expect(describeProbeError("connection refused")).toBe("connection refused")
  })
})

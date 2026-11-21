import { vi } from "vitest"

/** A `fetch` routed by path, each route answering a queue of responses (the
 *  last one repeats); a route may answer a deferred promise. */
export type Answer = Response | Promise<Response>
export function routeFetch(routes: Record<string, Answer[]>) {
  const calls: string[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url
    const path = url.replace(/^.*\/api\/v1/, "")
    calls.push(path)
    const queue = routes[path]
    if (!queue || queue.length === 0) return json({}, 404)
    return queue.length > 1 ? queue.shift()! : queue[0]!
  })
  vi.stubGlobal("fetch", fetchMock)
  return { fetchMock, calls, count: (path: string) => calls.filter((p) => p === path).length }
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

export function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

export const minutesAhead = (minutes: number) => new Date(Date.now() + minutes * 60_000).toISOString()

/** A WebSocket that, like a browser's, reports its own close a task later. */
export class FakeSocket {
  static instances: FakeSocket[] = []
  readyState = 0
  onopen: (() => void) | null = null
  onclose: ((event: { code: number; reason: string }) => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null

  constructor(public url: string) {
    FakeSocket.instances.push(this)
  }

  close() {
    if (this.readyState >= 2) return
    this.readyState = 2
    setTimeout(() => this.serverClose(1005, ""), 0)
  }

  open() {
    this.readyState = 1
    this.onopen?.()
  }

  serverClose(code: number, reason: string) {
    this.readyState = 3
    this.onclose?.({ code, reason })
  }

  message(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }

  static live(): FakeSocket[] {
    return FakeSocket.instances.filter((s) => s.readyState < 2)
  }

  static latest(): FakeSocket {
    const socket = FakeSocket.instances[FakeSocket.instances.length - 1]
    if (!socket) throw new Error("no socket was opened")
    return socket
  }
}

/**
 * Timers a test file leaves behind when it ends.
 *
 * Vitest tears an environment down between files with
 * `keys.forEach((key) => delete global[key])`, so every jsdom global — `window`,
 * `document`, `cancelAnimationFrame` — stops existing for the moment between
 * one file's teardown and the next file's setup. A `setTimeout` scheduled
 * during the file sits on Node's queue, not jsdom's, so it survives that
 * deletion and can fire into the gap. A callback that touches any jsdom global
 * then throws where no test can catch it, and vitest reports an unhandled error
 * and exits non-zero with every test still passing.
 *
 * The live example is Redux Toolkit's notification scheduler, reached through
 * recharts: it takes `createRafWithFallbackTimer(window.requestAnimationFrame,
 * 100)` and the fallback's first act is `cancelAnimationFrame(rafId)`. The rAF
 * stub in `setup.ts` deliberately never invokes its callback — invoking it
 * would let a draw loop reschedule forever — so RTK's `called` flag never flips
 * and *every* notification leaves that 100ms timer armed. Whether one lands in
 * the gap is a question of machine load, which is why this turned the merge gate
 * red once and passed four full runs in a row afterwards.
 *
 * `setInterval` gets the same treatment for the same reason, and is strictly
 * worse left untracked: it survives a `clearPendingTimers()` sweep aimed only
 * at timeouts, and instead of firing once into the gap it fires forever.
 *
 * Clearing what is still armed when a file ends is safe by construction: every
 * test in the file has already finished, so nothing in it is waiting on the
 * timer any more.
 */

type TimeoutId = ReturnType<typeof setTimeout>
type IntervalId = ReturnType<typeof setInterval>

const pendingTimeouts = new Set<TimeoutId>()
const pendingIntervals = new Set<IntervalId>()

/** Captured before anything can swap the globals, so the sweep still works
 *  under `vi.useFakeTimers()`. */
let nativeClearTimeout: typeof globalThis.clearTimeout | null = null
let nativeClearInterval: typeof globalThis.clearInterval | null = null

/** For the harness's own test; not part of the fixture surface. */
export function pendingTimerCount(): number {
  return pendingTimeouts.size + pendingIntervals.size
}

/**
 * Wrap `setTimeout`/`clearTimeout` and `setInterval`/`clearInterval` so what
 * is still armed can be cancelled.
 *
 * Called at module scope in the setup file, which runs once per test file after
 * the environment is installed. `vi.useFakeTimers()` swaps these out for its
 * own while it is active and restores them after, so a test using fake timers
 * simply bypasses the tracking.
 */
export function trackTimers(): void {
  const nativeSetTimeout = globalThis.setTimeout
  nativeClearTimeout = globalThis.clearTimeout
  const nativeSetInterval = globalThis.setInterval
  nativeClearInterval = globalThis.clearInterval

  globalThis.setTimeout = ((
    handler: TimerHandler,
    timeout?: number,
    ...args: unknown[]
  ) => {
    // A string handler is `eval` in disguise and nothing here uses it; hand it
    // straight to the platform rather than reimplementing that path.
    if (typeof handler !== "function") {
      return nativeSetTimeout(handler, timeout, ...args)
    }
    // The wrapper closes over `id` before `nativeSetTimeout` returns it. Even a
    // zero-delay timer cannot fire before this frame yields, so the binding is
    // always assigned by the time the callback reads it.
    const id: TimeoutId = nativeSetTimeout(
      (...callbackArgs: unknown[]) => {
        pendingTimeouts.delete(id)
        handler(...callbackArgs)
      },
      timeout,
      ...args,
    )
    pendingTimeouts.add(id)
    return id
  }) as typeof globalThis.setTimeout

  globalThis.clearTimeout = ((id: TimeoutId) => {
    pendingTimeouts.delete(id)
    nativeClearTimeout?.(id)
  }) as typeof globalThis.clearTimeout

  globalThis.setInterval = ((
    handler: TimerHandler,
    timeout?: number,
    ...args: unknown[]
  ) => {
    if (typeof handler !== "function") {
      return nativeSetInterval(handler, timeout, ...args)
    }
    // Unlike a timeout, an interval's own id is never removed from the set by
    // its callback: it keeps firing until something clears it, which is
    // exactly the state a leaked one is stuck in.
    const id: IntervalId = nativeSetInterval(
      (...callbackArgs: unknown[]) => {
        handler(...callbackArgs)
      },
      timeout,
      ...args,
    )
    pendingIntervals.add(id)
    return id
  }) as typeof globalThis.setInterval

  globalThis.clearInterval = ((id: IntervalId) => {
    pendingIntervals.delete(id)
    nativeClearInterval?.(id)
  }) as typeof globalThis.clearInterval
}

/** Cancel everything still armed. Run from `afterAll`. */
export function clearPendingTimers(): void {
  for (const id of pendingTimeouts) nativeClearTimeout?.(id)
  pendingTimeouts.clear()
  for (const id of pendingIntervals) nativeClearInterval?.(id)
  pendingIntervals.clear()
}

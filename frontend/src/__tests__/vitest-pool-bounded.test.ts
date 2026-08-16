import { availableParallelism } from "node:os"
import { describe, expect, it } from "vitest"

import config, { MAX_WORKERS } from "../../vitest.config"

// T4.12: the `frontend test` gate step reds on a loaded host for a reason no
// diff caused, which routes the autonomous loop straight into stop condition
// 7. The bound is what makes the step degrade in duration instead — it is a
// property of the suite, not a preference, so removing it must fail loudly
// rather than show up as an unexplained red weeks later.
describe("the vitest worker pool is bounded", () => {
  it("never takes more than four workers, nor more than half the host above two cores", () => {
    // The title says "above two cores" because the bound has a floor of 2:
    // on a 1- or 2-core host the pool is the whole host, deliberately, since
    // serialising the suite onto a single worker there costs more than the
    // contention it avoids. The earlier title claimed "never more than half
    // the host" flatly, which its own assertion did not check (E4 review, M6).
    expect(MAX_WORKERS).toBeLessThanOrEqual(4)
    expect(MAX_WORKERS).toBeLessThanOrEqual(Math.max(2, Math.floor(availableParallelism() / 2)))
    expect(MAX_WORKERS).toBeGreaterThanOrEqual(1)
    if (availableParallelism() > 4) {
      expect(MAX_WORKERS).toBeLessThanOrEqual(availableParallelism() / 2)
    }
  })

  it("the bound is wired into the config, not merely exported from it", () => {
    expect(config.test?.maxWorkers).toBe(MAX_WORKERS)
  })

  it("leaves the hook and test timeouts at their defaults", () => {
    // Raising these is the one change that could mask a genuinely slow hook,
    // so it is not made silently: measured max hook duration is 417ms against
    // the 10000ms default. A future raise belongs with its own measurement.
    expect(config.test?.hookTimeout).toBeUndefined()
    expect(config.test?.testTimeout).toBeUndefined()
  })
})

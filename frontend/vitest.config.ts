import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import { availableParallelism } from "node:os"
import path from "path"

// Vitest sizes its pool to the host, so under gate load the workers compete
// with everything else and hooks blow the 10s default — 14 unrelated files
// failed on the clock at load 57/16 cores with ~4GB in swap, against 811 green
// in 20s standalone. Half the host, at most four: peak worker RSS measured
// ~272MB, so an unbounded 16-core run is ~4GB of workers alone. Capping the
// pool can only serialise work, never mask a failing assertion — which is why
// the timeouts stay at their defaults (measured max hook 417ms vs 10000ms).
export const MAX_WORKERS = Math.max(2, Math.min(4, Math.floor(availableParallelism() / 2)))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    exclude: ["**/node_modules/**", "**/dist/**", "tests/**"],
    maxWorkers: MAX_WORKERS,
  },
})

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, it, expect, vi, beforeEach } from "vitest"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn().mockResolvedValue({}) }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { apiFetch } from "@/lib/api"
import { JobConfigForm } from "@/features/jobs/components/jobs-panel"
import type { Job } from "@/hooks/api"

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient()
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const job = {
  key: "code_enrichment",
  display_name: "Code Symbol Enrichment",
  description: "",
  enabled: true,
  cron: "*/10 * * * * *",
  min_interval_seconds: 1,
  default_cron: "*/10 * * * * *",
  last_run_at: null,
  last_status: null,
  last_error: null,
  running: false,
  config: { batch_size: 7 },
  config_schema: [
    {
      key: "batch_size",
      type: "int",
      label: "Batch Size",
      default: 5,
      min: 1,
      max: 100,
    },
  ],
} as Job

describe("JobConfigForm", () => {
  beforeEach(() => vi.clearAllMocks())

  it("saves the seeded config via PUT /jobs/{key}/config", async () => {
    const onClose = vi.fn()
    wrap(
      <JobConfigForm job={job} schema={job.config_schema!} onClose={onClose} />,
    )
    await userEvent.click(screen.getByRole("button", { name: /save/i }))
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/jobs/code_enrichment/config",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ config: { batch_size: 7 } }),
        }),
      ),
    )
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })
})

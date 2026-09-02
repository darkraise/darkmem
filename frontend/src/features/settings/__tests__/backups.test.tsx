import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { BackupsTab } from "../components/backups-tab"

/**
 * Increment 6's operator surface.
 *
 * Two properties carry the tab. A secret renders as the mask and, when the
 * operator does not touch it, goes back as the mask — the server reads that
 * as "unchanged", so a private key never crosses the wire in either
 * direction. And the encrypt-before-egress rule is the *server's* refusal,
 * rendered here rather than re-implemented: the tab shows the 422 it gets
 * back, so there is one place that decides and one place that explains.
 */

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const LOCAL = {
  name: "disk",
  kind: "local" as const,
  enabled: true,
  retention_keep: 14,
  age_recipient: null,
  ssh: null,
  s3: null,
}

const NAS = {
  name: "nas",
  kind: "ssh" as const,
  enabled: true,
  retention_keep: 30,
  age_recipient: "age1qqqqexample",
  ssh: {
    host: "192.0.2.10",
    port: 22,
    user: "backup",
    remote_dir: "/srv/darkmem",
    host_key: "192.0.2.10 ssh-ed25519 AAAA",
    private_key: "***",
  },
  s3: null,
}

function routes(overrides: Record<string, unknown> = {}) {
  const table: Record<string, unknown> = {
    "/config/backup-destinations": { destinations: [LOCAL, NAS] },
    "/events?event_type=backup_shipped&limit=50": { items: [], total: 0 },
    "/events?event_type=backup_verify_failed&limit=50": { items: [], total: 0 },
    ...overrides,
  }
  return vi.mocked(apiFetch).mockImplementation(async (path: string) => {
    for (const [key, value] of Object.entries(table)) {
      if (path.startsWith(key)) return value
    }
    return {}
  })
}

afterEach(() => vi.mocked(apiFetch).mockReset())

describe("BackupsTab", () => {
  it("lists every destination with its kind and retention", async () => {
    routes()
    render(<BackupsTab />, { wrapper })

    expect(await screen.findByText("disk")).toBeInTheDocument()
    expect(screen.getByText("nas")).toBeInTheDocument()
    // The kind badges, matched exactly: "local" and "ssh" also appear in the
    // posture copy above the list.
    expect(screen.getByText("local")).toBeInTheDocument()
    expect(screen.getByText("ssh")).toBeInTheDocument()
    expect(screen.getByText(/keeps 14/i)).toBeInTheDocument()
    expect(screen.getByText(/keeps 30/i)).toBeInTheDocument()
  })

  it("states the two-producer posture so an operator is not told this is the only backup", async () => {
    routes()
    render(<BackupsTab />, { wrapper })

    expect(
      await screen.findByText(
        /systemd timer keeps its own local dumps independently/i,
      ),
    ).toBeInTheDocument()
  })

  it("renders the last outcome per destination, failure included", async () => {
    routes({
      "/events?event_type=backup_shipped&limit=50": {
        items: [
          {
            id: 2,
            created_at: "2026-09-01T04:30:00Z",
            event_type: "backup_shipped",
            object_type: "system",
            object_id: null,
            project: null,
            actor: null,
            api_key_id: null,
            source: "backup_ship",
            payload: { destination: "disk", file: "darkmem-app-x.sql.gz", sha256: "a".repeat(64) },
          },
        ],
        total: 1,
      },
      "/events?event_type=backup_verify_failed&limit=50": {
        items: [
          {
            id: 3,
            created_at: "2026-09-01T04:31:00Z",
            event_type: "backup_verify_failed",
            object_type: "system",
            object_id: null,
            project: null,
            actor: null,
            api_key_id: null,
            source: "backup_ship",
            payload: { destination: "nas", file: "darkmem-app-x.sql.gz.age", error: "the NAS is unplugged" },
          },
        ],
        total: 1,
      },
    })
    render(<BackupsTab />, { wrapper })

    expect(await screen.findByText(/verified/i)).toBeInTheDocument()
    expect(screen.getByText(/the NAS is unplugged/)).toBeInTheDocument()
  })

  it("sends an untouched secret back as the mask", async () => {
    const fetchMock = routes()
    render(<BackupsTab />, { wrapper })

    fireEvent.click(await screen.findByRole("button", { name: /edit nas/i }))
    fireEvent.change(await screen.findByLabelText(/keep/i), {
      target: { value: "45" },
    })
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }))

    await waitFor(() => {
      const put = fetchMock.mock.calls.find(
        ([, init]) => (init as RequestInit | undefined)?.method === "PUT",
      )
      expect(put).toBeDefined()
      const body = JSON.parse((put![1] as RequestInit).body as string)
      const nas = body.destinations.find(
        (d: { name: string }) => d.name === "nas",
      )
      expect(nas.ssh.private_key).toBe("***")
      expect(nas.retention_keep).toBe(45)
    })
  })

  it("shows the server's refusal for an unencrypted egress destination", async () => {
    const fetchMock = routes()
    fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        throw new Error(
          "nas: encrypt before egress -- a non-local destination requires an age recipient",
        )
      }
      if (path.startsWith("/config/backup-destinations")) {
        return { destinations: [LOCAL, NAS] }
      }
      return { items: [], total: 0 }
    })
    render(<BackupsTab />, { wrapper })

    fireEvent.click(await screen.findByRole("button", { name: /edit nas/i }))
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }))

    expect(await screen.findByText(/encrypt before egress/i)).toBeInTheDocument()
  })

  it("posts the job trigger when Run now is pressed", async () => {
    const fetchMock = routes()
    render(<BackupsTab />, { wrapper })

    fireEvent.click(await screen.findByRole("button", { name: /run now/i }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/jobs/backup_ship/trigger",
        expect.objectContaining({ method: "POST" }),
      ),
    )
  })

  it("renders the empty state rather than an empty list", async () => {
    routes({ "/config/backup-destinations": { destinations: [] } })
    render(<BackupsTab />, { wrapper })

    expect(
      await screen.findByText(/no destinations configured/i),
    ).toBeInTheDocument()
  })
})

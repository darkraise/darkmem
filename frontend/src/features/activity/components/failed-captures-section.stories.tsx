import type { Meta, StoryObj } from "@storybook/react"
import { userEvent, within } from "storybook/test"
import type { BufferRow } from "@/hooks/api/use-memory-buffer-api"
import { FailedCapturesSection } from "./failed-captures-section"

function row(i: number, overrides: Partial<BufferRow> = {}): BufferRow {
  const tail = String(i).padStart(4, "0")
  return {
    id: `0190f000-0000-7000-8000-00000000${tail}`,
    memory_id: `0190f000-0000-7000-8000-0000abcd${tail}`,
    memory_exists: i % 2 === 0,
    project: i % 3 === 0 ? "notes" : "darkmem",
    source: "api",
    status: "error",
    is_stale: false,
    attempts: 5,
    max_attempts: 5,
    last_error: "value too long for type character varying(64)",
    created_at: "2026-11-20T10:00:00Z",
    claimed_at: null,
    claimed_by: null,
    token_size: null,
    content_preview: `Capture ${i}: the payments worker kept restarting after the deploy`,
    content_length: 64,
    ...overrides,
  }
}

const resolved = () => Promise.resolve()

const meta: Meta<typeof FailedCapturesSection> = {
  title: "Activity/FailedCapturesSection",
  component: FailedCapturesSection,
  args: {
    items: [],
    total: 0,
    isLoading: false,
    isError: false,
    onRequeue: resolved,
    onDiscard: resolved,
  },
  decorators: [
    (Story) => (
      <div className="bg-background max-w-3xl p-4">
        <Story />
      </div>
    ),
  ],
}
export default meta

type S = StoryObj<typeof FailedCapturesSection>

export const Empty: S = {}

export const OneRow: S = {
  args: { items: [row(0)], total: 1 },
}

export const NewestPageOfMany: S = {
  args: {
    items: Array.from({ length: 200 }, (_, i) => row(i)),
    total: 230,
  },
}

export const LongUnbrokenError: S = {
  args: {
    items: [row(0, { last_error: "x".repeat(400) })],
    total: 1,
  },
}

export const FailedLoad: S = {
  args: { isError: true },
}

export const DiscardDialogWithMemory: S = {
  args: { items: [row(0, { memory_exists: true })], total: 1 },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getByRole("button", { name: "Discard" }))
  },
}

/** The first row's requeue never settles, so both of its buttons stay held
 *  while the second row's stay live. */
export const RequeuePending: S = {
  args: {
    items: [row(0), row(1)],
    total: 2,
    onRequeue: () => new Promise<never>(() => {}),
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement)
    await userEvent.click(canvas.getAllByRole("button", { name: "Requeue" })[0]!)
  },
}

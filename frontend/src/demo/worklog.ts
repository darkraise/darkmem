import type { WorklogEntry, Workstream } from "@/hooks/api"

const OPEN_ID = "0f0e1d2c-0000-4000-8000-000000000001"
const CLOSED_ID = "0f0e1d2c-0000-4000-8000-000000000002"

/** Two workstreams in the demo's `darkmem` project: one open plan with a
 *  checkpoint, ledger chunks and a note, and one closed plan. */
export const DEMO_WORKSTREAMS: Workstream[] = [
  {
    id: OPEN_ID,
    project: "darkmem",
    key: "work-log-increment-6",
    title: "Work-log increment 6: UI and checkpoint removal",
    client: "dr-superpowers",
    state: "open",
    closed_at: null,
    retain: false,
    properties: {
      plan_uri: "superpowers/plans/2026-09-28-work-log-increment-6.md",
      spec_uri: "superpowers/specs/2026-09-23-work-log-lane-design.md",
    },
    last_entry_at: "2026-07-24T14:10:00Z",
    created_at: "2026-07-24T09:00:00Z",
    updated_at: "2026-07-24T14:10:00Z",
  },
  {
    id: CLOSED_ID,
    project: "darkmem",
    key: "work-log-increment-5-retention",
    title: "Work-log increment 5: retention",
    client: "dr-superpowers",
    state: "closed",
    closed_at: "2026-07-23T18:00:00Z",
    retain: false,
    properties: {},
    last_entry_at: "2026-07-23T17:40:00Z",
    created_at: "2026-07-23T08:30:00Z",
    updated_at: "2026-07-23T18:00:00Z",
  },
]

function entry(
  workstream_id: string,
  seq: number,
  kind: WorklogEntry["kind"],
  body: string,
  created_at: string,
): WorklogEntry {
  return {
    // Unique across both workstreams: their ids differ only in the last digit.
    id: `${workstream_id.slice(0, 24)}${workstream_id.slice(-1)}${String(seq).padStart(11, "0")}`,
    workstream_id,
    seq,
    run_key: "claude-code:demo-run",
    kind,
    body,
    properties: {},
    created_at,
  }
}

export const DEMO_WORKLOG_ENTRIES: Record<string, WorklogEntry[]> = {
  [OPEN_ID]: [
    entry(OPEN_ID, 1, "ledger", "Task 1: projects endpoint reports work-log activity — done\n", "2026-07-24T10:05:00Z"),
    entry(OPEN_ID, 2, "note", "The Progress tab keeps its project board; the Work log replaces the checkpoint runs.", "2026-07-24T10:20:00Z"),
    entry(OPEN_ID, 3, "ledger", "Task 2: frontend project summaries — done\nTask 3: work-log hooks — done\n", "2026-07-24T12:45:00Z"),
    entry(
      OPEN_ID,
      4,
      "checkpoint",
      "## State\n\nTasks 1-3 are merged. Task 4 (the Work log panel) is next.\n\n## Next\n\n- Mount the panel under the project board\n- Keep retention and search untouched",
      "2026-07-24T14:10:00Z",
    ),
  ],
  [CLOSED_ID]: [
    entry(CLOSED_ID, 1, "ledger", "Task 1: retention sweep — done\n", "2026-07-23T11:00:00Z"),
    entry(
      CLOSED_ID,
      2,
      "checkpoint",
      "## State\n\nRetention is merged and deployed; the plan is complete.",
      "2026-07-23T17:40:00Z",
    ),
  ],
}

import type { BoardRecords, BoardView } from "@/hooks/api/use-board-api"
import builtinViews from "./board-builtin-views.json"

const PLAN_URI = "superpowers/plans/2026-09-28-work-log-increment-6.md"
const SPEC_URI = "superpowers/specs/2026-09-23-work-log-lane-design.md"

/** One register and one plan in the demo's `darkmem` project, tracked by the
 *  open demo workstream (`demo/worklog.ts`). */
const DARKMEM: Omit<BoardRecords, "project"> = {
  registers: [
    {
      document_id: "0f0e1d2c-0000-4000-8000-0000000000b1",
      uri: "superpowers/registers/2026-09-23-work-log-lane.md",
      title: "Register — separate working data from memories",
      covers: "docs/superpowers/specs/2026-09-23-work-log-lane-design.md",
      content_hash: "demo-register-hash",
      block_first: false,
      malformed: [],
      error: null,
      rows: [
        {
          number: 1,
          item: "Separate working progress from memory",
          assigned: "docs/superpowers/plans/2026-09-28-work-log-increment-6.md",
          acceptance: "worklog store and verbs live on both doors",
          state: "verify",
          raw_state: "verify",
          note: "owed: the owner's review of the Work log UI",
          note_blank: false,
          line: 8,
          plan_uri: PLAN_URI,
          plan_progress: { done: 2, total: 4, untracked: null },
        },
        {
          number: 85,
          item: "A progress board like Notion's",
          assigned:
            "docs/superpowers/specs/2026-10-13-notion-progress-board-design.md",
          acceptance: "board and table over register rows and plan tasks",
          state: "doing",
          raw_state: "doing",
          note: "-",
          note_blank: true,
          line: 92,
          plan_uri: null,
          plan_progress: null,
        },
        {
          number: 86,
          item: "Retire the T-epic board",
          assigned: "-",
          acceptance: "-",
          state: "open",
          raw_state: "open",
          note: "-",
          note_blank: true,
          line: 93,
          plan_uri: null,
          plan_progress: null,
        },
      ],
    },
  ],
  plans: [
    {
      document_id: "0f0e1d2c-0000-4000-8000-0000000000b2",
      uri: PLAN_URI,
      title: "Work-log increment 6: UI and checkpoint removal",
      content_hash: "demo-plan-hash",
      workstream: {
        id: "0f0e1d2c-0000-4000-8000-000000000001",
        key: "work-log-increment-6",
        state: "open",
      },
      other_workstreams: 0,
      spec_uri: SPEC_URI,
      untracked: null,
      orphans: [],
      error: null,
      tasks: [
        {
          number: 1,
          label: "Task 1: Work log panel",
          title: "Work log panel",
          line: 40,
          state: "done",
          raw_state: "done",
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: "9513b71",
          last_activity: "2026-07-24T10:00:00Z",
          steps: [
            { checked: false, text: "**Step 1: Write the failing test**" },
          ],
        },
        {
          number: 2,
          label: "Task 2: Activity list",
          title: "Activity list",
          line: 120,
          state: "done",
          raw_state: "done",
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: "1330d43",
          last_activity: "2026-07-24T12:00:00Z",
          steps: [],
        },
        {
          number: 3,
          label: "Task 3: Revisions sheet",
          title: "Revisions sheet",
          line: 200,
          state: "blocked",
          raw_state: "blocked",
          untracked: null,
          shared_number: false,
          blocked_reason: "Task 3: BLOCKED — waiting on an owner ruling\n",
          commit: null,
          last_activity: "2026-07-24T14:10:00Z",
          steps: [],
        },
        {
          number: 4,
          label: "Task 4: Checkpoint removal",
          title: "Checkpoint removal",
          line: 260,
          state: "todo",
          raw_state: null,
          untracked: null,
          shared_number: false,
          blocked_reason: null,
          commit: null,
          last_activity: null,
          steps: [],
        },
      ],
    },
  ],
}

export function demoBoardRecords(project: string): BoardRecords {
  return project === "darkmem"
    ? { project, ...DARKMEM }
    : { project, registers: [], plans: [] }
}

/** The server's two built-ins, read from the JSON that
 *  `tests/test_board_views_service.py` compares with `BUILTIN_VIEWS`; the demo
 *  has no saved views. */
export const DEMO_BOARD_VIEWS: BoardView[] = builtinViews.map((view) => ({
  ...view,
  project: "darkmem",
  created_at: null,
  updated_at: null,
})) as BoardView[]

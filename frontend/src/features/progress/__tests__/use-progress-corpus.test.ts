import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import type { DocumentListItem, OutlineNode, Workstream } from "@/hooks/api"

const heading = (text: string, id: string, level = 3): OutlineNode => ({
  block_id: id, level, text, order_index: null,
})

const OUTLINES = new Map<string, OutlineNode[]>([
  ["landed", [heading("Landed plan", "l0", 1), heading("Task 1: Old work", "l1")]],
  ["active", [
    heading("Active plan", "a0", 1),
    heading("Task 1: Ledgered", "a1"),
    heading("Task 2: Half ticked", "a2"),
    heading("Task 3: Untouched", "a3"),
  ]],
  ["freeform", [heading("Free-form", "f0", 1), heading("Step one", "f1", 2)]],
])
const CONTENTS = new Map<string, string>([
  ["completed", "- 2026-09-01 `docs/superpowers/plans/2026-09-01-landed-work.md` — merged\n"],
  ["active", [
    "# Active plan", "", "### Task 1: Ledgered", "- [ ] a", "",
    "### Task 2: Half ticked", "- [x] a", "- [ ] b", "",
    "### Task 3: Untouched", "- [ ] a", "",
  ].join("\n")],
])
const WORKSTREAMS = [
  { id: "ws-1", key: "active-work", properties: {} },
] as unknown as Workstream[]

vi.mock("@/hooks/api", () => ({
  useDocumentOutlines: (ids: string[]) => ({
    data: new Map(ids.map((id) => [id, OUTLINES.get(id) ?? []])),
    isLoading: false,
  }),
  useDocumentContents: (ids: string[]) => ({
    data: new Map(ids.filter((id) => CONTENTS.has(id)).map((id) => [id, CONTENTS.get(id)!])),
    isLoading: false,
  }),
  useAllWorkstreams: () => ({ data: WORKSTREAMS, isLoading: false }),
  useLedgerTexts: (ids: string[]) => ({
    data: new Map(ids.map((id) => [id, "Task 1: Ledgered — blocked\n"])),
    isLoading: false,
  }),
}))

import { useProgressCorpus } from "../use-progress-corpus"

const doc = (id: string, uri: string): DocumentListItem => ({
  id, uri, title: null, source_type: "markdown", project: "p", block_count: 1,
})

describe("useProgressCorpus with plans", () => {
  const documents = [
    doc("landed", "superpowers/plans/2026-09-01-landed-work.md"),
    doc("active", "superpowers/plans/2026-10-01-active-work.md"),
    doc("freeform", "superpowers/plans/2026-08-01-freeform.md"),
    doc("completed", "superpowers/plans/completed.md"),
  ]

  it("boards every plan task under its reference, with its status and source", () => {
    const { result } = renderHook(() => useProgressCorpus(documents, "p"))
    const corpus = result.current

    // A plan alone is enough for a board; no progress.md is filed here.
    expect(corpus.present).toBe(true)
    // Newest plan first; the free-form plan has no tasks and is left out.
    expect(corpus.epics.map((e) => e.key)).toEqual(["AW", "LW"])

    const by = Object.fromEntries(
      corpus.tasks.map((t) => [t.task.id, [t.row?.rawStatus, t.statusFrom]]),
    )
    expect(by).toEqual({
      "AW-1": ["blocked", "ledger"],
      "AW-2": ["wip", "steps"],
      "AW-3": ["todo", "steps"],
      "LW-1": ["done", "completed"],
    })
    expect(corpus.rows.get("AW-2")?.status).toBe("wip")
  })
})

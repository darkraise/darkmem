import { describe, expect, it } from "vitest"
import type { FeedCategory } from "@/features/activity/types"
import {
  categoryOfEventType,
  isDeliberatelyUntabbed,
} from "../event-taxonomy"

const FEED_CATEGORIES: FeedCategory[] = [
  "capture",
  "pipeline",
  "verification",
  "consolidation",
  "code",
]

// The cross-language guard — every EVENT_TYPES value with a live emitter
// lands in one of the two lists below — lives in
// backend/tests/test_event_taxonomy_map.py, because it has to read Python
// source to find emitters and this suite cannot. These tests only pin the
// shape on the frontend side: a tabbed value names a real tab, and no value
// is claimed by both lists at once.
describe("event-taxonomy map shape", () => {
  it("maps every tabbed event type to one of the feed's five categories", () => {
    const tabbed = [
      "created",
      "document_filed",
      "extracted",
      "sources_changed",
      "verified",
      "contradiction_scanned",
      "contradiction_dismissed",
      "citation_stale",
      "human_verdict",
      "consolidated",
      "superseded",
      "deprecated",
      "expired",
      "invalidated",
      "undone",
      "repo_registered",
      "repo_synced",
      "repo_indexed",
      "repo_hint_rejected",
    ]
    for (const eventType of tabbed) {
      const category = categoryOfEventType(eventType)
      expect(category, `${eventType} should have a tab`).not.toBeNull()
      expect(FEED_CATEGORIES).toContain(category)
    }
  })

  it("records the deliberately untabbed values as excluded, not silent", () => {
    const untabbed = [
      "maintenance_run",
      "pin_decision",
      "buffer_requeued",
      "buffer_discarded",
    ]
    for (const eventType of untabbed) {
      expect(categoryOfEventType(eventType)).toBeNull()
      expect(isDeliberatelyUntabbed(eventType)).toBe(true)
    }
  })

  it("never claims a value in both the tab map and the exclusion set", () => {
    const tabbed = [
      "created",
      "document_filed",
      "extracted",
      "sources_changed",
      "verified",
      "contradiction_scanned",
      "contradiction_dismissed",
      "citation_stale",
      "human_verdict",
      "consolidated",
      "superseded",
      "deprecated",
      "expired",
      "invalidated",
      "undone",
      "repo_registered",
      "repo_synced",
      "repo_indexed",
      "repo_hint_rejected",
    ]
    for (const eventType of tabbed) {
      expect(isDeliberatelyUntabbed(eventType)).toBe(false)
    }
  })

  it("puts a stale-article label in the consolidation tab, not verification", () => {
    // The backend guard only asks that the value be classified *somewhere*;
    // which tab is the claim. `article_stale` says the knowledge under an
    // article moved and the re-synthesis it precedes journals `superseded`
    // into this same tab — nothing about the article's grounding is asserted,
    // which is what the verification tab is for.
    expect(categoryOfEventType("article_stale")).toBe("consolidation")
    expect(isDeliberatelyUntabbed("article_stale")).toBe(false)
  })

  it("an unrecognised event type is neither tabbed nor recorded as excluded", () => {
    expect(categoryOfEventType("not_a_real_event_type")).toBeNull()
    expect(isDeliberatelyUntabbed("not_a_real_event_type")).toBe(false)
  })
})

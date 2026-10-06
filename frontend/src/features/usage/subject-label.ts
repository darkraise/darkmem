import { shortId as idTail } from "@/lib/short-id"
/**
 * Turn a usage subject id back into something a person can read.
 *
 * Every shape decoded here is one this codebase itself writes, so the decoding
 * is a reversal rather than a guess: a job run is `{key}@{started_at}`, a
 * maintenance run is `{kind}:{target}`, a chat turn is
 * `{conversation_id}:{message_id}`, and the rest are bare uuids. Anything that
 * does not match its type's shape falls back to the raw id -- a subject the
 * reader cannot identify is better than a label that says the wrong thing.
 */
export interface SubjectLabel {
  /** What the reader looks for first. */
  title: string
  /** The disambiguator: a timestamp, a target, a short id. Empty when the
   *  title already identifies the subject completely. */
  detail: string
  /** The full id, for copying and for the tooltip. Null when unattributed. */
  raw: string | null
}

const TYPE_TITLES: Record<string, string> = {
  memory: "Memory",
  batch: "Ingest batch",
  chat: "Chat turn",
  search: "Search request",
  job_run: "Job run",
  maintenance: "Maintenance",
  unattributed: "Unattributed",
}

/** Human title for a subject type on its own (a filter chip, a table group). */
export function subjectTypeTitle(subjectType: string): string {
  return TYPE_TITLES[subjectType] ?? subjectType
}

function shortId(id: string): string {
  const tail = idTail(id)
  return tail === id ? id : `…${tail}`
}

function formatStamp(iso: string): string {
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return iso
  return at.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function subjectLabel(
  subjectType: string,
  subjectId: string | null,
): SubjectLabel {
  if (!subjectId) {
    return {
      title: subjectTypeTitle(subjectType),
      // An unattributed cost is a real cost, and saying "no owner recorded" is
      // the honest version of a blank cell.
      detail: subjectType === "unattributed" ? "no owner recorded" : "",
      raw: null,
    }
  }

  if (subjectType === "job_run") {
    // `{key}@{started_at}` -- the run has no job_runs id to name it by, because
    // that row is written only after the runner returns.
    const at = subjectId.indexOf("@")
    if (at > 0) {
      return {
        title: subjectId.slice(0, at),
        detail: formatStamp(subjectId.slice(at + 1)),
        raw: subjectId,
      }
    }
  }

  if (subjectType === "maintenance") {
    // `{kind}:{target}` -- a reindex, a re-embed, a wiki generation.
    const at = subjectId.indexOf(":")
    if (at > 0) {
      return {
        title: subjectId.slice(0, at).replace(/_/g, " "),
        detail: shortId(subjectId.slice(at + 1)),
        raw: subjectId,
      }
    }
  }

  if (subjectType === "chat") {
    // `{conversation_id}:{message_id}` -- the conversation is what a reader
    // recognises; the message disambiguates the turn within it.
    const at = subjectId.indexOf(":")
    if (at > 0) {
      return {
        title: "Chat turn",
        detail: `conversation ${shortId(subjectId.slice(0, at))}`,
        raw: subjectId,
      }
    }
  }

  return {
    title: subjectTypeTitle(subjectType),
    detail: shortId(subjectId),
    raw: subjectId,
  }
}

const DAYS = [
  "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
]

/** `0` -> `12:00 AM`, `17`/`30` -> `5:30 PM`. */
function clockTime(hour: number, minute: number): string {
  const suffix = hour < 12 ? "AM" : "PM"
  const h = hour % 12 === 0 ? 12 : hour % 12
  return `${h}:${String(minute).padStart(2, "0")} ${suffix}`
}

/** A plain number, or null for anything with a list, range or step. */
function fixed(field: string): number | null {
  return /^\d+$/.test(field) ? Number(field) : null
}

/** The step count of a star-slash-N field, or null. */
function step(field: string): number | null {
  const m = /^\*\/(\d+)$/.exec(field)
  return m ? Number(m[1]) : null
}

function plural(n: number, unit: string): string {
  return n === 1 ? `Every ${unit}` : `Every ${n} ${unit}s`
}

/**
 * A human reading of a cron expression, or `null` when it cannot be read
 * confidently.
 *
 * Null rather than a best guess on purpose: this sits next to the expression
 * that actually governs when a job fires, and a wrong sentence there is worse
 * than no sentence — the reader would trust it over the cron they can see.
 * Lists, ranges and stepped ranges all return null, and the caller keeps
 * showing the raw expression regardless.
 *
 * Six-field expressions are seconds-first, Quartz-style, matching the
 * registry (CLAUDE.md, "Jobs").
 */
export function describeCron(expr: string): string | null {
  const fields = expr.trim().split(/\s+/).filter(Boolean)
  if (fields.length !== 5 && fields.length !== 6) return null

  let seconds: string | null = null
  if (fields.length === 6) seconds = fields.shift()!
  const [minute, hour, dom, month, dow] = fields as [
    string, string, string, string, string,
  ]

  // Anything this reader does not model exactly is refused outright.
  const known = (f: string) => f === "*" || fixed(f) !== null || step(f) !== null
  if (![minute, hour, dom, month, dow].every(known)) return null
  if (seconds !== null && !known(seconds)) return null
  if (month !== "*") return null

  // Sub-minute: the seconds field is the only thing that varies.
  if (seconds !== null && seconds !== "0" && minute === "*") {
    const s = step(seconds)
    if (s) return plural(s, "second")
    if (fixed(seconds) !== null) return null
  }

  const dowFixed = fixed(dow)
  const domFixed = fixed(dom)
  // One weekday and one month-day at once is a cron subtlety (OR, not AND)
  // that a one-line reading would misstate.
  if (dow !== "*" && dom !== "*") return null

  const minStep = step(minute)
  const hourStep = step(hour)
  const minFixed = fixed(minute)
  const hourFixed = fixed(hour)

  const scope =
    dowFixed !== null
      ? ` every ${DAYS[dowFixed % 7]}`
      : domFixed !== null
        ? ` on day ${domFixed} of the month`
        : " every day"

  if (minute === "*" && hour === "*") return "Every minute"
  if (minStep && hour === "*") return plural(minStep, "minute")
  if (hourStep && minFixed === 0) return plural(hourStep, "hour")

  if (minFixed !== null && hour === "*") {
    return minFixed === 0
      ? "Every hour, on the hour"
      : `Every hour at :${String(minFixed).padStart(2, "0")}`
  }

  if (minFixed !== null && hourFixed !== null) {
    return `At ${clockTime(hourFixed, minFixed)}${scope}`
  }

  return null
}

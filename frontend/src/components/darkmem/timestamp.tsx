import { relativeTime } from "@/lib/format"

/** Every timestamp a reader sees: relative in the text, absolute on hover. A
 *  value that is not a date (a demo label such as "14:10 UTC") is shown as
 *  written rather than as "NaN". */
export function Timestamp({
  iso,
  className,
}: {
  iso: string | null | undefined
  className?: string
}) {
  if (!iso) return <span className={className}>—</span>
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return <span className={className}>{iso}</span>
  return (
    <time dateTime={iso} title={date.toLocaleString()} className={className}>
      {relativeTime(iso)}
    </time>
  )
}

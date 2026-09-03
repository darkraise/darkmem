import type { ReactNode } from "react"
import Markdown from "react-markdown"
import { Separator } from "darkraise-ui/components/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"
import type { BlockRow } from "@/hooks/api"

/** Heading text is inline content, so the markdown wrapper paragraph would
 *  put a block element inside an `<h*>`. Unwrapping it keeps inline code and
 *  emphasis working without breaking the heading's own layout. */
const INLINE_ONLY = { p: ({ children }: { children?: ReactNode }) => <>{children}</> }

/** Visual weight per level. A level is a document-structure fact, so it drives
 *  the tag for accessibility and the outline; the sizes keep the reader from
 *  rendering an h1 at browser-default proportions inside a pane. */
const HEADING_CLASS: Record<number, string> = {
  1: "text-xl font-semibold tracking-tight",
  2: "text-lg font-semibold tracking-tight",
  3: "text-base font-semibold tracking-tight",
  4: "text-sm font-semibold tracking-tight",
  5: "text-sm font-medium tracking-tight",
  6: "text-muted-foreground text-sm font-medium tracking-tight",
}

/** One block, rendered by type. A pure render of the row -- no fetching, no
 *  state -- because increment 8's editor wraps exactly this component for its
 *  unfocused state.
 *
 * The spec's §2 requirement — `table` blocks render through the library
 * `table` component — is met since increment 8's Task 5a put `properties` on
 * the block read. Before that the header and alignment data increment 2
 * writes could not reach this component at all, and the deviation was
 * recorded here rather than papered over.
 */
export function BlockView({
  block,
  rows = [],
}: {
  block: BlockRow
  /** A `table` block's own data rows, which are its `parent_id` children.
   *  Passed in rather than fetched because the caller already holds the whole
   *  block list, and rendering each row as its own `<table>` -- what this
   *  component did before -- left columns unaligned across one visual table. */
  rows?: BlockRow[]
}) {
  switch (block.type) {
    case "heading": {
      // `properties.level` is what the parser wrote from the `#` count.
      // Clamped rather than trusted: a block minted by the editor may carry
      // no level, and an out-of-range one would build an invalid tag name.
      const raw = Number(block.properties?.level)
      const level = Number.isInteger(raw) && raw >= 1 && raw <= 6 ? raw : 2
      const Tag = `h${level}` as "h1" | "h2" | "h3" | "h4" | "h5" | "h6"
      return (
        <Tag className={HEADING_CLASS[level]}>
          <Markdown components={INLINE_ONLY}>{block.text}</Markdown>
        </Tag>
      )
    }
    case "code":
      return (
        <pre className="border-border bg-muted/40 overflow-x-auto rounded-md border p-3 font-mono text-sm whitespace-pre-wrap">
          {block.text}
        </pre>
      )
    case "quote":
      return (
        <blockquote className="border-primary/40 text-muted-foreground border-l-2 pl-3 text-sm italic">
          <Markdown>{block.text}</Markdown>
        </blockquote>
      )
    case "list":
      return (
        <div className="flex gap-2 text-sm">
          <span aria-hidden>•</span>
          <Markdown>{block.text}</Markdown>
        </div>
      )
    case "divider":
      // A thematic break carries no text: the rule IS the block. Rendered as
      // the library separator rather than a styled empty paragraph, which is
      // what an unknown type would have fallen through to.
      return <Separator className="my-1" />
    case "table": {
      // The header row is the table block's own text; its data rows are
      // separate `table_row` children, so this renders the head only.
      const header = (block.properties?.header as string[] | undefined) ?? []
      if (header.length === 0) {
        return <div className="text-muted-foreground font-mono text-sm">{block.text}</div>
      }
      return (
        <Table>
          <TableHeader>
            <TableRow>
              {header.map((cell, i) => (
                <TableHead key={i}>{cell}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          {rows.length > 0 ? (
            <TableBody>
              {rows.map((row) => {
                const cells =
                  (row.properties?.cells as string[] | undefined) ?? []
                return (
                  <TableRow key={row.block_id}>
                    {cells.map((cell, i) => (
                      <TableCell key={i}>{cell}</TableCell>
                    ))}
                  </TableRow>
                )
              })}
            </TableBody>
          ) : null}
        </Table>
      )
    }
    case "table_row": {
      // Reached only when this row arrives without its table -- a `block_ids`
      // drill-down scopes strictly, so that is legitimate and dropping the
      // row would silently lose content. In a whole-document read the table
      // adopts its rows above and this case never runs.
      const cells = (block.properties?.cells as string[] | undefined) ?? []
      if (cells.length === 0) {
        return <div className="font-mono text-sm">{block.text}</div>
      }
      return (
        <Table>
          <TableBody>
            <TableRow>
              {cells.map((cell, i) => (
                <TableCell key={i}>{cell}</TableCell>
              ))}
            </TableRow>
          </TableBody>
        </Table>
      )
    }
    default:
      return (
        <div className="text-sm leading-relaxed">
          <Markdown>{block.text}</Markdown>
        </div>
      )
  }
}

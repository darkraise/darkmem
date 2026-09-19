import { Square, SquareCheck } from "lucide-react"
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
import { CodeBlock, InlineMarkdown } from "@/components/markdown"

/** Visual weight per level. A level is a document-structure fact, so it drives
 *  the tag for accessibility and the outline; the sizes keep the reader from
 *  rendering an h1 at browser-default proportions inside a pane.
 *
 * Every level below 3 used to land on `text-sm`, which is the body size --
 * so an h4, an h5 and a paragraph were the same size and weight, and a
 * document's structure below the second level was invisible. Each level now
 * steps, and h6 changes KIND rather than shrinking below the body text. */
const HEADING_CLASS: Record<number, string> = {
  1: "text-2xl font-semibold tracking-tight",
  2: "text-xl font-semibold tracking-tight",
  3: "text-lg font-semibold tracking-tight",
  4: "text-base font-semibold tracking-tight",
  5: "text-sm font-semibold tracking-tight",
  6: "text-muted-foreground font-mono text-xs font-semibold tracking-wide uppercase",
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
          <InlineMarkdown>{block.text}</InlineMarkdown>
        </Tag>
      )
    }
    case "code":
      // `overflow-x-auto` and `whitespace-pre-wrap` used to be set together,
      // which cannot both apply: the wrap means the box never overflows, so
      // long lines broke mid-token instead of scrolling. CodeBlock scrolls.
      return (
        <CodeBlock
          code={block.text}
          language={block.properties?.language as string | undefined}
        />
      )
    case "html":
      // Escaped source, never live markup. The markdown pipeline carries no
      // `rehype-raw`, so adding one to make <img>/<details> render is the
      // first place an imported file executes script under the operator's
      // session cookie. Live HTML is a separate owner decision behind
      // `rehype-sanitize` (2026-09-07 spec §12).
      return <CodeBlock code={block.text} language="html" />
    case "quote":
      return (
        <blockquote className="border-primary/40 text-muted-foreground border-l-2 pl-3 text-sm italic">
          <InlineMarkdown>{block.text}</InlineMarkdown>
        </blockquote>
      )
    case "list": {
      // A bullet unless the parser recorded an ordered marker. Every document
      // filed before increment 5 carries no list properties at all, so the
      // fallback is what those render until they are reparsed -- the same
      // bullet they have always shown, not a wrong number.
      // `marker` is the full marker as spelled ("-" or "3."), the convention
      // `block_serializer` owns; `ordered` and `number` are the parser's
      // explicit restatement of it. Prefer the marker so one string decides
      // what is rendered and what a round-trip writes back.
      const marker = block.properties?.marker
      const ordered =
        block.properties?.ordered === true ||
        (typeof marker === "string" && /^\d+[.)]$/.test(marker))
      const label = ordered && typeof marker === "string" ? marker : "\u2022"

      // A GFM task item. `remark-gfm` only builds a checkbox inside a real
      // `<ul>`, and this surface renders one row per block with no list
      // wrapper, so the `[ ]` / `[x]` reaches the row as literal text. It is
      // read here rather than left to render as two brackets and a letter.
      const task = /^\[([ xX])\]\s+/.exec(block.text)
      if (task) {
        const checked = task[1] !== " "
        return (
          <div className="flex gap-2 text-sm leading-relaxed">
            {checked ? (
              <SquareCheck
                aria-hidden
                className="text-primary-text mt-[3px] size-3.5 shrink-0"
              />
            ) : (
              <Square
                aria-hidden
                className="text-muted-foreground mt-[3px] size-3.5 shrink-0"
              />
            )}
            <div
              className={`min-w-0 flex-1 ${checked ? "text-muted-foreground" : ""}`}
            >
              <InlineMarkdown>{block.text.slice(task[0].length)}</InlineMarkdown>
            </div>
          </div>
        )
      }

      return (
        <div className="flex gap-2 text-sm leading-relaxed">
          <span
            aria-hidden
            className={
              ordered
                ? "text-muted-foreground shrink-0 tabular-nums"
                : "text-muted-foreground shrink-0"
            }
          >
            {label}
          </span>
          <div className="min-w-0 flex-1">
            <InlineMarkdown>{block.text}</InlineMarkdown>
          </div>
        </div>
      )
    }
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
          <InlineMarkdown>{block.text}</InlineMarkdown>
        </div>
      )
  }
}

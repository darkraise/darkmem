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
export function BlockView({ block }: { block: BlockRow }) {
  switch (block.type) {
    case "heading":
      return (
        <h3 className="text-base font-semibold tracking-tight">{block.text}</h3>
      )
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
        </Table>
      )
    }
    case "table_row": {
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

import Markdown from "react-markdown"
import { Separator } from "darkraise-ui/components/separator"
import { cn } from "darkraise-ui/lib"
import type { BlockRow } from "@/hooks/api"

/** One block, rendered by type. A pure render of the row -- no fetching, no
 *  state -- because increment 8's editor wraps exactly this component for its
 *  unfocused state.
 *
 * **Stated deviation from spec §2 / §4.1** (cross-plan review M-7): the spec
 * says `table` blocks render through the library `table` component. They do
 * not here, and the reason is a gap this increment cannot close on its own --
 * increment 2 writes the `{header, alignments}` / `{cells}` properties a real
 * table needs, but `properties` is on neither read surface, so the data never
 * reaches this component. `table` / `table_row` therefore render as the flat
 * cell-joined text the door actually serves. Increment 8's Task 5a adds
 * `properties` to the block read; when it lands, take the library component
 * here and strike this note. Do not invent the properties client-side.
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
    case "table":
    case "table_row":
      return (
        <div
          className={cn(
            "font-mono text-sm",
            block.type === "table" && "text-muted-foreground font-semibold",
          )}
        >
          {block.text}
        </div>
      )
    default:
      return (
        <div className="text-sm leading-relaxed">
          <Markdown>{block.text}</Markdown>
        </div>
      )
  }
}

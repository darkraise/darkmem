import { useEffect, useState } from "react"
import { cn } from "darkraise-ui/lib"
import type { PageEditorInstance } from "./lib/editor-schema"

interface Heading {
  id: string
  level: number
  text: string
}

function headingsOf(editor: PageEditorInstance): Heading[] {
  const out: Heading[] = []
  const walk = (blocks: PageEditorInstance["document"]) => {
    for (const block of blocks) {
      if (block.type === "heading") {
        const text = (block.content as { type: string; text?: string }[])
          .map((part) => (part.type === "text" ? (part.text ?? "") : ""))
          .join("")
        out.push({ id: block.id, level: Number((block.props as { level?: number }).level ?? 1), text })
      }
      walk(block.children)
    }
  }
  walk(editor.document)
  return out
}

/** The page's headings, read from the live document so an edit shows at
 *  once; a click scrolls the heading into view. */
export function PageOutline({ editor }: { editor: PageEditorInstance }) {
  const [headings, setHeadings] = useState(() => headingsOf(editor))
  useEffect(() => editor.onChange(() => setHeadings(headingsOf(editor))), [editor])
  if (headings.length === 0) return null
  return (
    <nav aria-label="Page outline" className="text-sm">
      <p className="text-muted-foreground mb-2 text-xs font-medium tracking-wide uppercase">Outline</p>
      <ul className="space-y-1">
        {headings.map((heading) => (
          <li key={heading.id} style={{ paddingLeft: `${(heading.level - 1) * 0.75}rem` }}>
            <button
              type="button"
              className={cn("text-muted-foreground hover:text-foreground w-full truncate text-left")}
              onClick={() =>
                document
                  .querySelector(`.bn-block-outer[data-id="${heading.id}"]`)
                  ?.scrollIntoView({ block: "start", behavior: "smooth" })
              }
            >
              {heading.text || "Untitled heading"}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}

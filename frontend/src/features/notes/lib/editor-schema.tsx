import {
  BlockNoteSchema,
  type BlockNoteEditor,
  createHeadingBlockSpec,
  defaultBlockSpecs,
  defaultInlineContentSpecs,
  defaultStyleSpecs,
} from "@blocknote/core"
import { createReactBlockSpec, createReactInlineContentSpec } from "@blocknote/react"
import { CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import { CALLOUT_VARIANTS, type CalloutVariant } from "./block-properties"

const CALLOUT_TONE: Record<CalloutVariant, string> = {
  info: "border-info/40 bg-info/10 [&>svg]:text-info-text",
  warning: "border-warning/40 bg-warning/10 [&>svg]:text-warning-text",
  error: "border-destructive/40 bg-destructive/10 [&>svg]:text-destructive",
  success: "border-success/40 bg-success/10 [&>svg]:text-success-text",
}

const CALLOUT_ICON: Record<CalloutVariant, typeof Info> = {
  info: Info,
  warning: TriangleAlert,
  error: CircleAlert,
  success: CircleCheck,
}

export const createCallout = createReactBlockSpec(
  {
    type: "callout",
    propSchema: { variant: { default: "info", values: CALLOUT_VARIANTS } },
    content: "inline",
  },
  {
    render: ({ block, contentRef }) => {
      const Icon = CALLOUT_ICON[block.props.variant]
      return (
        <div
          className={cn(
            "flex w-full items-start gap-2 rounded-md border px-3 py-2",
            CALLOUT_TONE[block.props.variant],
          )}
          data-variant={block.props.variant}
        >
          <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <div ref={contentRef} className="text-foreground min-w-0 flex-1" />
        </div>
      )
    },
  },
)

export const createRaw = createReactBlockSpec(
  {
    type: "raw",
    propSchema: { source: { default: "" } },
    content: "none",
  },
  {
    render: ({ block }) => (
      <pre className="bg-muted/40 text-muted-foreground w-full overflow-x-auto rounded px-2 py-1 font-mono text-xs">
        {block.props.source}
      </pre>
    ),
  },
)

export const rawInline = createReactInlineContentSpec(
  {
    type: "rawInline",
    propSchema: { source: { default: "" } },
    content: "none",
  },
  {
    render: ({ inlineContent }) => (
      <code className="bg-muted rounded px-1 font-mono text-xs">{inlineContent.props.source}</code>
    ),
  },
)

export const pageSchema = BlockNoteSchema.create({
  blockSpecs: {
    paragraph: defaultBlockSpecs.paragraph,
    heading: createHeadingBlockSpec({ levels: [1, 2, 3, 4, 5, 6], allowToggleHeadings: false }),
    bulletListItem: defaultBlockSpecs.bulletListItem,
    numberedListItem: defaultBlockSpecs.numberedListItem,
    checkListItem: defaultBlockSpecs.checkListItem,
    toggleListItem: defaultBlockSpecs.toggleListItem,
    quote: defaultBlockSpecs.quote,
    codeBlock: defaultBlockSpecs.codeBlock,
    table: defaultBlockSpecs.table,
    divider: defaultBlockSpecs.divider,
    callout: createCallout(),
    raw: createRaw(),
  },
  inlineContentSpecs: {
    text: defaultInlineContentSpecs.text,
    link: defaultInlineContentSpecs.link,
    rawInline,
  },
  styleSpecs: {
    bold: defaultStyleSpecs.bold,
    italic: defaultStyleSpecs.italic,
    strike: defaultStyleSpecs.strike,
    code: defaultStyleSpecs.code,
  },
})

export type PageSchema = typeof pageSchema
export type PageEditorBlock = typeof pageSchema.Block
export type PagePartialBlock = typeof pageSchema.PartialBlock
export type PageEditorInstance = BlockNoteEditor<
  typeof pageSchema.blockSchema,
  typeof pageSchema.inlineContentSchema,
  typeof pageSchema.styleSchema
>

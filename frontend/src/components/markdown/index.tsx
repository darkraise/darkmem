import type { ComponentProps, ReactNode } from "react"
import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeHighlight from "rehype-highlight"

/**
 * The app's markdown layer -- one pipeline, one set of link semantics, one
 * place to change either.
 *
 * Three surfaces render markdown: the chat transcript, the prompt viewer and
 * the document reader. The first two shared `.md-prose`; the reader called
 * bare `<Markdown>` and got Tailwind's preflight instead, which is why its
 * links were invisible, its `strong` unweighted and its `~~strikethrough~~`
 * literal text. They now share this module.
 *
 * `remark-gfm` is what makes strikethrough, autolinks and task lists real
 * rather than raw characters; `rehype-highlight` colours fenced code against
 * the `.hljs-*` tokens defined in `globals.css`.
 */

const PLUGINS = {
  remarkPlugins: [remarkGfm],
  rehypePlugins: [rehypeHighlight],
}

/** An external link opens away from the app and cannot reach back through
 *  `window.opener`. In-page anchors (the reader's outline) must NOT get
 *  this treatment -- a new tab for `#block-id` navigates away from the
 *  document the reader is showing. */
function Anchor({ href, children, ...rest }: ComponentProps<"a">) {
  const external = typeof href === "string" && /^https?:/i.test(href)
  return (
    <a
      href={href}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      {...rest}
    >
      {children}
    </a>
  )
}

const SHARED: Components = { a: Anchor }

/** Block-level markdown: a whole document, message or prompt. */
export function AppMarkdown({
  children,
  components,
  className,
}: {
  children: string
  /** Extra element overrides, merged over the shared ones. Chat passes its
   *  citation-reference renderers through here. */
  components?: Components
  className?: string
}) {
  return (
    <div className={className ? `md-prose ${className}` : "md-prose"}>
      <ReactMarkdown {...PLUGINS} components={{ ...SHARED, ...components }}>
        {children}
      </ReactMarkdown>
    </div>
  )
}

/** Markdown's paragraph wrapper, removed.
 *
 * An inline surface puts this content inside an `<h2>`, an `<li>` or a flex
 * row, where a `<p>` is either invalid or a layout break. */
const UNWRAP_PARAGRAPH: Components = {
  p: ({ children }: { children?: ReactNode }) => <>{children}</>,
}

/**
 * Inline-only markdown, for a caller that owns its own block layout.
 *
 * The document reader is that caller: it renders one row per block and the
 * markdown inside a row is always inline. `.md-inline` styles exactly the
 * inline elements and nothing else, so it cannot fight the row's own spacing.
 */
export function InlineMarkdown({ children }: { children: string }) {
  return (
    <span className="md-inline">
      <ReactMarkdown
        {...PLUGINS}
        components={{ ...SHARED, ...UNWRAP_PARAGRAPH }}
      >
        {children}
      </ReactMarkdown>
    </span>
  )
}

/** A fence long enough to survive the content.
 *
 * A code block's stored text is raw source, so it is rendered by wrapping it
 * back into a fence and letting the same pipeline highlight it. Source
 * containing its own ``` run would close the fence early and spill the rest
 * of the block into the document as prose -- so the fence is always longer
 * than the longest backtick run inside. */
export function fenceFor(code: string): string {
  const longest = Math.max(
    0,
    ...[...code.matchAll(/`+/g)].map((m) => m[0].length),
  )
  return "`".repeat(Math.max(3, longest + 1))
}

/**
 * A fenced code block with its language labelled and highlighted.
 *
 * The parser has always stored `properties.language` from the fence's info
 * string; nothing rendered it until now.
 */
export function CodeBlock({
  code,
  language,
}: {
  code: string
  language?: string | null
}) {
  const fence = fenceFor(code)
  const info = language?.trim() ? language.trim().split(/\s+/)[0] : ""

  return (
    <div className="border-border relative overflow-hidden rounded-md border">
      {info && (
        <span className="text-muted-foreground bg-muted/60 absolute top-0 right-0 rounded-bl px-2 py-0.5 font-mono text-[10px] tracking-wide lowercase">
          {info}
        </span>
      )}
      {/* `md-prose` styles the `pre`; the highlighter fills in the tokens. */}
      <div className="md-prose md-code">
        <ReactMarkdown {...PLUGINS}>
          {`${fence}${info}\n${code}\n${fence}`}
        </ReactMarkdown>
      </div>
    </div>
  )
}

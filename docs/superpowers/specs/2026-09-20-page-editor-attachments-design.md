# Page editor: images and files — design

Date: 2026-09-20. Sub-project 3 of the Notion import programme
(`docs/superpowers/specs/2026-09-19-notion-import-design.md`, §5.2-5.3, the
programme's increment 2). Sub-projects 1 and 2 shipped the storage, routes,
cleanup job and backups.

## 1. Goal

Let the operator put an image or a file into a page: uploaded from the editor
by paste, drag-drop or the slash menu, rendered in place, and stored as
ordinary markdown in the block's own text.

Frontend only. No route, no schema column, no event type and no backend module
changes, so the guards leg is not implicated and `docs/two-door-parity.md` is
untouched.

Out of scope: captions, image resizing, alignment and background colour (§5);
an inline thumbnail for an image sitting inside other text (§6); deleting an
attachment by hand; Playwright coverage (§8).

## 2. Rulings

| Question | Ruling |
|---|---|
| Which image URLs become an `image` block | **Any** — an attachment URL or an external one |
| Which link paragraphs become a `file` block | **Attachment URLs only** |
| An image inside other text | Stays a `rawInline` atom, rendered as today's code chip |
| Resize handles | Hidden in CSS |
| Block specs | BlockNote's built-ins, not custom ones |

The image ruling buys a consistent round trip: whatever the editor can create,
it reads back the same way. Restricting to attachment URLs would have meant a
pasted markdown image, or one embedded through the file panel, saving fine and
then reading back as a code chip — rendering differently a moment after it was
written. The cost accepted is that an external image in a note loads from a
third-party host when the page opens.

The link ruling is the asymmetric half and is not an oversight. `![alt](url)`
is unambiguously an image; `[text](url)` alone in a paragraph is an ordinary
link, and turning every one of those into a file-download block would be
wrong. So the `file` block is reached only from an upload or from a URL that
is already an attachment.

## 3. Schema

`lib/editor-schema.tsx` adds BlockNote's built-in specs to
`pageSchema.blockSpecs`:

```ts
file: defaultBlockSpecs.file,
image: defaultBlockSpecs.image,
```

**`file` must come before `image`, and the `file` key must be spelled exactly
that.** Both are properties of BlockNote's drop/paste handler, not style:

- The handler iterates `Object.values(schema.blockSpecs)` and assigns the
  block type of **every** spec whose `meta.fileBlockAccept` matches the
  dropped file's MIME type, so the **last** match wins. `file` declares
  `*/*` and `image` declares `image/*`; reversed, every dropped PNG would
  land on `file`.
- `"file"` is the handler's hardcoded fallback type when nothing matches. A
  schema without a block of that exact name drops non-image files into a
  block type that does not exist.

`video` and `audio` stay out of the schema, so an mp4 or an mp3 becomes a
`file`.

## 4. Mapping

### 4.1 The detector and its inverse

Two new exports in `lib/inline-markdown.ts`, which is the module that owns
mdast:

```ts
export function asStandaloneFile(
  text: string,
): { kind: "image" | "link"; url: string; name: string } | null

export function fileMarkdown(kind: "image" | "link", url: string, name: string): string
```

`asStandaloneFile` parses `text` with the module's existing `fromMarkdown`
configuration and accepts it only when the result is exactly one paragraph
holding exactly one node — an `image`, or a `link` whose URL is an attachment
URL — spanning the whole string, with no title.

**It then emits the candidate back through `fileMarkdown` and returns `null`
unless the result is byte-identical to its input.** This is the emit-and-verify
discipline `emitInline` already uses, and it is what makes the round trip a
property of the code rather than an argument about escaping: an alt text
holding a bracket, a URL holding parentheses or a spelling the markdown writer
normalises all fail the check and fall back to staying a `rawInline` atom.
Without it, `canonicalTree` would stop being a fixed point for those spellings
and the save engine would rewrite the block on every load.

`fileMarkdown` builds an mdast `image` or `link` node and serialises it with
the same `toMarkdown` call `emitInline` uses, so escaping is decided in one
place.

### 4.2 The attachment-URL predicate

A new module `lib/attachments.ts` owns the one spelling of the attachment URL:

```ts
export const ATTACHMENT_URL = /^\/api\/v1\/pages\/attachments\/[0-9a-f-]{36}$/
export function isAttachmentUrl(url: string): boolean
```

The character class matches the backend cleanup job's own regexp
(`page_attachment_cleanup`, programme spec §3.6), so what the editor writes is
what that scan finds.

### 4.3 Reading — `toEditorBlocks`

A server block of type `paragraph` whose `text` `asStandaloneFile` accepts
becomes an editor block instead of a paragraph:

- `kind: "image"` → `{type: "image", props: {url, name}}`
- `kind: "link"` → `{type: "file", props: {url, name}}`

`name` carries the markdown's alt text (image) or link text (link). Every
other prop the built-in specs define — `caption`, `previewWidth`,
`showPreview`, `textAlignment`, `backgroundColor` — is left at its default and
never read (§5).

Every other paragraph is unchanged, so an image among other text stays one
`rawInline` atom and renders as today's code chip.

### 4.4 Writing — `toSyncTree`

```
case "image": paragraph, text = fileMarkdown("image", url, name)
case "file":  paragraph, text = fileMarkdown("link",  url, name)
```

Both carry `properties: null`, like every other paragraph.

**A block of either type whose `url` is the empty string is omitted from the
tree entirely** — not pushed, not recursed into. One rule covers two states
that are the same thing from the server's side:

- the placeholder BlockNote inserts when the block is created from the slash
  menu, before a file is chosen;
- the block left behind by a failed upload (§7).

Nothing is persisted for either, the editor keeps showing its add-file button,
and the block becomes a real paragraph the moment a URL lands. Neither type
holds children (`content: "none"`), so the omission orphans nothing.

### 4.5 Why the text, and not a block type

The URL lives in the paragraph's own `text`, which is what the storage
sub-project's cleanup job requires: its reference scan reads `blocks.text`
only, and a carried follow-up from that sub-project asks this one to pin the
coupling with a test (§8). It is also programme spec §3.5's ruling — no new
block type and no change to `blocks`.

## 5. Affordances

- **Slash menu.** `SLASH_KEYS` in `use-page-editor.ts` gains `image` and
  `file`. Both are BlockNote's own item keys.
- **Resize.** `page-editor.css` hides `.bn-resize-handle`. With
  `display: none` the handle takes no pointer events, so `previewWidth` — for
  which markdown has no place — can never move off its default. A vitest
  assertion on the rendered markup catches a BlockNote class rename.
- **Caption, alignment, background colour.** No work. `page-editor.tsx`
  already passes `formattingToolbar={false}` and renders five explicit buttons
  (four text styles and the link button), so no affordance that sets those
  props exists in this editor.

## 6. Rejected: the inline thumbnail

Programme spec §5.2 asked that a `rawInline` atom render a thumbnail when its
target is an attachment image — the case of an image inside other text, which
cannot become a block. Cut: it adds a second image-rendering path to build and
test for a case the import does not produce (Notion writes images as their own
paragraph). It can be added later without touching anything in this design.

## 7. Upload

`lib/attachments.ts`:

```ts
export async function uploadAttachment(pageId: string, file: File): Promise<string>
```

`POST /pages/{pageId}/attachments` with the raw `File` as the body,
`X-Filename` percent-encoded, and `Content-Type` overridden off the shared
fetch helper's JSON default. Returns the response's `url`.

`usePageEditor` takes an optional `pageId` and configures BlockNote's
`uploadFile` **only when it has one**, so demo mode — which passes none and
renders a non-editable editor — has no upload code to fire at all.

**On failure the hook catches, raises a `sonner` toast carrying the server's
own message, and resolves the empty string.** It does not reject. BlockNote
calls `uploadFile` from a drop handler that does not await it, so a rejection
is an unhandled promise rejection; and the block it already inserted is then
updated with an empty URL, which §4.4 never persists. The operator sees the
refusal (413 over `attachment_max_bytes`, 403 on a read-only instance) and a
placeholder they can retry on.

The paste path can convert the empty paragraph at the cursor into the
placeholder rather than inserting a new block. That is BlockNote's behaviour,
it only ever consumes an empty paragraph, and it is left alone.

## 8. Known limits

- The file panel's "Embed URL" tab can point a **`file`** block at an external
  URL. It saves as `[name](url)` and reads back as an ordinary paragraph link:
  the text and the link survive, the rendering changes. Images are unaffected,
  since any image URL is a block (§2).
- An external image loads from a third-party host when the page opens.
- A caption or a resize set through some future BlockNote affordance would be
  silently lost on reload, because markdown carries neither. Today no such
  affordance is reachable (§5).

## 9. Testing

**vitest only.** No backend test, no Playwright: an end-to-end upload needs a
writable attachments directory on the disposable stack in
`backend/scripts/e2e/run_playwright_e2e.py`, which sub-project 4 needs for the
import run anyway and can carry.

- `block-mapping`: an image paragraph and an attachment-link paragraph in both
  directions; `canonicalTree` a fixed point over both; a standalone external
  link staying a paragraph; an image mid-sentence staying a `rawInline` atom;
  an empty-URL `image` and `file` block omitted from the tree; and **the
  emitted paragraph text matching the cleanup job's regexp verbatim** (§4.5).
- `inline-markdown`: a table of spellings through `asStandaloneFile` and
  `fileMarkdown`, including the ones the detector must reject — a bracket in
  the alt text, parentheses in the URL, a link title, trailing text.
- `attachments` (new file): `uploadAttachment` sends the raw body and the
  percent-encoded `X-Filename`; the error path toasts and resolves `""`.
- `use-page-editor`: `uploadFile` absent without a `pageId`; the slash menu
  offers `image` and `file`; the schema lists `file` before `image`.
- `page-editor`: the resize handle is hidden.

## 10. Documentation

- `CLAUDE.md`: one sentence in the `/notes` paragraph — the editor renders and
  uploads images and files, stored as markdown in the block's text.
- `CHANGELOG.md`: rides with the release carrying the import (sub-project 4).

# Page editor: images and files — design

Date: 2026-09-20. Revision 2, after an adversarial review (11 findings; the
nine that held are folded in below and §12 records the two that did not).
Sub-project 3 of the Notion import programme
(`docs/superpowers/specs/2026-09-19-notion-import-design.md`, §5.2-5.3, the
programme's increment 2). Sub-projects 1 and 2 shipped the storage, routes,
cleanup job and backups.

## 1. Goal

Let the operator put an image or a file into a page: uploaded from the editor
by paste, drag-drop or the slash menu, rendered in place, and stored as
ordinary markdown in the block's own text.

Almost all of the work is in `frontend/src/features/notes/`. **One backend
change rides with it** — the content-security-policy's `img-src` (§6) — which
means the redeploy rule applies and `backend/tests/test_edge_response_policy.py`
is part of the verification. No route and no MCP tool is registered, so the
guards leg is not triggered and `docs/two-door-parity.md` is untouched: the two
attachment routes already carry their `content_surfaces.py` classification and
their `pages.attachments` single-door row from sub-project 1.

Out of scope: captions, image resizing, alignment and background colour (§5);
an inline thumbnail for an image sitting inside other text (§9); deleting an
attachment by hand.

## 2. Rulings

| Question | Ruling |
|---|---|
| Which image URLs become an `image` block | **Any** — an attachment URL or an external one |
| The CSP that blocks external images | **Widened**, `img-src 'self' data: https:` (§6) |
| Which link paragraphs become a `file` block | **Attachment URLs only** |
| An image inside other text | Stays a `rawInline` atom, rendered as today's code chip |
| Resize handles | Hidden in CSS |
| Block specs | BlockNote's built-ins, not custom ones |

The image ruling buys a consistent round trip: whatever the editor can create,
it reads back the same way. Restricting to attachment URLs would have meant a
pasted markdown image, or one embedded through the file panel, saving fine and
then reading back as a code chip — rendering differently a moment after it was
written.

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

**The `file` key must be spelled exactly that**: `"file"` is the hardcoded
fallback block type in BlockNote's drop/paste handler when no spec's
`meta.fileBlockAccept` matches the dropped MIME type. A schema without a block
of that name drops non-image files into a type that does not exist.

Their **order does not matter**, contrary to the obvious reading of that
handler. It does assign the type of every matching spec in iteration order, so
the last match would win — but the installed matcher's wildcard branch
compares the two type halves, so the `file` spec's `*/*` matches nothing
except an exactly equal type. A PNG matches only `image/*`. The order is left
as written above for legibility, and a test pins the *behaviour* (a dropped
PNG becomes an `image`, a dropped PDF a `file`) rather than the order.

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
configuration and accepts it only when all of these hold:

1. the result is exactly one paragraph holding exactly one node, spanning the
   whole string, with no title;
2. that node is an `image`, or a `link` whose URL is an attachment URL (§4.2);
3. **the URL is not empty**;
4. re-emitting the candidate through `fileMarkdown` reproduces `text` byte for
   byte.

Rule 4 is the emit-and-verify discipline `emitInline` already uses. It decides
the spellings the markdown writer would normalise; it is **not** a bracket or
parenthesis filter, since the writer escapes both labels and destinations, so
`![a\[b\]](…)` and `![a](…/a\(b\).png)` are canonical and do round-trip. The
tests must distinguish a canonical escaped spelling from one the writer
rewrites.

**Rule 3 is the one that prevents silent content loss, and it is not
redundant with rule 4.** A stored paragraph `![draft]()` parses to one image
with an empty URL and re-emits byte-identically, so it passes rules 1, 2 and
4. Without rule 3 it would become an image block and then be dropped by §4.4,
and the editor would silently lose text the server still holds. Idempotence is
not preservation: an empty tree is a perfectly good fixed point. With rule 3
that paragraph stays a `rawInline` atom and survives.

Rule 3 also gives §4.4 its scope: **no block read from the server can ever
carry an empty URL**, so the omission rule there only ever applies to a block
the editor itself created.

`fileMarkdown` builds an mdast `image` or `link` node and serialises it with
the same `toMarkdown` call `emitInline` uses, so escaping is decided in one
place.

### 4.2 The attachment-URL predicate

A new module `lib/attachments.ts` owns the one spelling of the attachment URL:

```ts
export const ATTACHMENT_URL =
  /^\/api\/v1\/pages\/attachments\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/
export function isAttachmentUrl(url: string): boolean
```

**This is the cleanup job's own pattern, character for character**
(`backend/app/services/page_attachment_cleanup.py:78`) — a real UUID shape,
and case-insensitive because that job deliberately retains an uppercase URL
(`backend/tests/test_page_attachment_cleanup.py:100`). A loose class such as
`[0-9a-f-]{36}` is wrong in both directions: it rejects uppercase URLs the job
keeps alive, and accepts malformed values such as thirty-six hyphens that the
GET route would 422. A vitest test asserts the two patterns agree by reading
the backend file.

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
tree entirely** — not pushed, not recursed into. By §4.1 rule 3 such a block
can only have come from the editor, never from stored text, and it is always
one of two transient states that mean the same thing from the server's side:

- the placeholder BlockNote inserts when the block is created from the slash
  menu, before a file is chosen;
- the block left behind by a failed upload (§7.2).

Nothing is persisted for either, and the block becomes a real paragraph the
moment a URL lands. Neither type can hold children **because the nesting guard
refuses to give them any** (`lib/nesting-guard.ts` allows children only under
the four editor container types) — not because their content type is `"none"`,
which does not by itself forbid a child group. So the omission orphans
nothing, and a test asserts the guard covers both new types.

An upload in flight is **not** represented in this tree at all, which is what
§7.3 is about.

### 4.5 Why the text, and not a block type

The URL lives in the paragraph's own `text`, which is what the storage
sub-project's cleanup job requires: its reference scan reads `blocks.text`
only, and a carried follow-up from that sub-project asks this one to pin the
coupling with a test (§10). It is also programme spec §3.5's ruling — no new
block type and no change to `blocks`.

## 5. Affordances

- **Slash menu.** `SLASH_KEYS` in `use-page-editor.ts` gains `image` and
  `file`. Both are BlockNote's own item keys.
- **Resize.** `page-editor.css` hides `.bn-resize-handle`. With
  `display: none` the handle takes no pointer events, so `previewWidth` — for
  which markdown has no place — can never move off its default. A vitest
  assertion on the rendered markup catches a BlockNote class rename.
- **Download.** `page-editor.tsx`'s formatting toolbar gains
  `<FileDownloadButton />` from `@blocknote/react`. Without it an uploaded
  file is unreachable: the built-in file renderer draws an inert filename and
  icon, and the anchor that opens the URL exists only in exported HTML. The
  button renders only for a file or image block, so the toolbar is unchanged
  for text.
- **Caption and alignment.** No work. The toolbar is already
  `formattingToolbar={false}` plus five explicit buttons, so the caption and
  alignment buttons never render.
- **Background colour is reachable and is dropped, and that is pre-existing.**
  The side menu renders by default and its drag-handle menu carries a colour
  picker that writes `backgroundColor`. `toSyncTree` already pushes
  `properties: null` for every paragraph, so a paragraph's background colour
  is silently lost on reload today. An image block inherits exactly that
  behaviour and no worse. Recorded here so the next reader does not take it
  for a defect this change introduced; closing it is its own task.

## 6. The content-security-policy

External images need `img-src` widened. The value is declared twice and a test
asserts the two agree character for character
(`backend/tests/test_edge_response_policy.py`, which parses `nginx.conf` and
compares), so both move together:

- `backend/app/main.py`, `SECURITY_HEADERS`
- `frontend/nginx.conf`

`img-src 'self' data:` becomes `img-src 'self' data: https:`. **`http:` is
deliberately not added**: the LAN deployment serves over plain HTTP, and
allowing cleartext image loads would let a pasted note beacon a third party
over the wire in the clear. An `http://` image stays blocked, which reads as a
broken image.

The stated cost, which is the whole of what the widening buys and what it
gives up: any `https://` image URL in a note is fetched by the browser when
the page opens, so it reaches a third-party host carrying the operator's IP
and a referrer. `referrer-policy: strict-origin-when-cross-origin` is already
set and bounds the referrer to the origin.

The comment above `SECURITY_HEADERS` explains that these values are nginx's,
moved rather than retuned. This is a retune, so it gets a sentence saying so
and naming the reason.

## 7. Upload

### 7.1 The happy path

`lib/attachments.ts`:

```ts
export async function uploadAttachment(pageId: string, file: File): Promise<string>
```

`POST /pages/{pageId}/attachments` with the raw `File` as the body,
`X-Filename` percent-encoded, and `Content-Type` overridden off the shared
fetch helper's JSON default. Returns the response's `url`.

The response's `content_type` is authoritative and decides the block type:
`image` for the four sniffed image types, `file` for anything else. BlockNote
chose the block from the browser's own MIME guess and its `image/*` filter,
which is wider than what the route stores as an image, so an SVG picked as an
image comes back as `application/octet-stream` and must become a file block
rather than an image pointing at a download.

`usePageEditor` takes an optional `pageId` and configures BlockNote's
`uploadFile` **only when it has one**, so demo mode — which passes none and
renders a non-editable editor — has no upload code to fire at all.

### 7.2 Failure

BlockNote inserts the block and swaps in a "Loading…" element when the upload
starts, and it has **no completion reset**: the element is replaced only when
the node view re-renders. So resolving the empty string is not enough —
`url` is already `""`, the update emits no ProseMirror step, and the block
stays on "Loading…" with no way back to the add-file button.

On failure the hook therefore, in order: raises a `sonner` toast carrying the
server's own message (413 over `attachment_max_bytes`, 403 on a read-only
instance), **resets the block to an empty paragraph**
(`editor.updateBlock(blockId, {type: "paragraph", content: []})`), and
resolves `""`. The retype is a real change, so the node view is rebuilt and
the loader is gone; the operator is left with the empty paragraph they can
retry in. It does not reject: BlockNote calls `uploadFile` from a drop handler
that does not await it, so a rejection is an unhandled rejection.

### 7.3 Uploads in flight

A block whose upload has not resolved contributes nothing to the desired tree
(§4.4), so `PageSync.pending` reads false, the status shows "saved", and the
unload warning in `use-page-sync.ts` does not fire. Closing the tab mid-upload
would lose the insertion with no warning, and no keepalive write can help
because the URL does not exist yet.

So the upload lifecycle is tracked **outside** the tree: `usePageEditor` keeps
a count of uploads in flight, incremented before the request and decremented
in a `finally`, and exposes it. `use-page-sync.ts`'s unload guard fires when
`PageSync.pending` **or** that count is non-zero, and the saved indicator
shows the saving state while it is non-zero. The counter is the editor's, not
the sync engine's: `PageSync` stays pure of the editor, which is what
`lib/page-sync.ts` is for.

### 7.4 When the guard refuses the conversion

BlockNote replaces, rather than inserts after, **any** block whose content is
an empty array — not only an empty paragraph. Pasting a file into an empty
list item that has a child therefore retypes that list item into an image,
giving an `image` block a child group, which `addsNestingViolation` rejects.
The transaction is refused, the list item survives, the upload still runs, and
BlockNote then updates a block that never became an attachment: no attachment
block results and the file is silently discarded.

So `uploadFile` checks, after the upload resolves, that
`editor.getBlock(blockId)` is an `image` or `file` block. When it is not — the
guard refused, or the block was removed mid-upload — the hook inserts a fresh
block of the right type carrying the URL immediately after `blockId` (or at
the end of the document when `blockId` is gone) and returns `""`.

**One mechanic the implementation task must settle against a real editor, not
by reading:** what BlockNote's follow-up `updateBlock(blockId, {props: {url}})`
does when `blockId` is now a list item or a paragraph, which has no `url`
prop. If it is inert, returning `""` is right as written. If it throws, the
return value has to be chosen so the follow-up is a no-op, or the recovery
insert has to happen after it. `__tests__/blocknote-probe.test.tsx` is the
established place in this codebase for settling a question like this against a
real instance, and the answer belongs in a test there, not in a comment.

## 8. Known limits

- Deleting or undoing a placeholder while its upload is in flight makes
  BlockNote's own handler update a block that is gone, which throws inside a
  promise it does not await. It is a console error, not data loss — §7.4's
  recovery insert has already placed the attachment — and the fix belongs
  upstream.
- The file panel's "Embed URL" tab can point a **`file`** block at an external
  URL. It saves as `[name](url)` and reads back as an ordinary paragraph link:
  the text and the link survive, the rendering changes. Images are unaffected,
  since any image URL is a block (§2).
- An `http://` image stays blocked by the CSP and renders broken (§6).
- An image the route could not sniff (an SVG, say) is retyped from `image` to
  `file` by §7.1's rule after the upload, so the operator sees the block kind
  change once the response lands. Better than an image block pointing at a
  download, and a test covers it.
- A background colour set through the side menu is dropped on reload, as it
  already is for every paragraph (§5).

## 9. Rejected: the inline thumbnail

Programme spec §5.2 asked that a `rawInline` atom render a thumbnail when its
target is an attachment image — the case of an image inside other text, which
cannot become a block. Cut: it adds a second image-rendering path to build and
test for a case the import does not produce (Notion writes images as their own
paragraph). It can be added later without touching anything in this design.

## 10. Testing

**vitest.**

- `block-mapping`: an image paragraph and an attachment-link paragraph in both
  directions; `canonicalTree` a fixed point over both; **`![draft]()`
  surviving as a `rawInline` atom** (§4.1 rule 3); a standalone external link
  staying a paragraph; an image mid-sentence staying a `rawInline` atom; an
  empty-URL `image` and `file` block omitted from the tree; and **the emitted
  paragraph text matching the cleanup job's regexp verbatim** (§4.5).
- `inline-markdown`: a table of spellings through `asStandaloneFile` and
  `fileMarkdown`, separating canonical escaped spellings that do round-trip
  (`![a\[b\]](…)`) from ones the writer rewrites; an empty destination; a link
  title; trailing text.
- `attachments` (new file): `uploadAttachment` sends the raw body and the
  percent-encoded `X-Filename`; `ATTACHMENT_URL` agrees with the backend
  pattern read out of `page_attachment_cleanup.py`.
- `use-page-editor`: `uploadFile` absent without a `pageId`; the slash menu
  offers `image` and `file`; the failure path toasts, retypes the block to a
  paragraph and leaves no loader; the in-flight counter rises and falls.
- `use-page-sync`: the unload guard fires on an in-flight upload with a
  settled tree.
- `nesting-guard`: an `image` and a `file` block may not hold children.
- `blocknote-probe`: against a real editor — what the follow-up `updateBlock`
  does when its block is no longer a file block. Two probes this bullet
  originally asked for are **not** written; §13 says which, and why.
- `page-editor`: the resize handle is hidden; the download button renders for
  a file block and not for a paragraph.

**Backend pytest.** `tests/test_edge_response_policy.py` — unchanged in shape,
it already compares the app's CSP against `nginx.conf` character for
character, so it passes only when §6 edits both.

**No Playwright.** An end-to-end upload needs a writable attachments directory
on the disposable stack in `backend/scripts/e2e/run_playwright_e2e.py`, which
sub-project 4 needs for the import run anyway and can carry.

## 11. Documentation and deploy

- `CLAUDE.md`: one sentence in the `/notes` paragraph — the editor renders and
  uploads images and files, stored as markdown in the block's text — and the
  CSP's `img-src` widening beside the security-posture material.
- `CHANGELOG.md`: rides with the release carrying the import (sub-project 4).
- The change alters the running artifact (`backend/` and `frontend/`), so
  CLAUDE.md's redeploy rule applies: gate, build, `docker compose up -d`, and
  confirm the new CSP on a live response rather than only in the tree.

## 12. Review findings not adopted

- **Schema order is load-bearing.** Refuted on the installed library: the
  `*/*` accept matches nothing, so order cannot turn a PNG into a file (§3).
  The `"file"` fallback *name* is load-bearing and is kept.
- **Background colour is a defect this change introduces.** It is
  pre-existing for every paragraph and is recorded rather than fixed (§5).

## 13. Not pinned, deliberately

§3 rests on a claim about BlockNote's MIME matcher — that the `file` spec's
`*/*` accept matches nothing but an exactly equal type, so schema order cannot
turn a dropped PNG into a file block. §10 asked for a test pinning the
behaviour (a dropped PNG becomes an `image`, a dropped PDF a `file`) rather
than the order.

That test is **not written**. The matcher is not exported, so a test can only
reach it by dispatching a synthetic drop event with a constructed
`DataTransfer` through jsdom, which pins the harness's event plumbing at least
as much as the library. What is pinned instead is each spec's declared
`fileBlockAccept`, which is the input the matcher reads. The residual exposure
is narrow and named: a BlockNote release that changed the matcher so `*/*`
began matching everything would make schema order load-bearing again, and
nothing in this tree would go red. Re-read §3 on an upgrade.

The second is §7.4's conversion-refusal path end to end: a paste into an empty
list item holding a child, the nesting guard refusing the in-place conversion,
and the recovery insert placing the attachment beside it. The probe reaches the
same question — what a write of an undeclared prop does to a block that is no
longer a file block — by retyping the block instead, because the end-to-end
path needs a synthetic paste event carrying a file. The recovery branch itself
*is* covered, by `use-page-editor`'s own test (§10), driving `uploadFile`
directly against a list item with a child. What is untested is BlockNote's
follow-up write landing on it.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { ApiError, apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

/** Every documents payload carries `horizon` except the summary and the two
 *  relatedness reads (connections, related memories); those answer with
 *  `embedded` plus a comparable count instead, which is what says whether the
 *  comparison could be made at all. The label rides the data, not
 *  only the page chrome: a client rendering this anywhere else must still be
 *  able to say what it is looking at. */
export interface DocumentListItem {
  id: string
  title: string | null
  uri: string | null
  source_type: string | null
  project: string
  block_count: number
  /** Optional so the four existing test fixtures that build this shape by
   *  hand keep typechecking. The API always sends it. */
  pinned_at?: string | null
  /** Whether `GET /documents/{id}/summary` would answer 200 rather than its
   *  "not generated yet" 404. Optional for the same reason as `pinned_at`. */
  has_summary?: boolean
  /** Tag names, sorted. Optional for the same reason as `pinned_at`. */
  tags?: string[]
}

export interface DocumentListResponse {
  items: DocumentListItem[]
  horizon: boolean
}

export interface DocumentSummary {
  document_id: string
  text: string
  generated_at: string
  block_count: number
  /** Always false. A summary is a report over one document, never a verified
   *  claim — the wire says so rather than leaving a renderer to infer it. */
  badged: boolean
}

export interface DocumentConnection {
  document_id: string
  title: string | null
  /** An ordering key, never a calibrated relevance measure -- the score
   * distribution is continuous, so rendering this as a percentage or a badge
   * would assert a precision nobody measured. Show the passage. */
  score: number
  block_id: string
  block_text: string
  other_block_id: string
  other_block_text: string
}

export interface DocumentConnectionsResponse {
  items: DocumentConnection[]
  /** False means the comparison could not be made -- one side is not embedded
   * under any shared fingerprint yet. Different from an empty list. */
  embedded: boolean
  comparable_documents: number
}

export interface QaCitation {
  block_id: string
  document_id: string
  span_start: number
  span_end: number
}

export interface QaSentence {
  text: string
  citation: QaCitation | null
}

export interface QaResponse {
  question: string
  outcome: "served" | "labelled" | "withheld"
  grounded: boolean
  label: string | null
  entailed: number
  total: number
  judged: boolean
  reason: string | null
  sentences: QaSentence[]
  horizon: boolean
}

/** `null` when no summary has been generated — the door answers 404 for that,
 *  and it is an ordinary state rather than a fault: generating one is an
 *  explicit act nobody has performed yet. Every other status still throws.
 *
 *  `hasSummary` is the list row's `has_summary`. When it is `false` the read
 *  is never sent: the 404 is the expected answer, and the browser logs every
 *  one as a failed request, so opening any unsummarised document put an
 *  error in the console. `undefined` (a caller with no list row) still asks.
 *  A disabled query still serves what `useDocumentSummarize` seeds. */
export function useDocumentSummary(
  documentId: string | null,
  hasSummary?: boolean,
) {
  return useQuery<DocumentSummary | null>({
    queryKey: ["documentSummary", documentId],
    enabled: !DEMO && Boolean(documentId) && hasSummary !== false,
    queryFn: async () => {
      try {
        return await apiFetch<DocumentSummary>(`/documents/${documentId}/summary`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  })
}

/** Generate and store this document's summary. A POST because it creates the
 *  summary the GET twin reads -- and it spends an LLM call, so it is never
 *  fired implicitly by opening a document. */
export function useDocumentSummarize(documentId: string | null) {
  const qc = useQueryClient()
  return useMutation<DocumentSummary, Error, void>({
    mutationFn: () =>
      apiFetch<DocumentSummary>(`/documents/${documentId}/summary`, {
        method: "POST",
      }),
    onSuccess: (summary) => {
      // Seed rather than only invalidate: the generated summary is already
      // the authoritative body, so a refetch would spend a round trip to
      // learn what this response just said.
      qc.setQueryData(["documentSummary", documentId], summary)
      // The list rows carry `has_summary`, which is now stale.
      invalidateDocumentLists(qc)
    },
  })
}

/** Delete withdraws this document's block sources and expires any fact left
 *  with no surviving source, so the confirm copy has to say more than "this
 *  removes the row". `documentsAll` and `documents` both hold the tree. */
export function useDocumentDelete() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (documentId) =>
      apiFetch<void>(`/documents/${documentId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["documentsAll"] })
      void qc.invalidateQueries({ queryKey: ["documents"] })
    },
  })
}

export function useDocumentConnections(documentId: string | null) {
  return useQuery<DocumentConnectionsResponse>({
    queryKey: ["documentConnections", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: ({ signal }) =>
      apiFetch<DocumentConnectionsResponse>(
        `/documents/${documentId}/connections`, { signal }),
  })
}

export interface QaParams {
  question: string
  project: string
  document_id?: string | null
}

export function useGroundedQa() {
  return useMutation<QaResponse, Error, QaParams>({
    mutationFn: (params) =>
      apiFetch<QaResponse>("/documents/qa", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}

// ── The workspace's reads (2026-08-31 spec §2, §3) ───────────────────

/** The list route clamps `limit` to 200 (`backend/app/api/routes/documents.py`)
 *  and carries no `total`, so one page cannot hold a ~465-file corpus and
 *  cannot even say it was cut (review finding m1). Stitch pages until a short
 *  one; dedupe by id, because the order is `created_at DESC` and a filing that
 *  lands mid-pagination shifts every later offset. */
const PAGE_LIMIT = 200
const MAX_PAGES = 25 // 5,000 documents; a guard, not a target

export interface AllDocumentsResult {
  items: DocumentListItem[]
  /** True only when MAX_PAGES was exhausted while pages were still full.
   *  Render it as a visible banner, never drop it (invariant 14). */
  truncated: boolean
}

export function useAllDocuments(project: string) {
  return useQuery<AllDocumentsResult>({
    queryKey: ["documentsAll", project],
    enabled: !DEMO,
    queryFn: async () => {
      const byId = new Map<string, DocumentListItem>()
      let truncated = false
      for (let page = 0; ; page++) {
        if (page >= MAX_PAGES) {
          truncated = true
          break
        }
        const res = await apiFetch<DocumentListResponse>(
          `/documents?project=${encodeURIComponent(project)}` +
            `&limit=${PAGE_LIMIT}&offset=${page * PAGE_LIMIT}`,
        )
        for (const item of res.items) byId.set(item.id, item)
        if (res.items.length < PAGE_LIMIT) break
      }
      return { items: [...byId.values()], truncated }
    },
  })
}

export interface OutlineNode {
  block_id: string
  level: number
  text: string
  order_index: number | null
}

export interface BlockRow {
  block_id: string
  type: string | null
  /** Marker-stripped: a heading's text is "Foo", not "## Foo". */
  text: string
  order_index: number | null
  char_span: [number, number] | null
  /** The enclosing block, or null at the top level. A nested list item's
   *  parent is the enclosing *item* -- the list wrapper mints no block -- so
   *  nesting is rebuilt from this alone, never inferred from order_index. */
  parent_id: string | null
  /** A heading's level, a table's header/alignments. NOT a list marker on a
   *  parsed document: `parse_markdown` writes no properties for a list block.
   *  The block editor's `promote` does write `marker`, so the key exists on
   *  edited blocks only. */
  properties: Record<string, unknown> | null
  /** The block's own markdown source, marker included. This is what an
   *  editor edits -- `text` is a different string from the stored one. */
  source: string | null
}

export interface RelatedMemory {
  memory_id: string
  content: string
  memory_type: string | null
  status: string
  source: string | null
  /** The document's own project, which scopes the read. Served because
   * `content_surfaces` declares this surface labels it. */
  project: string
  /** An ordering key, never a calibrated relevance measure -- the score
   * distribution is continuous, so rendering this as a percentage or a badge
   * would assert a precision nobody measured. Show the passage. */
  score: number
  block_id: string
  block_text: string
  span_start: number | null
  span_end: number | null
}

export interface RelatedMemoriesResponse {
  items: RelatedMemory[]
  /** False means the comparison could not be made -- no live fingerprint
   * holds vectors for both this document and the project's memories yet.
   * Different from an empty list, and NOT the "no memory exists" state:
   * that is `comparable_memories === 0`, which is counted independently of
   * the fingerprint and must be tested first. */
  embedded: boolean
  comparable_memories: number
}

export function useRelatedMemories(documentId: string | null) {
  return useQuery<RelatedMemoriesResponse>({
    queryKey: ["documentRelatedMemories", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: ({ signal }) => apiFetch(`/documents/${documentId}/related-memories`, { signal }),
  })
}

export function useDocumentOutline(documentId: string | null) {
  return useQuery<{ document_id: string; items: OutlineNode[] }>({
    queryKey: ["documentOutline", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: ({ signal }) => apiFetch(`/documents/${documentId}/outline`, { signal }),
  })
}

export interface DocumentBlocksResponse {
  document_id: string
  blocks: BlockRow[]
  /** The hash a block write must precondition on. Nullable because the route's
   *  response model is, not because any filed document lacks one -- a document
   *  filed from bytes stores no `content` and still has its hash, taken over
   *  those bytes. */
  content_hash: string | null
}

/** Shared so a re-read of the hash resolves the same cache entry the editor
 *  renders from, rather than a second one under a duplicated key. */
export function documentBlocksQuery(documentId: string) {
  return {
    queryKey: ["documentBlocks", documentId],
    queryFn: () => apiFetch<DocumentBlocksResponse>(`/documents/${documentId}`),
  }
}

export function useDocumentBlocks(documentId: string | null) {
  return useQuery<DocumentBlocksResponse>({
    ...documentBlocksQuery(documentId ?? ""),
    enabled: !DEMO && Boolean(documentId),
  })
}

export interface SectionHit {
  block_id: string
  document_id: string
  uri: string | null
  title: string | null
  heading_path: string[]
  path_truncated: boolean
  text: string
  score: number
}

/** Both list keys, the pair `useDocumentDelete` already invalidates. Every
 *  mutation below changes what the tree renders, so they all invalidate the
 *  same two. */
function invalidateDocumentLists(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["documentsAll"] })
  void qc.invalidateQueries({ queryKey: ["documents"] })
}

export interface DocumentCreateParams {
  project: string
  uri: string
  title?: string
  /** Markdown. Blank seeds a heading from the title instead. */
  content?: string
}

export interface DocumentCreateResult {
  document_id: string
  /** created | updated | unchanged -- anything but `created` means a
   *  document was already filed at this uri when the POST landed. */
  outcome: string
}

export function useDocumentCreate() {
  const qc = useQueryClient()
  return useMutation<DocumentCreateResult, Error, DocumentCreateParams>({
    // Seeded content, never empty: `DocumentPutRequest.content` is
    // `min_length=1`, so an empty body is a 422. And note `document_put` is
    // an UPSERT on `(project, uri)` -- the caller mints a uri no document
    // holds (`isUriTaken`), or this silently refiles the existing document.
    mutationFn: ({ project, uri, title, content }) =>
      apiFetch(`/documents`, {
        method: "POST",
        body: JSON.stringify({
          project,
          uri,
          content: content?.trim() ? content : `# ${title ?? "Untitled"}\n`,
          title: title ?? "Untitled",
        }),
      }),
    onSuccess: () => invalidateDocumentLists(qc),
  })
}

/** Whether a document is filed at exactly `(project, uri)` right now.
 *
 *  Through the manifest rather than `GET /documents/by-uri`: that read
 *  answers a free path with a 404, which the browser logs as a failed
 *  request on every successful create. The manifest answers 200 with the
 *  subtree under the prefix, sorted by uri, so the exact uri -- the
 *  shortest key under itself -- is the first row when it exists. */
export async function isUriTaken(project: string, uri: string): Promise<boolean> {
  const res = await apiFetch<{ items: { uri: string }[] }>(
    `/documents/manifest?project=${encodeURIComponent(project)}` +
      `&uri_prefix=${encodeURIComponent(uri)}&limit=1`,
  )
  return res.items[0]?.uri === uri
}

export interface DocumentMetadataParams {
  documentId: string
  title?: string
  uri?: string
  pinned?: boolean
  tags?: string[]
  /** Compare-and-set on the document's `content_hash`; 409 when stale. */
  expected_hash?: string
}

export function useDocumentMetadataUpdate() {
  const qc = useQueryClient()
  return useMutation<{ document_id: string }, Error, DocumentMetadataParams>({
    mutationFn: ({ documentId, ...fields }) =>
      apiFetch(`/documents/${documentId}`, {
        method: "PATCH",
        body: JSON.stringify(fields),
      }),
    onSuccess: () => invalidateDocumentLists(qc),
  })
}

export interface SubtreeRenameParams {
  project: string
  uri_prefix: string
  new_uri_prefix: string
}

export function useDocumentSubtreeRename() {
  const qc = useQueryClient()
  return useMutation<{ renamed: number }, Error, SubtreeRenameParams>({
    mutationFn: (body) =>
      apiFetch(`/documents/rename`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateDocumentLists(qc),
  })
}

export interface SubtreeDeleteParams {
  project: string
  uri_prefix: string
}

export function useDocumentSubtreeDelete() {
  const qc = useQueryClient()
  return useMutation<{ deleted: number }, Error, SubtreeDeleteParams>({
    mutationFn: (body) =>
      apiFetch(`/documents/delete`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateDocumentLists(qc),
  })
}

export function useDocumentSearch() {
  return useMutation<
    { items: SectionHit[] },
    Error,
    { query: string; project: string; limit?: number }
  >({
    mutationFn: (params) =>
      apiFetch(`/documents/search`, {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}

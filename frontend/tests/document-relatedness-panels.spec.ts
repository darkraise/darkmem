import { test, expect, type Page } from "@playwright/test"
import { seedAdminPassword } from "./helpers/seed-admin"

/**
 * The two relatedness panels, end to end (spec §3, §4).
 *
 * **These panels were reachable from no test at all.** `DocumentDetail` and
 * `RelatedMemoriesCard` live in
 * `src/features/documents/components/document-actions.tsx`, which only
 * `project-workspace.tsx` mounts, and which only renders once a document is
 * selected in the tree. No spec in this directory had ever selected one:
 * `project-workspace-layout.spec.ts` navigates to `/projects/default` and
 * asserts pane geometry without opening anything, and `documents.spec.ts`
 * exercises the unrelated `/documents` route, whose detail pane is a
 * different, locally-defined component. `rg -l
 * "related-memories|comparable_memories" frontend/tests/` returned nothing
 * before this file. Nor is there a unit test: the sibling
 * `__tests__/document-actions.test.tsx` covers `DocumentActions` (the
 * mode/summarize/delete strip) and stops there. Every arm of both panels --
 * four states each, plus the failed-read arm each carries -- shipped with no
 * automated reader of any kind.
 *
 * **Why the count is asserted before `embedded`, in both panels.** Each panel
 * distinguishes four states, and two of them have `embedded: false`. The
 * count is what separates them, so the arms have to be ordered count-first —
 * and the failure mode of getting that wrong is silent: a project holding no
 * memory (or no second document) would render "still being embedded" forever,
 * about a counterpart that does not exist and that nothing will ever embed.
 * A test that only asserted the expected copy is present would pass under
 * either ordering, because the zero-count payload satisfies `!embedded` too.
 * So every zero-count test here additionally asserts that the *embedding*
 * copy is absent. That negative assertion is the whole regression guard; the
 * positive one is nearly free.
 *
 * **Real document, mocked reads.** Every test files a real document through
 * `POST /api/v1/documents` and selects it by clicking its real tree row, so
 * the navigation, the route, the tree, the selection state and the component
 * tree are all genuine. Only the two panel reads are fulfilled from fixtures,
 * for the three states a disposable stack cannot be driven into on demand:
 * producing a true `embedded: false` would mean racing the filing path's own
 * embed, and producing a populated list would mean filing a second document
 * and a memory and depending on their cosine landing where the assertion
 * expects. The fourth state — both counts at zero — is asserted against the
 * live door with nothing mocked, which is what pins the wire contract.
 *
 * **This spec needs the embedder.** Filing a document embeds its blocks in
 * the same request, so `POST /api/v1/documents` fails outright if the seeded
 * Ollama endpoint is unreachable. `fileDocument` throws with that named
 * rather than soft-skipping, for the reason documents.spec.ts's header
 * records: a skip is what let a whole spec read green while asserting
 * nothing.
 *
 * Sign-in is copied from the sibling real-mode specs rather than shared, for
 * the reason documents.spec.ts's header gives.
 */

const PASSWORD = process.env.E2E_ADMIN_PASSWORD

/** The workspace route the panels live under, and an empty project on a
 *  disposable stack: `seed_facts` files its memory under
 *  `t290-knowledge-e2e`, so `default` holds nothing but what this spec
 *  files. That emptiness is what makes the live-door test below predictable. */
const PROJECT = "default"

/** A root-level uri on purpose — one path segment means one leaf row with no
 *  folder to expand first. */
const URI = "e2e-relatedness-panels.md"
const CONTENT =
  "# Relatedness panels\n\nA filed paragraph for the panels to hang under.\n"

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByRole("textbox", { name: "Password" }).fill(PASSWORD!)
  await page.getByRole("button", { name: /sign in/i }).click()
  await expect(page).toHaveURL("/")
}

/** File the document the panels describe. Idempotent: `(project, uri)` is the
 *  document's identity, so a re-run updates the same row rather than filing a
 *  second one — which matters because these tests share one live stack. */
async function fileDocument(page: Page) {
  // `page.request` shares the browser context's cookie jar, so this carries
  // the session sign-in just established. It is NOT subject to `page.route`,
  // which is why the fixtures below cannot accidentally intercept it.
  const response = await page.request.post("/api/v1/documents", {
    data: {
      project: PROJECT,
      uri: URI,
      title: "Relatedness panels e2e",
      content: CONTENT,
    },
  })
  if (!response.ok()) {
    throw new Error(
      `filing the fixture document failed with ${response.status()}: ` +
        `${await response.text()}. Filing embeds the document's blocks in ` +
        "the same request, so an unreachable embedder fails here — check " +
        "the seeded Ollama endpoint before reading this as a UI regression.",
    )
  }
}

/** Open the workspace and select the fixture document, leaving both panels
 *  mounted. */
async function openDocument(page: Page) {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(`/projects/${PROJECT}`)
  // The tree renders uri path segments, so the leaf row carries the uri
  // itself. Unique until the document is selected, at which point the
  // breadcrumb renders it too — hence one click, no re-query.
  await page.getByText(URI, { exact: true }).click()
  await expect(page.getByText("Related memories")).toBeVisible()
  await expect(page.getByText("Connections")).toBeVisible()
}

async function mockConnections(page: Page, body: unknown) {
  await page.route("**/api/v1/documents/*/connections", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    }),
  )
}

async function mockRelated(page: Page, body: unknown) {
  await page.route("**/api/v1/documents/*/related-memories", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    }),
  )
}

/** Both panels are fixtured in every mocked test, even when only one is under
 *  assertion: an unmocked sibling would answer from the live door and make
 *  the page's copy depend on the stack's corpus. */
const NO_CONNECTIONS = { items: [], embedded: false, comparable_documents: 0 }
const NO_MEMORIES = { items: [], embedded: false, comparable_memories: 0 }

// The panel-specific halves of the "still being embedded" copy. The two
// panels deliberately word it differently, and that difference is what lets
// each assertion name one panel without scoping to its card.
const CONNECTIONS_EMBEDDING =
  /this project's other documents are still being embedded/
const MEMORIES_EMBEDDING = /this project's memories are still being embedded/

test.beforeAll(() => {
  if (!PASSWORD) {
    throw new Error(
      "E2E_ADMIN_PASSWORD must be set — this spec never soft-skips for a " +
        "missing credential, for the reason documents.spec.ts records.",
    )
  }
  if (!process.env.E2E_DISPOSABLE_STACK) {
    seedAdminPassword()
  }
})

test("both panels mount against the live door and read as empty, not failed", async ({
  page,
}) => {
  // Nothing mocked. One document in the project and no memory in it, so both
  // panels are in their zero-count state for real — which is also the one
  // state the live door can be held in deterministically.
  await signIn(page)
  await fileDocument(page)
  await openDocument(page)

  await expect(
    page.getByText(/no other documents in this project to compare against/),
  ).toBeVisible()
  await expect(
    page.getByText(/no memories in this project to compare against/),
  ).toBeVisible()

  // The distinction the copy exists to make: an empty read is not a failed
  // one, and on a healthy install the failed-read copy must not appear.
  await expect(
    page.getByText(/connections could not be read/),
  ).toHaveCount(0)
  await expect(
    page.getByText(/related memories could not be read/),
  ).toHaveCount(0)
})

test.describe("connections", () => {
  test("a zero count reads as nothing to compare against, never as pending embedding", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await mockConnections(page, {
      items: [],
      embedded: false,
      comparable_documents: 0,
    })
    await mockRelated(page, NO_MEMORIES)
    await openDocument(page)

    await expect(
      page.getByText(/no other documents in this project to compare against/),
    ).toBeVisible()
    // The guard: this payload satisfies `!embedded` too, so an arm order that
    // tested `embedded` first would render the copy below and still pass a
    // positive-only assertion.
    await expect(page.getByText(CONNECTIONS_EMBEDDING)).toHaveCount(0)
  })

  test("a positive count with nothing embedded reads as pending", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await mockConnections(page, {
      items: [],
      embedded: false,
      comparable_documents: 3,
    })
    await mockRelated(page, NO_MEMORIES)
    await openDocument(page)

    await expect(page.getByText(CONNECTIONS_EMBEDDING)).toBeVisible()
    await expect(
      page.getByText(/no other documents in this project to compare against/),
    ).toHaveCount(0)
  })

  test("an embedded comparison that returned nothing names the sampling window", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await mockConnections(page, {
      items: [],
      embedded: true,
      comparable_documents: 3,
    })
    await mockRelated(page, NO_MEMORIES)
    await openDocument(page)

    // Not "nothing is embedded" and not "nothing is near": the read applies
    // no similarity floor, so the only thing an empty list can mean here is
    // that every passage's neighbour window was filled by other projects.
    await expect(
      page.getByText(/no other document in this project surfaced/),
    ).toBeVisible()
    await expect(page.getByText(CONNECTIONS_EMBEDDING)).toHaveCount(0)
  })

  test("a populated list renders the score and both passages", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await mockConnections(page, {
      items: [
        {
          document_id: "11111111-1111-4111-8111-111111111111",
          title: "The neighbouring document",
          score: 0.8127,
          block_id: "22222222-2222-4222-8222-222222222222",
          block_text: "the passage in this document that matched",
          other_block_id: "33333333-3333-4333-8333-333333333333",
          other_block_text: "the passage in the other document",
        },
      ],
      embedded: true,
      comparable_documents: 3,
    })
    await mockRelated(page, NO_MEMORIES)
    await openDocument(page)

    await expect(page.getByText("The neighbouring document")).toBeVisible()
    // Three decimals of a raw cosine, never a percentage or a band: the
    // distribution is continuous, so any banding would assert a precision
    // nobody measured.
    await expect(page.getByText("0.813")).toBeVisible()
    // Both passages, because the evidence is the passage and the score only
    // orders the rows.
    await expect(
      page.getByText("the passage in this document that matched"),
    ).toBeVisible()
    await expect(
      page.getByText("the passage in the other document"),
    ).toBeVisible()
  })

  test("a failed read says so rather than rendering as empty", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await page.route("**/api/v1/documents/*/connections", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "boom" }),
      }),
    )
    await mockRelated(page, NO_MEMORIES)
    await openDocument(page)

    await expect(
      page.getByText(/this is a failed read, not an empty one/).first(),
    ).toBeVisible()
    await expect(
      page.getByText(/no other documents in this project to compare against/),
    ).toHaveCount(0)
  })
})

test.describe("related memories", () => {
  test("a zero count reads as nothing to compare against, never as pending embedding", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await mockRelated(page, {
      items: [],
      embedded: false,
      comparable_memories: 0,
    })
    await mockConnections(page, NO_CONNECTIONS)
    await openDocument(page)

    await expect(
      page.getByText(/no memories in this project to compare against/),
    ).toBeVisible()
    // Same guard as the connections twin, and the same silent failure: a
    // project that will never hold a memory would otherwise be told one is
    // on its way.
    await expect(page.getByText(MEMORIES_EMBEDDING)).toHaveCount(0)
  })

  test("a positive count with nothing embedded reads as pending", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await mockRelated(page, {
      items: [],
      embedded: false,
      comparable_memories: 2,
    })
    await mockConnections(page, NO_CONNECTIONS)
    await openDocument(page)

    await expect(page.getByText(MEMORIES_EMBEDDING)).toBeVisible()
    await expect(
      page.getByText(/no memories in this project to compare against/),
    ).toHaveCount(0)
  })

  test("an embedded comparison that returned no rows renders its own arm", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await mockRelated(page, {
      items: [],
      embedded: true,
      comparable_memories: 2,
    })
    await mockConnections(page, NO_CONNECTIONS)
    await openDocument(page)

    // Defensive in production — the read inner-joins every comparable memory
    // to this document's best block with no floor, so a comparable memory
    // always yields a row — but it is an arm that renders, and an arm that
    // renders is one a payload can reach.
    await expect(
      page.getByText(/no rows came back for this document/),
    ).toBeVisible()
    await expect(page.getByText(MEMORIES_EMBEDDING)).toHaveCount(0)
  })

  test("a populated list renders the memory, its score, its passage and a non-active status", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await mockRelated(page, {
      items: [
        {
          memory_id: "44444444-4444-4444-8444-444444444444",
          content: "the memory text that sits near a passage",
          memory_type: "decision",
          status: "superseded",
          source: "mcp",
          project: PROJECT,
          score: 0.7342,
          block_id: "55555555-5555-4555-8555-555555555555",
          block_text: "the passage this memory matched",
          span_start: 0,
          span_end: 31,
        },
      ],
      embedded: true,
      comparable_memories: 2,
    })
    await mockConnections(page, NO_CONNECTIONS)
    await openDocument(page)

    await expect(
      page.getByText("the memory text that sits near a passage"),
    ).toBeVisible()
    await expect(page.getByText("0.734")).toBeVisible()
    await expect(
      page.getByText("the passage this memory matched"),
    ).toBeVisible()
    // A memory off the active lifecycle is badged, so a reader is never shown
    // a superseded row as though it were current.
    await expect(page.getByText("superseded")).toBeVisible()
  })

  test("a failed read says so rather than rendering as empty", async ({
    page,
  }) => {
    await signIn(page)
    await fileDocument(page)
    await page.route("**/api/v1/documents/*/related-memories", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "boom" }),
      }),
    )
    await mockConnections(page, NO_CONNECTIONS)
    await openDocument(page)

    await expect(
      page.getByText(/this is a failed read, not an empty one/).first(),
    ).toBeVisible()
    await expect(
      page.getByText(/no memories in this project to compare against/),
    ).toHaveCount(0)
  })
})

# Two-door parity — every Phase-1 surface, REST and MCP

**Audit date:** 2026-07-28 · **Task:** T1.42d · **Contract:** doc 12 (`docs/design/12-api-and-mcp-contract.md`), invariant 17.

Invariant 17 is *two front doors, one service layer*: an MCP tool and its REST
twin call the same service and never drift into two engines, and **every
capability lands on both doors or is explicitly single-door with a stated
reason**. This file is the audit that makes that checkable instead of
aspirational. It is exhaustive over the Phase-1 surface — every REST route on
`app.routes` and every tool in the live FastMCP registry appears in exactly one
row.

**68 surfaces: 20 two-door, 48 single-door with a stated reason (41 REST-only, 7 MCP-only), 0 divergent.**

## How to read a row, and what each status costs

- **two-door** — the capability is reachable from both doors. Where the two
  doors deliberately differ in *wire shape* (never in ranking, filtering or
  scope) the difference is recorded in the row.
- **single-door** — reachable from one door, with a reason. A schedule is not a
  reason: *"not yet built"*, *"planned"*, *"TBD"* are precisely the sequencing
  invariant 17 forbids, and `tests/test_door_parity.py` rejects them.
- **divergent** — the worst state, and deliberately not filed as an exemption.
  Both doors implement the same capability separately and the two have already
  drifted, so the same question gets two answers with no error anywhere. A
  divergence must name an owning task, and the test asserts that task exists.

## The table is generated, not maintained

`backend/tests/test_door_parity.py`'s `PARITY_TABLE` is the single source of
truth; the block below is rendered from it and `test_the_committed_table_is_the_enforced_table`
fails if the two disagree. Do not edit the markdown by hand — change the table
and regenerate:

```bash
cd backend && .venv/bin/python -c \
  "from tests.test_door_parity import render_markdown; print(render_markdown())"
```

The enumeration itself is driven off the router and the tool registry, never
off a literal, so a new REST route or a new tool that nobody classified fails
the test rather than quietly joining the surface.

## The parity table

<!-- BEGIN GENERATED PARITY TABLE -->
| Surface | REST | MCP | Status | Reason / note |
|---|---|---|---|---|
| `distribution.config` | `GET /api/v1/distribution`<br>`PUT /api/v1/distribution/policy` | — | REST single-door | Configures what agents are *told*, and the curb stops push entirely. Exposing 'stop telling agents things' to an agent inverts the control it exists to give a human, so this is single-door on purpose rather than by omission. |
| `config.auto_research` | `GET /api/v1/config/auto-research`<br>`PUT /api/v1/config/auto-research` | — | REST single-door | Arming the research loop is an operator act, and the loop's own door is an MCP tool — so an MCP twin here would let the caller that runs the loop also switch it on, which is the control this row exists to keep with the human. Same shape as the distribution config above and for the same reason. |
| `usage.read` | `GET /api/v1/usage/overview`<br>`GET /api/v1/usage/series`<br>`GET /api/v1/usage/by-subject/{subject_type}/{subject_id}`<br>`GET /api/v1/usage/top`<br>`POST /api/v1/usage/subject-totals`<br>`GET /api/v1/usage/by-job` | — | REST single-door | What the operator's own agents cost, read by the operator. An MCP twin would hand the metered party its own meter -- the same review-folded-back-into-the-reviewed shape the research-runs row below records, and sharper here, because an agent that can read which of its calls were expensive is being handed the only signal a human has for noticing that. It is also not a capability an agent needs: nothing an agent does with a memory depends on what the call cost. |
| `usage.prices` | `GET /api/v1/usage/prices`<br>`PUT /api/v1/usage/prices` | — | REST single-door | Model rates are an operator setting, and the write half decides what every later call is reported to have cost. Exposing it to an agent would let the measured party set its own price, which is the same control the distribution curb keeps with the human. |
| `config.research_runs` | `GET /api/v1/config/auto-research/runs`<br>`POST /api/v1/config/auto-research/runs/{event_id}/rerun` | — | REST single-door | The operator's view of what the loop has already filed, and a re-derivation of one run's evidence. Single-door for the sibling reason to the config rows above: the MCP caller is the one that runs the loop, and handing it the surface that inspects and re-derives its own past runs is the review step folded back into the reviewed. Re-derivation also files nothing and gathers nothing, so doc 09 §6's gatherer argument -- which is what keeps `research_run` itself off REST -- does not reach it. |
| `documents.reads` | `GET /api/v1/documents`<br>`GET /api/v1/documents/{document_id}/summary`<br>`GET /api/v1/documents/{document_id}/connections` | — | REST single-door | EH1 is a horizon lane behind its own eval gate (doc 16 §1's firewall), and an MCP twin would put an unshipped surface in front of every agent before the gate that governs it has run. Single-door until G-F clears, then re-decided on its merits rather than inherited. |
| `documents.grounded_qa` | `POST /api/v1/documents/qa` | — | REST single-door | Same firewall as the reads above, plus a sharper reason of its own: the answer is served, labelled or withheld by the faithfulness gate, and an agent twin would be a second consumer of a judge role that has no qualification record yet. Every answer is withheld today; publishing that to agents as a tool would advertise a capability the gate does not license. |
| `checkpoint.save` | `POST /api/v1/checkpoints` | `checkpoint_save` | two-door | — |
| `checkpoint.latest` | `GET /api/v1/checkpoints/latest` | `checkpoint_latest` | two-door | — |
| `memory.capture` | `POST /api/v1/memories` | `memory_add` | two-door | — |
| `memory.capture_batch` | `POST /api/v1/memories/batch` | `memory_batch_add` | two-door | Both doors resolve identity on the raw entry dicts before MemoryCreate validation, and both mirror the 1-100 cap. |
| `memory.search` | `POST /api/v1/memories/search`<br>`POST /api/v1/memories/search/paginated` | `memory_search` | two-door | Stated wire asymmetry, settled by T1.42a and T1.42c: the tool answers a bare JSON array, which has nowhere to carry the envelope's ContextEcho or excluded counts. Giving it one is a breaking change that doc 12 section 3 says ships as a new tool name, never as a silent mutation of this one. The ranking, the filters and the SQL pushdown are the same service call. |
| `memory.read` | `GET /api/v1/memories/{memory_id}` | `memory_get` | two-door | — |
| `memory.update` | `PUT /api/v1/memories/{memory_id}` | `memory_update` | two-door | — |
| `memory.delete` | `DELETE /api/v1/memories/{memory_id}` | `memory_delete` | two-door | — |
| `memory.reason` | `POST /api/v1/memories/reason` | `memory_reason` | two-door | — |
| `memory.duplicates` | `GET /api/v1/memories/{memory_id}/duplicates` | `memory_find_duplicates` | two-door | — |
| `tag.histogram` | `GET /api/v1/tags` | `memory_tags` | two-door | — |
| `project.catalog` | `GET /api/v1/projects` | — | REST single-door | The scope picker's list, for a human choosing which project the UI is looking at. An MCP caller never browses for its scope: it passes `project` explicitly on every capture and recall tool, because the agent is the thing that decides which project its work belongs to. Its sibling tag.histogram above is two-door for the opposite reason -- tags are a retrieval filter an agent picks from, so it has to be able to see which ones exist. Revisit this if an agent ever needs to recall across a corpus whose projects it did not author. |
| `repo.list` | `GET /api/v1/repos` | `list_repos` | two-door | — |
| `code.search` | `POST /api/v1/code/search` | `code_search` | two-door | Both doors fuse through CodeQueryService.search_code and publish the same rrf_score under the same score key (T1.42c). With no embedder configured the doors answer differently on purpose: the tool returns doc 12 section 3's typed degradation envelope, the route degrades to the keyword arm. |
| `code.blast_radius` | `POST /api/v1/code/blast-radius` | `code_blast_radius` | two-door | Only the name-to-id resolution is the tool's; the recursive traversal is the service's (T1.42c). |
| `code.symbols` | `GET /api/v1/code/symbols`<br>`GET /api/v1/code/symbols/lookup`<br>`GET /api/v1/code/symbols/{symbol_id}` | `code_symbol`<br>`code_file_symbols` | two-door | Two doors, two implementations: both tools build their own SQLAlchemy query instead of spending CodeQueryService.list_symbols. Not yet observably divergent -- the tools emit a subset of the service's keys and no row differs -- but it is the same latent drift T1.42c found already realised on code_search and code_blast_radius. Delegating is not a no-behaviour-change edit (the service caps at limit=50 and the tools are uncapped), so it needs an owner, not a one-liner. |
| `knowledge.overview` | `GET /api/v1/knowledge/overview` | `memory_overview` | two-door | Doc 12 section 3's tool table pairs the tool with this route, and both doors call memory_overview.get_overview -- the map selection, the single summarization reduce, the community-set cache and the declared drops are the service's, so neither door can answer a partial overview the other reports as complete. The REST door is auth-gated and the tool is not, the same posture every two-door read on this table carries. |
| `knowledge.fact_detail` | `GET /api/v1/knowledge/facts/{fact_id}` | `fact_get` | two-door | Doc 12 section 2's route table assigns fact_get a REST twin at exactly this path and section 3 puts the agent-facing single-object vault read on the tool, so T2.72 built the tool rather than leaving the route filed single-door on a posture argument. Both doors call facts_read.get_fact and both serialise through FactDetailResponse -- the tool does not reshape the dict, so a field the model does not declare is dropped on both doors and the badge's claim sentence crosses byte for byte (test_fact_detail_doors_serve_the_same_row). The REST door is auth-gated and the tool is not, the same posture every two-door read on this table carries. |
| `knowledge.article_detail` | `GET /api/v1/knowledge/articles/{article_id}` | `article_get` | two-door | Doc 12 section 2's route table assigns article_get a REST twin at exactly this path, and section 3 puts the single-object vault reads on tools. Built as its sibling was rather than filed single-door: both doors call articles_read.get_article and both serialise through ArticleDetailResponse, so the coverage number, the citations and the stale label cross byte for byte. The REST door is auth-gated and the tool is not, the same posture every two-door read here carries. |
| `knowledge.articles_list` | `GET /api/v1/knowledge/articles` | — | REST single-door | The same reason knowledge.facts_list is REST-only, and it is the list/detail split rather than a posture argument: doc 12 section 3 assigns the agent one list-shaped vault read and it is knowledge_search -- a composed, ranked, badged answer to a query. A project-scoped page of articles in synthesis order is a browsing surface doc 13 section 5.2 needs and an agent does not; the detail half of this surface is knowledge.article_detail, two-door with article_get. |
| `knowledge.composed_search` | `POST /api/v1/knowledge/search` | `knowledge_search` | two-door | Doc 12 section 3's composed four-layer read: one ranked list drawn from L0 memories and L2 facts at once, every row labelled and every fact badged, the memories that source a fact nested under it, and an envelope naming which channels ran and how many rows a context conflict excluded. T2.72 shipped the tool and filed the surface MCP-single-door as an agent-shaped projection, recording rather than resolving the fact that doc 12 section 2 assigns the twin; T2.80 built it. The filing was honest and it was wrong: memory.search and code.search are both two-door, so a cross-layer ranked answer is a capability by this table's own precedent, and this was the only ranked retrieval in the system with one door. Both ends call LayerCompositionService.search and both serialise through knowledge_search_response, the function T2.72 placed outside the tool for exactly this; the degraded payload has one producer too (knowledge_search_unavailable). Ranking parity is asserted on the order and not the shape (tests/test_knowledge_search.py), because a row-shape test stays green while two doors order one corpus differently. Two stated wire asymmetries, neither of them a capability: the tool clamps an out-of-range limit to the shared cap while the route 422s on it, and unavailability is a 503 whose body is the shared model against a tool payload that adds the MCP envelope's schema_version. The route is auth-gated and the tool is not, the same posture every two-door read on this table carries. |
| `memory.stats` | `GET /api/v1/analytics/stats` | `memory_stats` | two-door | T1.42f closed the audit's one recorded divergence: neither door called a service before, so the shared counts (plus the entities and relationships pair from PostgresGraphRepository.get_stats(), with its SQLAlchemyError rollback guard intact) were lifted into AnalyticsService.get_stats() and both doors now call it. |
| `auth.session` | `POST /api/v1/auth/login`<br>`POST /api/v1/auth/logout`<br>`POST /api/v1/auth/refresh`<br>`POST /api/v1/auth/change-password`<br>`GET /api/v1/auth/me` | — | REST single-door | The MCP door is unauthenticated by design (invariant 20, doc 12 section 6), so a session surface on it is a contradiction in terms: there is no session to establish, and a change-password twin would let any LAN peer seize the admin account. |
| `auth.audit` | `GET /api/v1/auth/audit` | — | REST single-door | A human security-review read of the doc 12 section 7 observability class: it enumerates login attempts and token events, which is precisely the material an unauthenticated caller must not be able to page through. |
| `security.posture` | `GET /api/v1/auth/security-posture` | — | REST single-door | Human observability of the box's own security configuration -- the same doc 12 section 7 class as the review queue and auth.audit above: an operator's read of which IP-trust and cookie strategy is live, not a capability an agent retrieves. The response enumerates named fields rather than serialising settings, so it can never leak a credential, but it stays an authenticated door read: an unauthenticated caller has nothing to gain from seeing another human's transport-trust posture. |
| `setup.tofu` | `POST /api/v1/setup`<br>`GET /api/v1/setup/status`<br>`GET /api/v1/setup/fs/list`<br>`GET /api/v1/setup/fs/roots`<br>`POST /api/v1/setup/probe-models` | — | REST single-door | Trust-on-first-use admin provisioning (invariant 21). It writes the admin password hash and the provider credentials and browses the host filesystem to choose a repo root; a twin would make the TOFU window seizable by any LAN peer, which is the one thing the no-pre-shared-secret design depends on not happening. |
| `system.fs_browse` | `GET /api/v1/system/fs/list`<br>`GET /api/v1/system/fs/roots` | — | REST single-door | Authenticated host-filesystem browse behind the repo-path picker. Directory listing over an unauthenticated door is a disclosure primitive with no offsetting agent benefit (invariant 20). |
| `config.runtime` | `GET /api/v1/config/classification-areas`<br>`GET /api/v1/config/feature-flags`<br>`PUT /api/v1/config/feature-flags`<br>`GET /api/v1/config/llm`<br>`POST /api/v1/config/llm`<br>`GET /api/v1/config/repo-allowlist`<br>`PUT /api/v1/config/repo-allowlist`<br>`GET /api/v1/config/repos-path`<br>`PUT /api/v1/config/repos-path`<br>`GET /api/v1/config/system-prompts`<br>`PUT /api/v1/config/system-prompts`<br>`GET /api/v1/config/notifications`<br>`PUT /api/v1/config/notifications`<br>`POST /api/v1/config/notifications/test`<br>`GET /api/v1/config/theme`<br>`PUT /api/v1/config/theme`<br>`GET /api/v1/config/verification-ladder`<br>`PUT /api/v1/config/verification-ladder` | — | REST single-door | Operator configuration -- provider credentials, feature flags, the repo allowlist, the repos path, the system prompts. Doc 12 section 3's confirmed-power rule generalises: the unauthenticated LAN door must never carry a power the REST door reserves for an authenticated human, and the read half alone would hand out the provider API key. |
| `config.llm_providers` | `GET /api/v1/config/llm-providers`<br>`POST /api/v1/config/llm-providers`<br>`PUT /api/v1/config/llm-providers/{name}`<br>`DELETE /api/v1/config/llm-providers/{name}`<br>`POST /api/v1/config/llm-providers/probe-models`<br>`POST /api/v1/config/llm-providers/{name}/probe-models` | — | REST single-door | Provider management is operator configuration, not an agent capability -- the same posture as config.runtime, split into its own surface because it is a distinct resource. An agent has no business rotating the operator's vendor credentials, and /mcp is unauthenticated on a local-network trust model, so putting credential writes there would be a genuine security regression. |
| `analytics.observability` | `GET /api/v1/analytics/overview`<br>`GET /api/v1/analytics/pipeline-logs` | — | REST single-door | Human-observability reads behind the dashboard (doc 12 section 7's sanctioned class): aggregate activity over a date window and the raw ingest log, which is a view of how the box is running rather than knowledge an agent retrieves. |
| `analytics.reprocess` | `POST /api/v1/analytics/reprocess`<br>`POST /api/v1/analytics/reprocess/stream` | — | REST single-door | A whole-corpus reprocess is unbounded operator maintenance that spends the configured provider budget and rewrites every memory's graph. The reasoning that keeps ratification off the MCP door (doc 12 section 3) keeps this off it: an unauthenticated caller must not be able to spend the operator's money or churn the whole corpus. |
| `events.read` | `GET /api/v1/events`<br>`GET /api/v1/events/calendar`<br>`GET /api/v1/events/timeline` | — | REST single-door | Stated in doc 12 section 7 verbatim, and the canonical example of the sanctioned exception: an observability and curation surface a human consumes to reconstruct history, not an agent capability, and the raw stream would leak cross-project operational detail with no isolation benefit. |
| `graph.candidate_read` | `GET /api/v1/graph/full`<br>`GET /api/v1/graph/unified`<br>`GET /api/v1/graph/entities`<br>`GET /api/v1/graph/entities/{entity_id}/neighbors`<br>`GET /api/v1/graph/memory-context/{memory_id}` | — | REST single-door | The L1 candidate graph, served as node-and-edge payloads the UI canvas lays out client-side. Doc 12 section 4 fixes L1 as never directly served on a retrieval surface; the agent-facing path to the same knowledge is memory_search at L0 and, target-new, the vault family at L2/L3. |
| `jobs.control` | `GET /api/v1/jobs`<br>`PUT /api/v1/jobs/{key}`<br>`PUT /api/v1/jobs/{key}/config`<br>`POST /api/v1/jobs/{key}/trigger`<br>`GET /api/v1/jobs/{key}/runs` | — | REST single-door | Scheduler control. Triggering or reconfiguring a job is remote control of the box's background work -- expired_memory_cleanup deletes rows and graph_orphan_cleanup prunes the graph -- so it stays behind the authenticated door. |
| `pipeline.observability` | `GET /api/v1/pipeline`<br>`GET /api/v1/pipeline/metrics` | — | REST single-door | Human-observability read behind the pipeline dashboard: configuration echo and per-phase metrics, an operator's view of the box's health rather than knowledge an agent retrieves. |
| `pipeline_failures.triage` | `GET /api/v1/pipeline-failures`<br>`GET /api/v1/pipeline-failures/counts`<br>`GET /api/v1/pipeline-failures/{failure_id}`<br>`DELETE /api/v1/pipeline-failures/{failure_id}`<br>`POST /api/v1/pipeline-failures/{failure_id}/retry`<br>`POST /api/v1/pipeline-failures/retry-all` | — | REST single-door | Operator triage and remediation: the retry doors re-run extraction and spend the provider budget, and the listing is a health view for the human. An agent learns its own capture's fate from the pipeline websocket and its ack, not from another caller's failure queue. |
| `dream_digest.undo` | `GET /api/v1/dream-digest/cycles`<br>`GET /api/v1/dream-digest/cycles/{cycle_id}`<br>`POST /api/v1/dream-digest/actions/{event_id}/undo`<br>`POST /api/v1/dream-digest/cycles/{cycle_id}/undo` | — | REST single-door | Curation, not an agent capability, and the same conflict-of-interest reasoning doc 12 section 1 applies to the review queue applies here more sharply. Doc 08 section 7 makes undo an authenticated human act over what consolidation did overnight; an agent reversing the consolidation of its own memories is the agent editing the record it is measured against. The read half is the same human-observability shape as pipeline_failures.triage -- a digest a person reviews -- and an agent has no use for another actor's nightly cycle report. Invariant 15 is the second, independent reason: the dream job family may not be reachable from capture or retrieval, and an MCP twin would put a door onto that stream inside the agent surface. |
| `review_queue.triage` | `GET /api/v1/review-queue/facts`<br>`GET /api/v1/review-queue/articles`<br>`GET /api/v1/review-queue/counts`<br>`POST /api/v1/review-queue/facts/{fact_id}/reject`<br>`POST /api/v1/review-queue/facts/{fact_id}/dismiss-suspicion` | — | REST single-door | Doc 12 section 1 names the review queue as one of the reshape's two deliberate single-door kinds -- a human-observability read, not a confirmed-power write -- and section 3 assigns the agent-facing capability to a separate tool family, dispute_inspect (both-sides detail on one disputed fact or article), never to this backlog view: 'the review-queue read is a curation surface, not an agent capability ... an agent triaging its own truth backlog is a conflict of interest the design declines.' This surface is the pipeline_failures.triage shape (doc 08 section 6) over facts and articles. review_state still has no writer here (T2.62 owns its sole derived one). T2.63 added the one action door: reject withdraws belief and journals a human_verdict event so doc 17 section 5.1's false-promotion audit has a human-rejected half at all. It stays REST-only for the same conflict-of-interest reason the reads do, and more sharply -- an agent rejecting the facts it is measured against is the adjudication analogue of grading its own work. |
| `knowledge.facts_list` | `GET /api/v1/knowledge/facts` | — | REST single-door | Doc 12 section 3 assigns the agent one list-shaped vault read and it is knowledge_search, not a fact list: a composed, ranked, badged answer to a query, with the memories that source each fact nested under it and an envelope naming what was excluded. This route answers a different question -- doc 13 section 5.1's Facts tab, the vault's own bookkeeping in arrival order: the bi-temporal belief window including window-closed rows that are retained history, and exact-match filters on subject, relation, object and verification_status. There is no query for an agent to aim at it, and an agent that paged the vault would be reading the corpus rather than retrieving from it. T2.72 replaced the trust-posture argument this row used to carry, which was weak for the reason its reviewer gave: every two-door read on this table already pairs an unauthenticated tool with an authenticated route, so posture does not decide door count. The detail half of this surface is no longer here -- it is knowledge.fact_detail, two-door with fact_get. |
| `knowledge.ratify` | `POST /api/v1/knowledge/facts/{fact_id}/ratify` | — | REST single-door | The confirmed-power write, and doc 12 section 3 names it as the first of the reshape's two sanctioned single-door kinds in so many words: 'the unauthenticated LAN MCP surface must never carry confirmed power'. Unlike knowledge.facts_list, this row's reason IS the trust posture and the posture argument holds here where it did not there -- the two-door reads pair an unauthenticated tool with an authenticated route because reading the vault is a capability an agent should have, whereas confirmed is by construction the one rung the machine cannot reach on its own (doc 08 section 4.4). A twin would let any LAN peer forge the human's imprimatur, which is the forged-ratification threat doc 18 section 2 tables. Recorded here so nobody completes the symmetry later. |
| `api_keys.manage` | `POST /api/v1/api-keys`<br>`GET /api/v1/api-keys`<br>`DELETE /api/v1/api-keys/{key_id}` | — | REST single-door | The second of doc 12 section 3's sanctioned single-door kinds, and doc 18 section 5 fixes it in the same words it uses for ratification: 'a credential mint is confirmed-grade power'. The posture argument is the one that holds for knowledge.ratify and not for the vault reads -- a twin on the unauthenticated LAN MCP door would let any peer on the network mint itself a credential, which is strictly worse than the surface it would be minting access to. It is also why 'admin' is not the scope of this surface: a key holding admin still cannot reach it, so a stolen key cannot mint its own successor and outlive its revocation (T4.01). Recorded here so nobody completes the symmetry later. |
| `knowledge.topics` | `GET /api/v1/knowledge/topics`<br>`GET /api/v1/knowledge/topics/{label}`<br>`GET /api/v1/knowledge/topics/pin-suggestions`<br>`POST /api/v1/knowledge/topics/pin-suggestions/accept`<br>`POST /api/v1/knowledge/topics/pin-suggestions/dismiss` | — | REST single-door | T2.39a's door onto T2.20's topic_browsing.py / pin_suggestions.py, both shipped with zero callers anywhere in app/ until this task. Doc 12 section 3's tool table names exactly one MCP-exposed topic capability -- memory_overview, the project-wide map-reduce (already two-door, knowledge.overview above) -- and assigns no tool to per-topic browsing or to the pin-suggestion diff/accept/dismiss flow doc 09 section 3.4 describes. Accept/dismiss are also a human curation decision about what feeds article synthesis, the same review-a-suggestion shape hygiene_queue.triage and review_queue.reject keep off the unauthenticated MCP surface rather than a query an agent has a reason to aim at. If a later doc revision names an agent-facing tool here the way T2.72 added fact_get for knowledge.facts_list, this row moves to two-door then, not before. |
| `hygiene_queue.triage` | `GET /api/v1/hygiene-queue/duplicates`<br>`GET /api/v1/hygiene-queue/low-confidence`<br>`GET /api/v1/hygiene-queue/expiring-soon`<br>`GET /api/v1/hygiene-queue/superseded`<br>`GET /api/v1/hygiene-queue/counts`<br>`POST /api/v1/hygiene-queue/bulk/supersede`<br>`POST /api/v1/hygiene-queue/bulk/prune`<br>`POST /api/v1/hygiene-queue/bulk/confirm-dedup` | — | REST single-door | The same review_queue.triage shape (doc 08 section 6) over memories/memory_relations instead of facts/articles: a human curation surface for housekeeping, not an agent capability. The bulk actions are a human deciding what to retire or triage in its own store, the same conflict-of-interest review_queue's reject door declines to hand an agent; there is no dispute_inspect-shaped agent need for a housekeeping backlog either. |
| `buffer.triage` | `GET /api/v1/memory-buffer`<br>`GET /api/v1/memory-buffer/stats`<br>`DELETE /api/v1/memory-buffer/{buffer_id}`<br>`POST /api/v1/memory-buffer/{buffer_id}/requeue` | — | REST single-door | The operator's view of the Tier-A capture buffer plus poison-row remediation. An agent already learns its own capture's fate from memory_add's ack (doc 05 section 2); another caller's buffered rows, and the power to drop or requeue them, are not its business. |
| `reembed.maintenance` | `POST /api/v1/reembed/all`<br>`POST /api/v1/reembed/memories`<br>`POST /api/v1/reembed/entities`<br>`POST /api/v1/reembed/code-chunks`<br>`POST /api/v1/reembed/prune-cache`<br>`GET /api/v1/reembed/obsolete-counts`<br>`GET /api/v1/reembed/obsolete/memories`<br>`GET /api/v1/reembed/obsolete/entities`<br>`GET /api/v1/reembed/obsolete/code-chunks` | — | REST single-door | Expensive, destructive maintenance around an embedder rotation: it re-embeds the whole corpus into a new fingerprint partition and prunes the entity cache. Operator power, authenticated door only; the obsolete-listings exist to let the human decide whether to pay for it. |
| `vectors.projection` | `GET /api/v1/vectors/projection` | — | REST single-door | A 2-D projection computed purely for the UI's scatter plot. It is a rendering aid over embeddings an agent already reaches as ranked results through memory_search, so a twin would ship coordinates no agent has a use for. |
| `chat.console` | `POST /api/v1/chat/completions`<br>`GET /api/v1/chat/conversations`<br>`POST /api/v1/chat/conversations`<br>`GET /api/v1/chat/conversations/{conversation_id}`<br>`PATCH /api/v1/chat/conversations/{conversation_id}`<br>`DELETE /api/v1/chat/conversations/{conversation_id}` | — | REST single-door | The UI's chat console runs on the box's own configured LLM. An MCP client brings its own model, and a twin would turn the unauthenticated door into an open proxy spending the operator's provider credit. |
| `memory.bulk_delete` | `POST /api/v1/memories/delete` | — | REST single-door | The UI's multi-select delete. An agent removes the rows it knows by id through memory_delete; a mass-erasure primitive on an unauthenticated door is exactly the power doc 12 section 3 keeps behind authentication. |
| `memory.merge` | `POST /api/v1/memories/{memory_id}/merge` | — | REST single-door | A human curation decision that collapses two memories and discards content -- the same conflict of interest doc 12 section 3 declines for the review queue. The agent gets the read (memory_find_duplicates) and the human makes the call. |
| `repo.manage` | `POST /api/v1/repos`<br>`GET /api/v1/repos/stats`<br>`GET /api/v1/repos/{repo_id}`<br>`PUT /api/v1/repos/{repo_id}`<br>`DELETE /api/v1/repos/{repo_id}`<br>`POST /api/v1/repos/{repo_id}/reindex`<br>`POST /api/v1/repos/{repo_id}/webhook`<br>`GET /api/v1/repos/{repo_id}/tasks`<br>`DELETE /api/v1/repos/{repo_id}/tasks/{task_id}` | — | REST single-door | Registration and indexing control: creating a repo makes the box clone and index an arbitrary URL or path under the operator's allowlist, and reindex spends the provider budget. The reads carry indexing-operations detail -- index debt, the task queue, the HEAD sha -- that belongs to the operator dashboard, while list_repos already gives an agent the id, name and counts it needs to scope a code query. The push webhook (T4.05, doc 10 §5) is the same reindex control surfaced for an external CI system rather than the UI's Reindex button -- an externally reachable receiver, gated on the same `admin` scope, calling the identical `CodePipeline.run` polling and the Reindex button both call; it earns no MCP twin for the same reason reindex doesn't. |
| `code.files` | `GET /api/v1/code/files/{repo_id}` | — | REST single-door | A file-tree browse for the code explorer. The agent-facing equivalent is code_file_symbols, which answers 'what is in this file' directly, so a twin would add a browse round-trip and no capability. |
| `code.repo_graph` | `GET /api/v1/code/graph/{repo_id}` | — | REST single-door | The whole-repo node-and-edge dump the UI canvas lays out client-side. The agent-facing projections of the very same rows are the six code_* graph tools below, which answer a question instead of shipping a graph; a tool twin would hand an agent a repo-sized payload to traverse itself. |
| `code.wiki` | `GET /api/v1/code/wiki/{repo_id}` | — | REST single-door | Generated repo prose rendered by the UI. It is strictly read-only -- generation is an explicit POST /repos/{id}/reindex?generate_wiki=true, never a GET side effect -- and an agent reads the code graph and the symbols themselves rather than a summary written for a human. |
| `health.liveness` | `GET /health` | — | REST single-door | An unauthenticated liveness probe for the container runtime. A tool twin is meaningless by construction: reaching the tool already proves the server is up. |
| `code.context` | — | `code_context` | MCP single-door | An agent-shaped projection -- callers, callees, heritage, community, processes for one symbol -- of rows the REST door serves whole through GET /code/graph/{repo_id}. No knowledge is REST-unreachable; what is single-door is the filtered query, because the UI's consumer is a canvas that wants the graph and the agent's consumer is a prompt that wants the answer. Doc 12 section 3 lists this tool as having a REST twin under /code or /repos today. No route answers this query; the claim is true of the underlying rows, not of the query. Escalated by T1.42d, not resolved. |
| `code.dependencies` | — | `code_dependencies` | MCP single-door | The imports edges for one repo or one file, filtered server-side out of the same code_edges rows GET /code/graph/{repo_id} ships whole to the canvas. Single-door in shape, not in capability. Doc 12 section 3 lists this tool as having a REST twin under /code or /repos today. No route answers this query; the claim is true of the underlying rows, not of the query. Escalated by T1.42d, not resolved. |
| `code.communities` | — | `code_communities` | MCP single-door | The Leiden community nodes for one repo, filtered out of the same code_graph_nodes rows GET /code/graph/{repo_id} ships whole. The UI renders communities as clusters on the canvas; the agent wants them as a list. Doc 12 section 3 lists this tool as having a REST twin under /code or /repos today. No route answers this query; the claim is true of the underlying rows, not of the query. Escalated by T1.42d, not resolved. |
| `code.processes` | — | `code_processes` | MCP single-door | The traced execution flows for one repo with their ordered steps, filtered out of the same code_graph_nodes and code_edges rows GET /code/graph/{repo_id} ships whole. Single-door in shape, not in capability. Doc 12 section 3 lists this tool as having a REST twin under /code or /repos today. No route answers this query; the claim is true of the underlying rows, not of the query. Escalated by T1.42d, not resolved. |
| `code.rename` | — | `code_rename` | MCP single-door | A cross-file reference sweep with a per-reference confidence, assembled from the definition rows and the call, heritage and import edges the REST door serves whole. It exists to drive an agent's edit; the UI has no rename view for a twin to feed. Doc 12 section 3 lists this tool as having a REST twin under /code or /repos today. No route answers this query; the claim is true of the underlying rows, not of the query. Escalated by T1.42d, not resolved. |
| `research.run` | — | `research_run` | MCP single-door | The door files evidence its caller gathered, and darkmem has no evidence gatherer by design -- a model without web access would invent its sources. So the caller has to be the gatherer, which an MCP agent is and neither REST caller is: the SPA and the generated three-verb SDK cannot search the web, so the honest REST shape of 'research subject S into project P' is a route that gathers server-side, i.e. the in-tree gatherer the design refuses. A second door would also be the second ingestion path T3.07 was built to avoid. Not a capture twin either: the tool takes no source, no origin_key and no ctx, so a caller cannot file through it while looking like ordinary capture, and it refuses until the owner enables the research config row (T3.27, doc 09 section 6). |
| `code.changes` | — | `code_changes` | MCP single-door | The only genuinely single-door capability in the code family: it shells out to git in the repo working directory and reports the uncommitted diff against the indexed symbols. Every REST read and the whole indexed graph are commit-based, so no route carries this state and the UI has no working-tree view. It serves the agent editing the tree right now. Doc 12 section 3 lists this tool as having a REST twin under /code or /repos today. It has none, and unlike its five siblings the underlying state is not REST-reachable either. Escalated by T1.42d, not resolved. |
<!-- END GENERATED PARITY TABLE -->

## Findings this audit raises

### 1. `memory_stats` was a live divergence — closed by **T1.42f**

Formerly the one row marked divergent. `GET /api/v1/analytics/stats` and the
`memory_stats` tool each hand-rolled the same three counts, and they had
already drifted where a caller could see it: the route also returned
`entities` and `relationships` from `PostgresGraphRepository.get_stats()`,
the tool returned neither. Neither door called a service — the route computed
inline — so there was nothing to point the tool at. T1.42f lifted the
computation (counts plus the guarded graph pair) into
`AnalyticsService.get_stats()` and moved both doors onto it; the row is now
`two-door`. Found by T1.42c, opened as T1.42f by this audit, closed by T1.42f.

### 2. Doc 12 §3 claims six REST twins that do not exist — escalated, not resolved

Doc 12 §3 lists the code family and states that each of the eleven tools comes
"with a REST twin under `/code` or `/repos`", tagged **(exists today)**. Six of
them have no such route: `code_context`, `code_dependencies`, `code_changes`,
`code_communities`, `code_processes`, `code_rename`.

The claim is true of the *rows* and false of the *query*. Five of the six read
`code_edges` / `code_graph_nodes`, which `GET /code/graph/{repo_id}` serves
whole to the UI canvas, so no knowledge is REST-unreachable — what is
single-door is the filtered projection. `code_changes` is the exception: it
shells out to `git` in the repo working directory, and no REST read carries
uncommitted state at all.

Each of the six therefore carries a stated single-door reason above. But a
design doc asserting a shipped twin that does not exist is an invariant-23
(scaffolding-not-substrate) problem, and correcting a design doc is a Tier-3
amendment. **This audit records the divergence and does not edit doc 12.**

### 3. `code_symbol` / `code_file_symbols` are a latent repeat of the T1.42c defect

Marked two-door, and genuinely reachable from both doors — but each tool builds
its own SQLAlchemy query instead of spending `CodeQueryService.list_symbols`.
No row differs today, so this is not yet a divergence; it is the same
parallel-implementation setup T1.42c found *already realised* on `code_search`
and `code_blast_radius`. Delegating is not a behaviour-preserving one-liner
(the service caps at `limit=50`; the tools are uncapped), so it needs an owner
rather than an opportunistic edit.

### 4. No capability was found sequenced MCP-behind-REST

The direction invariant 17 most fears — a capability shipped on REST with the
MCP twin "planned" — did not appear. Every REST-single-door row above is
single-door for a trust, curation, operator-power or rendering reason, not
because the tool has not been written yet. The asymmetries that do exist run
the other way: six code tools ahead of their routes.

**T2.72 (2026-08-03) found the one instance where it nearly did, and closed
it.** `GET /api/v1/knowledge/facts/{fact_id}` shipped with T2.36a filed
REST-only on a trust-posture argument, while doc 12 §2 assigns that exact path
as `fact_get`'s twin and doc 12 §3 puts the agent-facing vault reads on
`fact_get` and `knowledge_search`. Nothing in the corpus owned either tool, so
the row was one task away from being the shape this finding says did not
appear. It was not a live breach — parity is not violated by a surface absent
on both doors' agent side — but the *reason* was wrong rather than merely
thin: every two-door read on this table already pairs an unauthenticated tool
with an authenticated route, so posture does not decide door count. The detail
half is now `knowledge.fact_detail`, two-door, both ends serialising through
one `FactDetailResponse`; the list half stays REST-only for doc 12's reason,
which is that the agent's list-shaped vault read is `knowledge_search`.

### 5. `knowledge_search` was a seventh MCP-ahead-of-REST row — T2.80 closed it

T2.72 shipped `knowledge_search`, doc 12 §3's composed four-layer read, and
filed it MCP-single-door for the same agent-shaped-projection reason the six
code tools carry: the rows are REST-reachable in their own key spaces (L0
through `POST /api/v1/memories/search`, L2 through `GET
/api/v1/knowledge/facts`) and what is single-door is the cross-layer ranked
question. It recorded, rather than resolved, that doc 12 §2 assigns a twin at
`POST /knowledge/search` which no epic file owned.

**That filing was honest and it was wrong, and T2.80 (2026-08-04) built the
route.** The projection argument does not survive contact with this table's own
precedent: `memory.search` and `code.search` are both two-door, so a ranked
answer over a key space is a capability here and not a projection of one. Filed
as it was, the composed read was the only ranked retrieval in the system with a
single door.

The route spends the serialiser T2.72 placed outside the tool for exactly this
(`knowledge_search_response`), and the degraded payload got the same treatment
(`knowledge_search_unavailable`), so neither the served shape nor the outage
shape has a second producer. Two settlements the route forced rather than
inherited:

- **A composition defect is no longer served as an outage.** Both doors caught
  `RuntimeError`, and the composition raises that base for its own bugs — the
  grouping fixpoint that stopped decreasing, a reranker returning a window of
  the wrong length. Every door now catches only `CompositionUnavailable`, so a
  bug over a healthy vault surfaces as an error rather than as "the vault is
  down". The third door, chat, was narrowed with them.
- **Ranking parity is asserted on the order.** `envelope.reranked` is
  permanently false because the reranker is a door-side constructor argument,
  and the moment one door passed one the two would rank differently while every
  row-shape parity test stayed green. `tests/test_knowledge_search.py` compares
  the id sequences both doors produce over one corpus deep enough that fusion
  depth is load-bearing, and an AST scan fails the build on any door that
  constructs the composition with a reranker of its own.

Note the harmful direction is guarded rather than merely absent, on both vault
surfaces: `test_fact_detail_doors_serve_the_same_row` compares the whole
document from both doors, and the composed read compares the whole document
*and* its order.

## The two kinds of sanctioned single door, and a third this audit names

Doc 12 §1 names two sanctioned kinds: the **confirmed-power writes** (ratify,
review-resolve — target-new, not on the Phase-1 surface yet) and the
**human-observability reads** (the review queue, the events stream). The audit
finds the shipped surface uses three, and the third is not new — it is the same
reasoning applied to a different noun:

1. **Trust boundary.** `/mcp` is unauthenticated on the LAN behind only the Host
   allowlist (invariant 20), so auth, setup, config, filesystem browse, chat
   completions, bulk delete and merge stay on the authenticated door. The rule
   is doc 12 §3's own: the unauthenticated door must never carry a power the
   REST door reserves for an authenticated human.
2. **Human observability and curation.** Events, analytics, the pipeline and
   buffer views, the failure queue, the audit log, the vector projection, the
   L1 graph canvas — a human reconstructing what the box did, not an agent
   retrieving knowledge.
3. **Operator power over cost and state.** Reprocess, reindex, reembed, job
   trigger and job config all spend the operator's provider budget or churn the
   corpus. This is the trust boundary argument applied to money and durability
   rather than to secrets, and it is why these are called out separately here.

The mirrored kind — **agent-shaped projections** of rows the REST door serves
whole — covers the six MCP-single-door code tools. It is the kind doc 12 §3
does not currently name. `knowledge_search` was filed under it by T2.72 and
does not belong there: a projection re-presents rows another door already
serves, and a ranked cross-layer answer is a row set neither other door
produces. T2.80 moved it to two-door rather than widening this kind to cover
it.

# Comprehensive review remediation specification

The owner authorized fixing the validated issues with subagent-driven development on `fix/comprehensive-review`. The reviewed base is `b5a25e6bc0a3e70afdc3cb888416114704e0ca56`. The independent review confirmed 21 findings and qualified 5, retaining 26 items with 6 P1 and 20 P2.

## Scope

Implement the behavioral requirements recorded in the nine task descriptions of the associated plan. Every numbered finding remains tracked in the register. Preserve existing public contracts except for validation/security behavior required by these fixes. No unrelated refactor or new product feature is included.

## Accepted qualifications

- Finding 3 concerns the affected destination's last verified copy; the independent systemd backup family remains separate.
- Finding 5 is P2: stale derived embeddings require freshness checks and can already be repaired by explicit re-embedding.
- Finding 9 must preserve current zero/off feature defaults while making trace diagnostics faithful when supported arms are enabled or hybrid is disabled.
- Finding 13 preserves current owner policy: unchanged HEAD is not a new recurring trigger. Clarify deferred work, prove manual/later-run convergence, and retain explicit debt visibility.
- Finding 26 concerns ambiguous commit acknowledgement. Preserve uncertain files; prove handler behavior without claiming all driver schedules are reproduced.

## Constraints

- Work only on `fix/comprehensive-review`; no commits, staging, merge, push, publication, or production deployment are authorized.
- Do not access live providers or production application/database endpoints. Backend tests use only dedicated development test databases on port 5433.
- Never edit `0001_baseline.py`; avoid schema changes when compatible locks/version checks suffice. Any necessary migration must preserve populated data and requires separate review.
- Keep exactly one runtime worker. Existing provider feature gates, capture identities, append-only journals and fingerprint partitions remain binding.
- Use `apply_patch` for file changes. Do not add inline code comments or one-letter identifiers. Follow scoped repository instructions and existing UI components.
- Agents own disjoint write sets; Task 6 starts after Task 1 because both touch code_pipeline.py. No agent edits CLAUDE.md, the review report, plan, register, or controller ledger; controller reconciles documentation.
- Regression tests must demonstrate the failing behavior before implementation where executable. Concurrency correctness uses production entry points and transaction barriers, not only source scans.

## Completion

All 26 register items must have accepted behavior/contract resolutions and passing covering tests. Native independent reviewers validate each completed task and the whole change. Full validation uses disposable development databases and bounded frontend workers; unavailable checks are recorded explicitly. Authorization to continue execution persists across tasks and skill phase boundaries; routine count-based handoff must not abandon the owner's requested work.

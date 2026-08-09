# T2.110 blind-pass dispatch (both passes received this identical text)

Two labellers, separately dispatched (pass A: Claude Opus; pass B: Claude
Sonnet), no shared context, no access to recorded labels or to each other.
Each saw exactly two files: `new_pairs_blind.json` (the 110 growth pairs,
id/premise/hypothesis only) and a rulebook excerpt = LABELLING.md verbatim
from the top through the reversal-exclusivity table and the ratified
extensions (everything before "## History"), so the full 16-relation table
and the three ratified exclusive-slot extensions were in hand — the exact
omission that voided the first resample attempt.

Dispatch text (identical for both, output path differing):

> You are a blind labeller for an entailment gold set (claim/fact variant).
> You label 110 premise/hypothesis pairs with a three-way verdict, strictly
> by a written rulebook.
>
> HARD CONSTRAINTS — the measurement is destroyed if you break them:
> - Read ONLY these two files, nothing else. Do not open any other file, do
>   not search any repository, do not run any command other than reading
>   these files and writing your output: 1. Rulebook [path] 2. Pairs [path]
> - You have no access to any recorded labels and must not try to find any.
> - Use ONLY the premise. The labeller's world knowledge and what is
>   "obviously true" of homelabs are inadmissible (rulebook, general
>   procedure 2).
>
> TASK: For each of the 110 pairs, decide exactly one verdict — "entailed",
> "contradicted", or "unsupported" — per the rulebook's decision procedures,
> edge rulings (cite them by name: exclusive-slot rule and its three
> ratified extensions, window rule, open-window rule, evaluation-time rule,
> implicature-is-not-contradiction rule, reversal rule with the 16-relation
> reversal-exclusivity table). Pay particular attention to:
> - Contradiction requires exclusion, not absence (general procedure 4).
> - The reversal-exclusivity table decides reversed-relation pairs
>   mechanically by relation semantics.
> - The exclusive-slot rule covers ports, versions of one instance,
>   intervals/schedules, buckets holding a state file, token
>   lifetimes/retention, and the three ratified extensions (host/platform of
>   a single named instance, IS_A kind, object of a named replacement).
> - Score the whole hypothesis: a conjunction with one unsupported conjunct
>   is unsupported.
>
> OUTPUT: Write a single JSON file to [per-pass path] containing a JSON
> array of exactly 110 objects, one per pair, in the input order:
> [{"id": "eg-0242", "verdict": "...", "rule": "..."}, ...]

Merge (the stated Layer-2 rule, `entailment_adjudication.merge_blind_passes`):
pass A vs recorded 109/110 = 0.9909; pass B vs recorded 110/110 = 1.0000;
pass A vs pass B 109/110 = 0.9909. 109 flipped to `adjudicated`; eg-0308
escalated untouched to `entailment/escalation_queue.json`.

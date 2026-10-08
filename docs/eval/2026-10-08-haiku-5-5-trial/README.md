# Haiku 5.5 trial (2026-10-08)

Haiku 5.5 runs on Darkmem inputs. Report: https://claude.ai/artifact/CyrBes36jXK7UELN4AXmTN

Run from this directory with `backend/.venv/bin/python`. Export `AK` (Anthropic key) and
`SSL_CERT_FILE` first; keys are never stored here.

- `haiku_bench.py <nothink|low|medium> <gold.json|gold_heldout.json>`: extraction F1 bench using
  `ExtractionService.build_extraction_request`, `clean_extraction` and `run_bench`'s scorer.
- `rerank.py <nothink|default|low>`: reranker AUC/MRR on 40 retrieval-gold queries (seed 7) with
  6 lexical hard negatives each, parsed with the reranker's own bare `json.loads`.
- `summ.py <nothink|default>`: `enrichment_worker.SUMMARY_PROMPT` on 14 functions sampled from
  six service modules (seed 3).

`ds_trial.py <ext gold.json|ext gold_heldout.json|rerank|summ>` is the DeepSeek twin of all three,
with the seeded `deepseek-flash-*` profiles' request settings. Export `DK` (DeepSeek key). Its
outputs are the `ds_*.json` files (paired run, 2026-10-08, DeepSeek peak window).

`claude_trial.py <model> <off|low|medium|high> <ext gold.json|rerank [max_tokens]|summ>` runs the same
three tests on any Claude model (Sonnet 5.5 and Opus 5.5 so far; `off` maps to each model's
thinking-off mode). Outputs are `<model>_<think>_*.json`; `*_run2/3` are repeat runs for stability.

`reason_trial.py <model> <think> <fullctx|qa>` tests the reasoning purpose: benchlib's full-context
ranking arm (102 gold queries, retrieval scorer) and `MemoryService.reason`'s prompt on 30 gold
questions with and without their answering memories. `judge.py <judge> <qa.json...>` grades the Q&A
answers blind; it was run with `claude-opus-5-5` and `deepseek-v4-pro` (`judged_*.json`).

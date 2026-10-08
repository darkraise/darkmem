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

DeepSeek was not run live: the cloud environment blocked api.deepseek.com. A paired run needs a
DeepSeek twin of each script (OpenAI-compat, `temperature: 0`, `thinking: {type: disabled}`,
`response_format: json_object`, the per-content seed).

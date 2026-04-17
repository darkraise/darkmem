"""ML-based extraction service.

Mirrors :class:`app.services.extraction.ExtractionService`'s contract so it
can be swapped in behind the ``ml_extraction`` feature flag. The output is
normalized through the same :func:`clean_extraction` helper, so downstream
graph dedup and direction validation see the exact same canonical shape.

Pipeline:
    1. GLiNER span detector proposes candidate entity spans (single label).
    2. NMS drops overlapping spans, keeping the highest-score per region.
    3. ModernBERT typer classifies each span (``[ENT]...[/ENT]`` markers).
    4. REBEL seq2seq reads text + entity hint and emits ``<triplet>`` tuples.
    5. REL_MAP collapses 30 relation types to 10.
    6. :func:`clean_extraction` normalizes names, dedupes, and validates direction.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import ml_pipeline_settings
from app.services.extraction import clean_extraction
from app.services.ml_models import MLModels, get_ml_models
from app.taxonomy import normalize_entity_type, normalize_relation_type

logger = logging.getLogger(__name__)


_TYPER_LABELS_10 = [
    "tool",
    "service",
    "database",
    "language",
    "protocol",
    "project",
    "algorithm",
    "artifact",
    "concept",
    "entity",
]

_MAX_CONTENT_CHARS = 6000


def _nms_spans(spans: list[dict], iou_threshold: float) -> list[dict]:
    """Non-max suppression on GLiNER span candidates.

    Sort by score descending; drop any span whose character-level IoU with a
    kept span exceeds the threshold.
    """
    if not spans:
        return []
    ordered = sorted(spans, key=lambda s: -float(s.get("score", 0.0)))
    kept: list[dict] = []
    for s in ordered:
        s_start, s_end = int(s["start"]), int(s["end"])
        s_len = max(1, s_end - s_start)
        overlap = False
        for k in kept:
            inter_start = max(s_start, k["start"])
            inter_end = min(s_end, k["end"])
            inter = max(0, inter_end - inter_start)
            union = s_len + (k["end"] - k["start"]) - inter
            if union > 0 and inter / union > iou_threshold:
                overlap = True
                break
        if not overlap:
            kept.append(s)
    return kept


def _build_marked_text(text: str, start: int, end: int) -> str:
    return text[:start] + "[ENT]" + text[start:end] + "[/ENT]" + text[end:]


def _parse_rebel_triplets(decoded: str) -> list[dict]:
    """Parse the REBEL seq2seq decode format into relation dicts.

    Format: ``<triplet> source <subj> target <obj> type`` repeated.
    ``<triplet> NONE`` indicates no relations. Malformed chunks are skipped.
    """
    rels: list[dict] = []
    for chunk in decoded.split("<triplet>"):
        chunk = chunk.strip()
        if not chunk or chunk == "NONE":
            continue
        a = chunk.split("<subj>")
        if len(a) != 2:
            continue
        source = a[0].strip()
        b = a[1].split("<obj>")
        if len(b) != 2:
            continue
        target = b[0].strip()
        rtype = b[1].strip().split("<")[0].strip()
        if source and target and rtype:
            rels.append({"source": source, "target": target, "type": rtype})
    return rels


def _typer_id2label(model: Any) -> dict[int, str]:
    """Return the typer's id->label map, falling back to the canonical 10-type order."""
    raw = getattr(model.config, "id2label", None) or {}
    mapped: dict[int, str] = {}
    for k, v in raw.items():
        try:
            mapped[int(k)] = str(v)
        except (TypeError, ValueError):
            continue
    if mapped and set(mapped.values()) == set(_TYPER_LABELS_10):
        return mapped
    return {i: l for i, l in enumerate(_TYPER_LABELS_10)}


def _run_span_and_type(ml: MLModels, content: str) -> list[dict]:
    """Synchronous Stage 1 + Stage 2: detect spans then classify each.

    Runs inside :func:`asyncio.to_thread` from the async ``extract`` entrypoint.
    """
    import torch  # noqa: PLC0415
    import torch.nn.functional as F  # noqa: PLC0415

    threshold = ml_pipeline_settings.span_threshold
    iou = ml_pipeline_settings.span_nms_iou

    try:
        raw_spans = ml.span.predict_entities(content, ["entity"], threshold=threshold)
    except Exception:
        logger.exception("GLiNER span detection failed")
        return []

    spans = _nms_spans(raw_spans, iou_threshold=iou)
    if not spans:
        return []

    marked = [_build_marked_text(content, int(s["start"]), int(s["end"])) for s in spans]
    id2label = _typer_id2label(ml.typer)
    batch = ml_pipeline_settings.typer_batch_size
    max_len = ml_pipeline_settings.typer_max_length
    abstain = ml_pipeline_settings.typer_abstain_margin

    preds: list[int] = []
    margins: list[float] = []
    for j in range(0, len(marked), batch):
        chunk = marked[j : j + batch]
        enc = ml.typer_tok(chunk, return_tensors="pt", truncation=True, max_length=max_len, padding=True)
        if ml.device == "cuda":
            enc = {k: v.to("cuda") for k, v in enc.items()}
        with torch.no_grad():
            logits = ml.typer(**enc).logits
        probs = F.softmax(logits, dim=-1)
        top2 = probs.topk(2, dim=-1)
        preds.extend(top2.indices[:, 0].tolist())
        margins.extend((top2.values[:, 0] - top2.values[:, 1]).tolist())

    entities: list[dict] = []
    for span_info, pred_id, margin in zip(spans, preds, margins):
        if margin < abstain:
            continue
        start = int(span_info["start"])
        end = int(span_info["end"])
        name = content[start:end]
        etype = normalize_entity_type(id2label.get(int(pred_id), "concept"))
        entities.append({
            "name": name,
            "type": etype,
            "properties": {},
        })
    return entities


def _run_relations(ml: MLModels, content: str, entities: list[dict]) -> list[dict]:
    """Synchronous REBEL decode + REL_MAP collapse."""
    import torch  # noqa: PLC0415

    if not entities:
        return []

    ent_str = ", ".join(f"{e['name']} ({e['type']})" for e in entities)
    prompt = f"{content} | Entities: {ent_str}"

    try:
        tokens = ml.relation_tok(
            prompt,
            return_tensors="pt",
            max_length=ml_pipeline_settings.relation_max_source_length,
            truncation=True,
        )
        if ml.device == "cuda":
            tokens = {k: v.to("cuda") for k, v in tokens.items()}
        with torch.no_grad():
            out = ml.relation.generate(
                **tokens,
                max_length=ml_pipeline_settings.relation_max_target_length,
                num_beams=ml_pipeline_settings.relation_num_beams,
            )
        decoded = ml.relation_tok.decode(out[0], skip_special_tokens=False)
    except Exception:
        logger.exception("REBEL relation extraction failed")
        return []

    entity_names = {e["name"] for e in entities}
    rels_out: list[dict] = []
    for rel in _parse_rebel_triplets(decoded):
        src = rel["source"]
        tgt = rel["target"]
        if src not in entity_names or tgt not in entity_names or src == tgt:
            continue
        rels_out.append({
            "source": src,
            "target": tgt,
            "type": normalize_relation_type(rel["type"]),
            "properties": {},
            "weight": 0.6,
        })
    return rels_out


def _extract_sync(content: str) -> dict:
    ml = get_ml_models()
    entities = _run_span_and_type(ml, content)
    relationships = _run_relations(ml, content, entities)
    return {
        "memory_type": "fact",
        "importance": 0.5,
        "entities": entities,
        "relationships": relationships,
    }


class ExtractionMLService:
    """Drop-in replacement for :class:`app.services.extraction.ExtractionService`.

    The ``system_prompt`` argument is accepted for signature compatibility but
    is ignored — the ML pipeline does not condition on prompts.
    """

    async def extract(self, content: str, system_prompt: str | None = None) -> dict:
        if not content or not content.strip():
            return {
                "memory_type": "fact",
                "importance": 0.5,
                "entities": [],
                "relationships": [],
            }

        trimmed = content[:_MAX_CONTENT_CHARS]
        try:
            raw = await asyncio.to_thread(_extract_sync, trimmed)
        except Exception as exc:
            logger.exception("ML extraction failed")
            return {
                "memory_type": "fact",
                "importance": 0.5,
                "entities": [],
                "relationships": [],
                "_error": f"{type(exc).__name__}: {exc}",
            }

        return clean_extraction(raw, content, is_tool_call=False)

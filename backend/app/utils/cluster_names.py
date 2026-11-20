"""Name graph clusters from their members' tags and entity names, with no model call.

Each cluster gets an optional project prefix and up to three terms ranked by a
class-based TF-IDF: how much of the cluster carries a term, weighted by how rare
the term is across the view.
"""
from __future__ import annotations

import math
import unicodedata
from collections import Counter

from app.taxonomy import MEMORY_TYPES

PREFIX_SHARE = 0.6
MAX_NAME_CHARS = 40
MAX_TERMS = 3
MAX_TERM_CHARS = 30
FOLD_PREFIX_CHARS = 6
SEPARATOR = " · "

_DEFAULT_PROJECT = "default"
_PROJECT_TAG = "project/"
_STOPLIST = frozenset(t.lower() for t in MEMORY_TYPES)


def _key(term: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", term).casefold() if c.isalnum())


def _effective_project(project: str | None, tags: list[str]) -> str:
    if project and project != _DEFAULT_PROJECT:
        return project
    for tag in tags:
        if tag.startswith(_PROJECT_TAG) and len(tag) > len(_PROJECT_TAG):
            return tag[len(_PROJECT_TAG):]
    return _DEFAULT_PROJECT


def _terms(tags: list[str], entities: set[str]) -> dict[str, str]:
    """Spelling key -> the memory's own spelling, first seen in sorted order."""
    out: dict[str, str] = {}
    candidates = [t for t in tags if not t.startswith(_PROJECT_TAG)] + list(entities)
    for term in sorted(t.lower() for t in candidates):
        if term in _STOPLIST or len(term) > MAX_TERM_CHARS:
            continue
        key = _key(term)
        if key and key not in out:
            out[key] = term
    return out


def _overlaps(key: str, chosen: list[str]) -> bool:
    return any(
        key in other
        or other in key
        or key[:FOLD_PREFIX_CHARS] == other[:FOLD_PREFIX_CHARS]
        for other in chosen
    )


def _join(prefix: str | None, terms: list[str]) -> str:
    parts = [prefix] if prefix else []
    name = ""
    for i, part in enumerate(parts + terms):
        candidate = part if not name else name + SEPARATOR + part
        keep_anyway = i == 0 or (prefix is not None and i == 1)
        if len(candidate) > MAX_NAME_CHARS and not keep_anyway:
            break
        name = candidate
    return name


def name_clusters(
    members: dict[int, list[str]],
    tags: dict[str, list[str]],
    projects: dict[str, str | None],
    entity_terms: dict[str, set[str]],
) -> dict[str, str]:
    view = set(tags) | set(projects) | set(entity_terms)
    clustered = {mid for ids in members.values() for mid in ids}
    view |= clustered

    effective = {
        mid: _effective_project(projects.get(mid), tags.get(mid) or [])
        for mid in view
    }
    terms = {
        mid: _terms(tags.get(mid) or [], entity_terms.get(mid) or set())
        for mid in view
    }
    df = Counter(key for mid in view for key in terms[mid])

    clustered_projects = {effective[mid] for mid in clustered}
    multi_project = len(clustered_projects) > 1
    shared_project_key = (
        None if multi_project or not clustered_projects
        else _key(next(iter(clustered_projects)))
    )
    sizes = [len(ids) for ids in members.values() if ids]
    mean_size = sum(sizes) / len(sizes) if sizes else 0.0

    names: dict[str, str] = {}
    for cluster_id, ids in members.items():
        size = len(ids)
        prefix = None
        if multi_project and size:
            counts = Counter(effective[mid] for mid in ids)
            top, top_count = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))
            if top != _DEFAULT_PROJECT and top_count >= PREFIX_SHARE * size:
                prefix = top

        carried = Counter(key for mid in ids for key in terms[mid])
        excluded = {_key(prefix)} if prefix else set()
        if shared_project_key is not None:
            excluded.add(shared_project_key)
        scored = sorted(
            (
                -(count / size) * math.log(1 + mean_size / df[key]),
                key,
            )
            for key, count in carried.items()
            if count >= 2 and key not in excluded
        )

        chosen: list[str] = []
        for _, key in scored:
            if len(chosen) == MAX_TERMS:
                break
            if not _overlaps(key, chosen):
                chosen.append(key)

        spellings = []
        for key in chosen:
            spelled = Counter(terms[mid][key] for mid in ids if key in terms[mid])
            spellings.append(min(spelled.items(), key=lambda kv: (-kv[1], kv[0]))[0])

        name = _join(prefix, spellings)
        names[str(cluster_id)] = name or f"Cluster {cluster_id}"
    return names

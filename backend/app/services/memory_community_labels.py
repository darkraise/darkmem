"""Deterministic community labels from dominant entities (doc 06 §7).

**Why detection labels at all, rather than leaving it to T2.19.** Doc 06 §7's
flowchart puts `label = dominant entities` inside the *Insert* box and
`report_string` in a separate downstream *Report* box, and it requires each
detection run to journal referencing its communities **by label** — which is
impossible unless detection labels. Doc 06 §10's pin-suggestion contract is
likewise keyed on stable dominant-entity labels rather than churning ids. So
this is a pure function over the projection: no model call, nothing to refine.
T2.19 may overwrite the label with a refined one and owns `report_string`.

**Ranking, dedup and tie-breaking read the lowercase `entities.name`;
rendering reads `properties.display_name`** (invariant 7). Ordering on the
display form would make the label a function of whichever memory happened to
capitalise the entity first.

**Collisions matter even though nothing enforces uniqueness.** Without a
`UNIQUE (project, label)` a collision does not merge rows the way the code
detector's composed key could — it does something subtler, making the run's
journal (which references by label) and doc 09's pin-suggestion diff ambiguous.
Resolution is deterministic: widen to the next-ranked entity, and only if that
still collides append an ordinal derived from the community's sorted member
list, which is stable across runs because the node order is.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.services.memory_projection import EntityAssertion

LABEL_SEPARATOR = ", "
LABEL_ENTITY_COUNT = 3
LABEL_WIDENED_ENTITY_COUNT = 4
UNLABELLED = "untitled topic"


@dataclass(frozen=True)
class DominantEntity:
    name: str
    display_name: str | None
    entity_type: str
    members: int
    n_e: int

    @property
    def rendered(self) -> str:
        return self.display_name or self.name

    def as_payload(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "type": self.entity_type,
            "members": self.members,
            "n_e": self.n_e,
        }


@dataclass(frozen=True)
class CommunityLabel:
    label: str
    dominant_entities: tuple[DominantEntity, ...]


def rank_dominant_entities(
    entity_index: Sequence[EntityAssertion],
    member_indices: Iterable[int],
) -> list[DominantEntity]:
    """Most-asserted first; the more specific entity wins a tie.

    `n_e` ascending as the second key is the specificity preference: between
    two entities asserted by the same members, the one fewer memories in the
    project mention describes this community better.
    """
    members = set(member_indices)
    ranked: list[DominantEntity] = []
    for assertion in entity_index:
        hits = sum(1 for idx in assertion.member_indices if idx in members)
        if not hits:
            continue
        ranked.append(
            DominantEntity(
                name=assertion.name,
                display_name=assertion.display_name,
                entity_type=assertion.entity_type,
                members=hits,
                n_e=assertion.n_e,
            )
        )
    ranked.sort(key=lambda e: (-e.members, e.n_e, e.name))

    seen: set[str] = set()
    deduped: list[DominantEntity] = []
    for entity in ranked:
        if entity.name in seen:
            continue
        seen.add(entity.name)
        deduped.append(entity)
    return deduped


def _join(entities: Sequence[DominantEntity]) -> str:
    if not entities:
        return UNLABELLED
    return LABEL_SEPARATOR.join(entity.rendered for entity in entities)


def _collision_groups(labels: Sequence[str]) -> list[list[int]]:
    by_label: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        by_label.setdefault(label, []).append(index)
    return [group for group in by_label.values() if len(group) > 1]


def label_communities(
    entity_index: Sequence[EntityAssertion],
    communities: Sequence[Sequence[int]],
) -> list[CommunityLabel]:
    ranked = [
        rank_dominant_entities(entity_index, members) for members in communities
    ]
    labels = [_join(entities[:LABEL_ENTITY_COUNT]) for entities in ranked]

    for group in _collision_groups(labels):
        for index in group:
            labels[index] = _join(ranked[index][:LABEL_WIDENED_ENTITY_COUNT])

    for group in _collision_groups(labels):
        ordered = sorted(group, key=lambda index: tuple(communities[index]))
        for ordinal, index in enumerate(ordered, start=1):
            labels[index] = f"{labels[index]} ({ordinal})"

    return [
        CommunityLabel(
            label=labels[index],
            dominant_entities=tuple(ranked[index][:LABEL_ENTITY_COUNT]),
        )
        for index in range(len(communities))
    ]

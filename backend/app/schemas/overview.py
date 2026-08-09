"""Wire shape for `memory_overview` (doc 09 §3.3, doc 12 §3) — T2.21.

Deliberately carries **no badge object**. Doc 12 §3's tool table gives this
surface "no badge" because the reduce is a summary of summaries — an
organizational view of what memory holds, not a verified claim — and `kind`
says so in-band rather than leaving a consumer to infer it from the absence
of a field.
"""

from pydantic import BaseModel


class OverviewTopic(BaseModel):
    """One community as the map presents it.

    ``project`` rides every row even though the door is project-scoped: a
    memory-derived row that names the scope it came from stays honest if it
    ever escapes through a consumer nobody enumerated
    (``app/services/content_surfaces.py``).
    """

    project: str
    label: str
    member_count: int
    report_status: str
    report: str | None
    used_in_reduce: bool


class OverviewResponse(BaseModel):
    """The reduce's answer plus the bookkeeping that makes it honest.

    ``reports_omitted`` / ``omitted_labels`` / ``reports_truncated`` are
    invariant 14 on the wire: when the report set exceeds the reduce's
    budget the overview is partial, and it says by how much rather than
    reading as complete. ``reduce_input_chars`` and ``reduce_input_bound``
    publish the measured cost and the bound it is held under — both
    functions of the community count, never of the memory count.
    """

    project: str
    kind: str
    text: str | None
    community_set_hash: str
    generated_at: str
    cached: bool
    model_calls: int
    communities_total: int
    reports_ready: int
    reports_used: int
    reports_omitted: int
    omitted_labels: list[str]
    reports_truncated: int
    reduce_input_chars: int
    reduce_input_bound: int
    topics: list[OverviewTopic]

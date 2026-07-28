import uuid


def compute_triple_key(
    project: str,
    subject_name: str,
    rel_type: str,
    object_name: str,
) -> str:
    """
    Compute the stable identity key for a knowledge triple (fact).

    Canonicalises each input (lowercase, strip, collapse whitespace),
    then computes a UUID5 over the four-tuple joined with a field separator.
    The resulting key is deterministic and invariant to equivalent input
    representations (casing, whitespace variations).

    Args:
        project: Project scope (part of identity).
        subject_name: Subject entity name.
        rel_type: Relation type (predicate).
        object_name: Object entity name.

    Returns:
        String representation of a UUID5.
    """

    def canonicalise(s: str) -> str:
        return " ".join(s.strip().split()).lower()

    canonical_project = canonicalise(project)
    canonical_subject = canonicalise(subject_name)
    canonical_rel = canonicalise(rel_type)
    canonical_object = canonicalise(object_name)

    triple_tuple = "\x1f".join(
        [canonical_project, canonical_subject, canonical_rel, canonical_object]
    )

    triple_uuid = uuid.uuid5(uuid.NAMESPACE_URL, triple_tuple)
    return str(triple_uuid)

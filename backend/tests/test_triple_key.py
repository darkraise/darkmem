import uuid

from app.services.triple_key import compute_triple_key


def test_determinism():
    """Same inputs produce the same key across multiple calls."""
    key1 = compute_triple_key("proj", "postgres", "uses", "docker")
    key2 = compute_triple_key("proj", "postgres", "uses", "docker")
    assert key1 == key2


def test_casing_insensitivity():
    """Casing differences are normalized; keys are identical."""
    key_lower = compute_triple_key("proj", "postgres", "uses", "docker")
    key_mixed = compute_triple_key("proj", "Postgres", "USES", "Docker")
    assert key_lower == key_mixed


def test_whitespace_canonicalisation():
    """Leading, trailing, and internal whitespace are normalized."""
    key_clean = compute_triple_key("proj", "postgres", "uses", "docker")
    key_lead_trail = compute_triple_key("proj", "  postgres  ", "uses", "docker")
    key_internal = compute_triple_key("proj", "post  gres", "uses", "docker")
    key_internal_clean = compute_triple_key("proj", "post gres", "uses", "docker")

    assert key_clean == key_lead_trail
    assert key_internal == key_internal_clean


def test_project_separates_identity():
    """Different projects produce different keys for the same triple."""
    key_a = compute_triple_key("a", "postgres", "uses", "docker")
    key_b = compute_triple_key("b", "postgres", "uses", "docker")
    assert key_a != key_b


def test_rel_type_separates_identity():
    """Different relation types produce different keys for the same entities."""
    key_uses = compute_triple_key("proj", "postgres", "uses", "docker")
    key_deploys = compute_triple_key("proj", "postgres", "deploys", "docker")
    assert key_uses != key_deploys


def test_field_boundary_safety():
    """Field separator prevents collision between different field concatenations."""
    key_a_b_c_d = compute_triple_key("a", "b", "c", "d")
    key_ab_empty_c_d = compute_triple_key("ab", "", "c", "d")
    assert key_a_b_c_d != key_ab_empty_c_d


def test_return_shape():
    """Result is a valid UUID version 5 string."""
    key = compute_triple_key("proj", "postgres", "uses", "docker")
    parsed_uuid = uuid.UUID(key)
    assert parsed_uuid.version == 5

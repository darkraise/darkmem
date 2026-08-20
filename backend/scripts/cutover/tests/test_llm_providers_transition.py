from scripts.cutover.llm_providers_transition import derive

OLD = [
    {"purpose": "embedding", "model": "qwen3-embedding:0.6b", "api_kind": "openai",
     "base_url": "http://192.168.0.196:11434/v1", "api_key": None,
     "dimensions": 1024, "reasoning": False, "params": {}, "classifier_kind": None},
    {"purpose": "extraction", "model": "deepseek-v4-flash", "api_kind": "deepseek",
     "base_url": "https://api.deepseek.com/v1", "api_key": "sk-a",
     "dimensions": None, "reasoning": False, "params": {}, "classifier_kind": None},
    {"purpose": "verification", "model": "gpt-5.5", "api_kind": "deepseek",
     "base_url": "https://api.deepseek.com/v1", "api_key": "sk-a",
     "dimensions": None, "reasoning": False, "params": {}, "classifier_kind": None},
]


def test_distinct_triples_become_distinct_providers():
    providers, _ = derive(OLD)
    assert len({p["name"] for p in providers}) == len(providers)


def test_verification_is_split_onto_its_own_provider():
    """Its base_url and api_kind are the judge's identity; sharing the row puts
    them behind an unrelated edit."""
    providers, purposes = derive(OLD)
    vp = next(p["provider_name"] for p in purposes if p["purpose"] == "verification")
    others = {p["provider_name"] for p in purposes if p["purpose"] != "verification"}
    assert vp not in others


def test_connection_values_are_carried_verbatim():
    providers, purposes = derive(OLD)
    by_name = {p["name"]: p for p in providers}
    for old in OLD:
        new = next(p for p in purposes if p["purpose"] == old["purpose"])
        provider = by_name[new["provider_name"]]
        assert provider["api_kind"] == old["api_kind"]
        assert provider["base_url"] == old["base_url"]
        assert provider["api_key"] == old["api_key"]


def test_derivation_is_deterministic():
    assert derive(OLD) == derive(OLD)

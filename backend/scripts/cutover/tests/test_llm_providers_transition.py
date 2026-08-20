import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.cutover.llm_providers_transition import derive

BACKEND_ROOT = Path(__file__).resolve().parents[3]

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

# Differs from OLD's first two rows only in api_key: None vs "". A sort key
# that folds both to the same value would let their relative provider-name
# assignment depend on set iteration order, which depends on the process
# hash seed.
AMBIGUOUS_NULL_VS_EMPTY = [
    {"purpose": "embedding", "model": "m1", "api_kind": "openai",
     "base_url": "http://shared.example/v1", "api_key": None,
     "dimensions": None, "reasoning": False, "params": {}, "classifier_kind": None},
    {"purpose": "extraction", "model": "m2", "api_kind": "openai",
     "base_url": "http://shared.example/v1", "api_key": "",
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


def _derive_in_subprocess(rows: list[dict], hash_seed: str) -> list:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed
    code = (
        "import json, sys\n"
        "from scripts.cutover.llm_providers_transition import derive\n"
        "rows = json.load(sys.stdin)\n"
        "providers, purposes = derive(rows)\n"
        "json.dump([providers, purposes], sys.stdout)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(rows),
        capture_output=True,
        text=True,
        cwd=BACKEND_ROOT,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


# A wider spread than a single pair: under the pre-fix _sort_key, whichever
# purpose gets the plain generated name splits roughly evenly across seeds,
# so a fixed two-seed comparison can land in the same class by chance and
# pass against the bug it exists to catch — 0 and 42 both happened to name
# "extraction" the plain-name owner under the broken code. Sweeping several
# seeds makes that coincidence unlikely to survive across the whole set.
HASH_SEEDS = ("0", "1", "41", "42", "100")


def test_provider_naming_is_independent_of_hash_seed():
    """derive(OLD) == derive(OLD) inside one test process shares a single
    PYTHONHASHSEED between both calls and cannot see a seed-dependent set
    iteration order; running the ambiguous None-vs-"" dump under several
    seeds in separate processes can."""
    results = [_derive_in_subprocess(AMBIGUOUS_NULL_VS_EMPTY, seed) for seed in HASH_SEEDS]
    assert all(result == results[0] for result in results[1:])


def test_provider_naming_pins_the_expected_owner():
    """Cross-seed equality alone proves stable, not correct: a naming scheme
    that stably (but wrongly) always gave the plain name to "extraction"
    would also pass the sweep above. Pin the actual intended assignment —
    "embedding" (the first row in sorted-triple order once None and ""
    no longer collide) owns the plain generated name; "extraction" gets the
    "-2" suffix."""
    _, purposes = derive(AMBIGUOUS_NULL_VS_EMPTY)
    by_purpose = {p["purpose"]: p["provider_name"] for p in purposes}
    assert by_purpose["embedding"] == "openai-shared.example"
    assert by_purpose["extraction"] == "openai-shared.example-2"


def test_empty_string_base_url_falls_back_to_local():
    rows = [
        {"purpose": "embedding", "model": "m", "api_kind": "openai",
         "base_url": "", "api_key": None,
         "dimensions": None, "reasoning": False, "params": {}, "classifier_kind": None},
    ]
    providers, _ = derive(rows)
    assert providers[0]["name"] == "openai-local"


def test_single_row_dump():
    rows = [OLD[0]]
    providers, purposes = derive(rows)
    assert len(providers) == 1
    assert len(purposes) == 1
    assert purposes[0]["provider_name"] == providers[0]["name"]


def test_dump_without_verification_purpose():
    rows = [row for row in OLD if row["purpose"] != "verification"]
    providers, purposes = derive(rows)
    assert {p["purpose"] for p in purposes} == {"embedding", "extraction"}
    assert all(not name.endswith("-judge") for name in {p["name"] for p in providers})


def test_duplicate_purpose_raises():
    rows = [OLD[0], OLD[0]]
    with pytest.raises(ValueError, match="embedding"):
        derive(rows)

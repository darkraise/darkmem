"""Carry a dumped pre-migration ``llm_purpose_configs`` onto providers.

The deployment runbook's drop-and-recreate procedure dumps
``llm_purpose_configs`` with ``--column-inserts`` from the old schema and
restores it into the new one. That cannot work for this migration: the
dumped rows carry ``api_kind``/``base_url``/``api_key`` columns the new table
no longer has, and even stripped, the insert violates the new
``provider_name`` NOT NULL foreign key, because a freshly recreated database
starts with zero ``llm_providers`` rows.

``derive`` reads the old dump (one dict per purpose, connection fields
inline) and emits both the provider rows the new schema needs and the
purpose rows that reference them by name. ``main`` wraps it for the actual
cutover: JSON dump on stdin, SQL ``INSERT`` statements on stdout, a summary
of what was derived on stderr.

``verification`` always lands on a provider no other purpose references.
Its ``base_url``/``api_kind`` anchor the judge's frozen identity (the
provider-freeze guard elsewhere in this change refuses to let another
purpose join that row), so sharing a triple with another purpose here would
recreate exactly the shared-row state that guard exists to prevent.
"""
from __future__ import annotations

import json
import sys
from urllib.parse import urlparse

CONNECTION_FIELDS = ("api_kind", "base_url", "api_key")
PROVIDER_COLUMNS = ("name", "api_kind", "base_url", "api_key")
PURPOSE_COLUMNS = (
    "purpose",
    "provider_name",
    "model",
    "dimensions",
    "reasoning",
    "params",
    "classifier_kind",
)


def _triple(row: dict) -> tuple:
    return tuple(row[field] for field in CONNECTION_FIELDS)


def _sort_key(triple: tuple) -> tuple:
    # api_key and base_url may be None; None sorts against str in no defined
    # order in Python 3, so blank it out for ordering purposes only — the
    # triple stored on the provider row keeps the real value.
    return tuple("" if value is None else value for value in triple)


def _base_name(api_kind: str, base_url: str | None) -> str:
    hostname = urlparse(base_url).hostname if base_url else None
    return f"{api_kind}-{hostname or 'local'}"


def _dedupe(name: str, taken: set[str]) -> str:
    if name not in taken:
        taken.add(name)
        return name
    suffix = 2
    while f"{name}-{suffix}" in taken:
        suffix += 1
    deduped = f"{name}-{suffix}"
    taken.add(deduped)
    return deduped


def _provider_row(name: str, triple: tuple) -> dict:
    api_kind, base_url, api_key = triple
    return {"name": name, "api_kind": api_kind, "base_url": base_url, "api_key": api_key}


def derive(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    verification_rows = [row for row in rows if row["purpose"] == "verification"]
    other_rows = [row for row in rows if row["purpose"] != "verification"]

    providers: list[dict] = []
    taken_names: set[str] = set()
    triple_to_name: dict[tuple, str] = {}

    other_triples = sorted({_triple(row) for row in other_rows}, key=_sort_key)
    for triple in other_triples:
        name = _dedupe(_base_name(triple[0], triple[1]), taken_names)
        triple_to_name[triple] = name
        providers.append(_provider_row(name, triple))

    verification_name = None
    if verification_rows:
        triple = _triple(verification_rows[0])
        verification_name = _dedupe(_base_name(triple[0], triple[1]) + "-judge", taken_names)
        providers.append(_provider_row(verification_name, triple))

    purposes: list[dict] = []
    for row in sorted(rows, key=lambda row: row["purpose"]):
        if row["purpose"] == "verification":
            provider_name = verification_name
        else:
            provider_name = triple_to_name[_triple(row)]
        purpose_row = {k: v for k, v in row.items() if k not in CONNECTION_FIELDS}
        purpose_row["provider_name"] = provider_name
        purposes.append(purpose_row)

    return providers, purposes


def _sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, dict):
        return "'" + json.dumps(value).replace("'", "''") + "'::jsonb"
    return "'" + str(value).replace("'", "''") + "'"


def _insert_sql(table: str, columns: tuple[str, ...], row: dict) -> str:
    column_list = ", ".join(columns)
    value_list = ", ".join(_sql_literal(row[column]) for column in columns)
    return f"INSERT INTO {table} ({column_list}) VALUES ({value_list});"


def main(argv: list[str] | None = None) -> int:
    rows = json.load(sys.stdin)
    providers, purposes = derive(rows)

    print(
        f"derived {len(providers)} providers from {len(rows)} purpose rows",
        file=sys.stderr,
    )
    for provider in providers:
        used_by = sorted(
            purpose["purpose"]
            for purpose in purposes
            if purpose["provider_name"] == provider["name"]
        )
        print(
            f"  {provider['name']} ({provider['api_kind']}): {', '.join(used_by)}",
            file=sys.stderr,
        )

    for provider in providers:
        print(_insert_sql("llm_providers", PROVIDER_COLUMNS, provider))
    for purpose in purposes:
        print(_insert_sql("llm_purpose_configs", PURPOSE_COLUMNS, purpose))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

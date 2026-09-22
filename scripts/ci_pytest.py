"""Partition pytest's actual collection across isolated CI runners.

Keep whole files together (including class/module fixtures) and preserve pytest's
order within each shard. Balance by collected test count, with deterministic
path-based tie breaking. No filename glob or hand-maintained test list can hide
new tests. This runner must never share a database with another shard.
"""
from __future__ import annotations

import argparse
from collections import Counter


def assign_files(nodeids: list[str], count: int) -> dict[str, int]:
    if count < 1:
        raise ValueError("shard count must be positive")
    weights = Counter(nodeid.split("::", 1)[0] for nodeid in nodeids)
    loads = [0] * count
    assignments = {}
    for path in sorted(weights, key=lambda path: (-weights[path], path)):
        shard = min(range(count), key=lambda index: (loads[index], index))
        assignments[path] = shard
        loads[shard] += weights[path]
    return assignments


class Shard:
    def __init__(self, index: int, count: int):
        self.index, self.count = index, count

    def pytest_collection_modifyitems(self, config, items):
        assignments = assign_files([item.nodeid for item in items], self.count)
        selected, deselected = [], []
        for item in items:
            target = assignments[item.nodeid.split("::", 1)[0]]
            (selected if target == self.index else deselected).append(item)
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
        reporter = config.pluginmanager.get_plugin("terminalreporter")
        if reporter:
            reporter.write_line(
                f"CI shard {self.index + 1}/{self.count}: "
                f"{len(selected)} of {len(selected) + len(deselected)} tests"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", required=True, help="one-based index/total")
    args, pytest_args = parser.parse_known_args()
    try:
        index, count = map(int, args.shard.split("/"))
        if not 1 <= index <= count:
            raise ValueError
    except ValueError:
        parser.error("--shard must be index/total with 1 <= index <= total")
    import pytest

    # Collection failures and empty selections retain pytest's nonzero exit.
    return int(pytest.main(pytest_args, plugins=[Shard(index - 1, count)]))


if __name__ == "__main__":
    raise SystemExit(main())

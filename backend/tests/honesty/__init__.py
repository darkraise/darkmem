"""Backend half of the honesty suite (docs/planning/e2e-test-plan.md).

These specs assert rules that are cheap to state and catastrophic to regress.
They are never deleted and never skipped. They live here rather than in the API
e2e suite because that suite does not exist yet — T1.64 builds it and adopts
them; until then the floor is the only ring that runs them.
"""

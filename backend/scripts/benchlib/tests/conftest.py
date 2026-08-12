import pytest
import pytest_asyncio

# Opt-in via `pytestmark = pytest.mark.usefixtures("_bench_db")`, not autouse:
# modules with no database dependency (e.g. ledger) must stay collectible and
# runnable without a reachable Postgres.
@pytest_asyncio.fixture(scope="session")
async def _bench_db():
    # reset_bench_db imports app modules, so importing bench_db here (which sets
    # DATABASE_URL first) must happen before anything touches app.database.
    from benchlib import bench_db
    await bench_db.reset_bench_db()
    yield
    await bench_db.engine.dispose()


@pytest.fixture(autouse=True)
def _no_test_may_mint_the_qualification_record():
    """Fail any test that writes the production judge-qualification record.

    On 2026-08-08 one did. `test_gate_mode_refuses_the_real_gold_before_any_call`
    ran gate mode with default paths, and its only protection was that the real
    gold was ineligible -- so the run stopped before minting. The moment the
    resample landed and the gold became eligible, the same test sailed past the
    refusal, drove a *stub* orchestrator, and wrote
    `app/services/verification_qualification.json` with the stub's metrics
    (contradiction precision 0.259 against a 0.95 bar) and `gate_eligible: true`.

    The ladder failed closed -- `qualification_state` re-checks every metric
    against its bar, so the forged record qualified nothing -- but a forged
    record sat at the canonical path, untracked and one `git add -A` from being
    committed. The guard that was supposed to prevent this is gold-keyed: the
    recorder refuses the canonical record path for any *other* gold. Against the
    real gold it does not fire, which is precisely the case a test should never
    be able to reach.

    So this is structural rather than a fix to the one test: no test in this
    suite may leave that file behind, whatever it points at.

    Since the 2026-08-12 per-role split there are two such files, and the guard
    covers every role's rather than a named path: a role added to
    ``JUDGE_ROLES`` without a line here would be the one record a test could
    mint unnoticed.
    """
    from app.services import verification_judge as vj

    paths = [vj.qualification_record_path(role) for role in vj.JUDGE_ROLES]
    existed = {path for path in paths if path.exists()}
    yield
    minted = [path for path in paths if path.exists() and path not in existed]
    for path in minted:
        path.unlink()
    if minted:
        raise AssertionError(
            "this test minted the production qualification record(s) at "
            f"{[str(p) for p in minted]} -- they have been removed. A test must "
            "pass an explicit record path; only a real cleared gate run may "
            "write a canonical one."
        )


@pytest.fixture(autouse=True)
def _no_test_may_write_into_the_committed_corpus():
    """Fail any test that leaves a file in the entailment corpus directory.

    The resample runner defaults its raw-reply output to
    `entailment/resample_runs/`, which is committed corpus. A test driving the
    runner without `--raw-dir` therefore wrote a fabricated run into it, and
    one got committed alongside two real ones -- three files, two of them
    evidence and one of them stub output, distinguishable only by reading them.

    Same family as the qualification-record leak above: a production default is
    the wrong default under test, and nothing said so until the artifact
    appeared.
    """
    from benchlib import resample_llm

    before = set(resample_llm.RAW_DIR.glob("*")) if resample_llm.RAW_DIR.exists() else set()
    yield
    after = set(resample_llm.RAW_DIR.glob("*")) if resample_llm.RAW_DIR.exists() else set()
    leaked = after - before
    for path in leaked:
        path.unlink()
    if leaked:
        raise AssertionError(
            f"this test wrote {sorted(p.name for p in leaked)} into the committed "
            f"corpus at {resample_llm.RAW_DIR} -- removed. Pass --raw-dir "
            "(or an explicit output path) so test output lands in tmp_path."
        )

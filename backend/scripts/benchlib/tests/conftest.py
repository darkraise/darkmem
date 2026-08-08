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
    """
    from app.services import verification_judge as vj

    existed = vj.QUALIFICATION_RECORD_PATH.exists()
    yield
    if vj.QUALIFICATION_RECORD_PATH.exists() and not existed:
        vj.QUALIFICATION_RECORD_PATH.unlink()
        raise AssertionError(
            "this test minted the production qualification record at "
            f"{vj.QUALIFICATION_RECORD_PATH} -- it has been removed. A test must "
            "pass an explicit record_path; only a real cleared gate run may "
            "write the canonical one."
        )

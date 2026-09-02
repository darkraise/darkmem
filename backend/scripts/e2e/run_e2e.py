"""The API e2e suite's one documented entry point.

    python scripts/e2e/run_e2e.py

Nothing else needs to be true first: no fresh deployment, no pre-set
password, no already-running server. This script does the drop, the
migrate, the boot and the seed itself, every run (T1.64 plan §2.1) — "not
set up" is the normal starting condition here, not a failure mode.

Sequence: boot a disposable stack (``stack.boot``) → run
``pytest scripts/e2e/tests -q`` against it, with ``E2E_BASE_URL`` and
``E2E_ADMIN_PASSWORD`` set from the booted stack → tear the stack down in a
``finally`` → parse the JUnit summary.

**Exit contract, mirroring ``scripts/gate.sh``'s own exit-2 precedent**
("GATE BLOCKED (exit 2) means a missing toolchain, not a red gate"): if
every collected test skipped, this overrides pytest's own exit code to
**2** (BLOCKED) instead of propagating a green 0 — a suite that ran and
skipped everything has proven nothing, and must not report the same exit
code as a suite that proved something. Any other outcome (a real pass or a
real failure) propagates pytest's exit code unchanged.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from e2e import stack  # noqa: E402

BOOT_PORT = 8321
BLOCKED_EXIT_CODE = 2


def _junit_totals(xml_path: Path) -> tuple[int, int]:
    """Return (total collected, total skipped) from a pytest JUnit report.

    ``<testsuites>`` wraps one-or-more ``<testsuite>`` for a single pytest
    run; sum across all of them rather than assume exactly one.
    """
    root = ET.parse(xml_path).getroot()
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    total = sum(int(s.get("tests", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    return total, skipped


def _extraction_model_is_servable() -> tuple[bool, str]:
    """Is the model the seed pins for `extraction` actually on that endpoint?

    Read straight off ``llm_seed`` rather than out of the booted database,
    because that is exactly what this suite gets: it posts a bare password to
    ``/api/v1/setup`` with no ``purposes``, so nothing overlays the prefill.
    (A human in the wizard never lands here -- ``StepLLM.tsx`` live-probes the
    endpoint and the operator picks from what really exists.)

    Returns (servable, human-readable reason).
    """
    from app.services.llm_quirks import models_probe
    from app.services.llm_seed import DEFAULT_PURPOSE_CONFIGS, OLLAMA_BASE_URL
    from app.services.model_probe import parse_model_list

    seed = next(
        (s for s in DEFAULT_PURPOSE_CONFIGS if s.purpose == "extraction"), None
    )
    if seed is None:
        return True, "no extraction seed to check"

    target = models_probe(seed.api_kind, OLLAMA_BASE_URL, None)
    try:
        import httpx

        response = httpx.get(target.url, headers=target.headers, timeout=10)
        response.raise_for_status()
        served = parse_model_list(response.json())
    except Exception as exc:  # noqa: BLE001 - unreachable is its own answer
        return False, f"could not probe {target.url}: {exc}"

    if seed.model in served:
        return True, f"{seed.model} is served by {target.url}"
    return False, (
        f"the seed pins model {seed.model!r} for extraction, and "
        f"{target.url} does not serve it.\n"
        f"  served there: {', '.join(served) or '(none)'}\n"
        f"  Nothing requires that model -- it is a prefill. But this suite "
        f"takes the seed verbatim, so every extraction call would 404 while "
        f"capture, flush and search all still pass. Pull a generation model "
        f"onto that endpoint, or repoint the seed, rather than reading a "
        f"green run as proof the extraction path works."
    )


def main() -> int:
    # Checked BEFORE the stack boots: a model the endpoint does not serve is a
    # missing toolchain, not a red gate, and `gate.sh`'s exit-2 precedent is
    # what that means. Without this the suite would go RED on every run here,
    # which teaches people to ignore it -- the opposite of the point.
    servable, reason = _extraction_model_is_servable()
    if not servable:
        print(f"BLOCKED: {reason}", file=sys.stderr)
        return BLOCKED_EXIT_CODE
    print(f"extraction model precondition: {reason}")

    password = secrets.token_urlsafe(16)

    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "results.xml"
        handle = stack.boot(port=BOOT_PORT, password=password)
        try:
            env = {
                **os.environ,
                "E2E_BASE_URL": handle.base_url,
                "E2E_ADMIN_PASSWORD": password,
            }
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest", "scripts/e2e/tests", "-q", "-rs",
                    f"--junitxml={xml_path}",
                ],
                cwd=str(BACKEND_DIR),
                env=env,
            )
        finally:
            handle.teardown()

        pytest_rc = result.returncode

        if not xml_path.exists():
            # pytest itself never got far enough to write a report (a
            # collection error, an import error) — that is a real failure,
            # not an all-skipped run, so propagate pytest's own code.
            return pytest_rc

        total, skipped = _junit_totals(xml_path)
        if total > 0 and skipped == total:
            print(
                f"BLOCKED: all {total} collected e2e tests skipped — "
                "no API-level assertion executed this run.",
                file=sys.stderr,
            )
            return BLOCKED_EXIT_CODE

        return pytest_rc


if __name__ == "__main__":
    sys.exit(main())

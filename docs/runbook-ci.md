# CI runtime

The release workflow calls `ci.yml` on every master push. Publishing still
requires the complete reusable workflow to succeed, including all matrix jobs.
No test selection is based on changed files.

Measured on release run `35755669739` before splitting the suites:

| Step | Duration |
| --- | ---: |
| Backend application tests | 604 s |
| Evaluation harness tests (after application tests) | 130 s |
| Frontend unit tests | 417 s |
| Image build, boot and scan (after both suites) | 209 s |

The optimized workflow runs these independently:

- Three backend application shards, each with its own Postgres service. The
  session fixture drops and recreates the schema, so concurrent workers must
  never share a database. `scripts/ci_pytest.py` assigns entire collected files
  by test count, preserving order within each shard. This is a count-based
  balance, not a claim that each test takes the same time. `--durations=20`
  exposes expensive tests for later tuning.
- The evaluation harness in a fourth backend job.
- Four frontend test shards using Vitest's native `--shard` option. Test
  isolation, worker caps and timeouts are unchanged.
- Frontend typecheck, lint and build once, outside the test matrix. Build runs
  Vite directly because the preceding step already ran TypeScript.
- The image build, real entrypoint smoke test and Trivy scan alongside the
  suites. The image stays local to that job until release verification passes.

Python downloads are cached against the dependency files. Docker installs the
Python lockfile before copying package metadata, allowing the release's version
sync to reuse the dependency layer. Release serialization and publication gates
are unchanged.

Validate workflow edits with `actionlint`. The backend partitioner's behavioral
checks run with:

```sh
backend/.venv/bin/python -m unittest discover -s scripts/tests -p test_ci_pytest.py
```

Vitest sharding is documented in its [performance guide](https://vitest.dev/guide/improving-performance.html#sharding).
The Python cache uses [setup-python's dependency caching](https://github.com/actions/setup-python#caching-packages-dependencies).

Splitting jobs trades extra runner setup and potentially more billed runner
minutes for shorter elapsed time. Compare the slowest shard and total workflow
runtime after deployment; runner queue time and registry uploads remain variable.

"""One-off emitter for shared-base batch-241 - technical domain (Python tooling: uv, Poetry, Hatch, PDM, Ruff, mypy, pytest, packaging).

Writes 50 rows to data/v2/shared/batch_241.tmp.jsonl with ids shared-12001..12050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_241.tmp.jsonl"
ID_OFFSET = 12000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Migrated the monorepo from Poetry to uv for dependency resolution; lock times on the dev laptops dropped from forty seconds to under two and CI cache warmups finally fit inside the thirty-second budget.", "decision", "technical", False,
     [("Poetry", "tool"), ("uv", "tool"), ("CI", "infrastructure")],
     [("uv", "Poetry", "REPLACES")],
     "which resolver took over from Poetry in the monorepo and what kind of lock-time speedup justified the swap",
     "uv poetry resolver lock time monorepo ci cache migrate"),
    # --- 2 architecture ---
    ("The packaging layout uses a single pyproject.toml per package with PEP 621 metadata and hatchling as the build backend; setuptools stuck around only for two legacy C-extension packages we haven't ported yet.", "architecture", "technical", False,
     [("pyproject.toml", "file"), ("PEP 621", "protocol"), ("hatchling", "tool"), ("setuptools", "tool")],
     [("hatchling", "setuptools", "REPLACES")],
     "which build backend sits behind the pyproject.toml files and where does setuptools still hang on",
     "pyproject toml pep 621 hatchling setuptools build backend legacy"),
    # --- 3 milestone ---
    ("Ruff replaced the trio of Pyflakes, pycodestyle, and isort across every repo in the org; the single binary shaved about twelve seconds off pre-commit and the shared config lives in the org-wide pyproject.toml fragment.", "milestone", "technical", False,
     [("Ruff", "tool"), ("Pyflakes", "tool"), ("pycodestyle", "tool"), ("isort", "tool"), ("pre-commit", "tool")],
     [("Ruff", "Pyflakes", "REPLACES"), ("Ruff", "isort", "REPLACES")],
     "which linters did Ruff supplant org-wide and what kind of pre-commit time win followed",
     "ruff pyflakes pycodestyle isort pre commit org wide replace"),
    # --- 4 decision ---
    ("Chose pyright over mypy for the new service tree; incremental rechecks on the 120k-line codebase run in about 900 ms versus seven seconds on mypy, and editor feedback finally feels live.", "decision", "technical", False,
     [("pyright", "tool"), ("mypy", "tool")],
     [("pyright", "mypy", "PREFERS")],
     "which type checker did the new service tree pick and what editor-feedback latency pushed the call",
     "pyright mypy type check incremental editor feedback service tree"),
    # --- 5 fact ---
    ("Every repo pins tool versions through pipx so contributors get the same Ruff and mypy builds regardless of what their system Python has; the pinned set lives in scripts/install-dev-tools.sh.", "fact", "technical", False,
     [("pipx", "tool"), ("Ruff", "tool"), ("mypy", "tool"), ("scripts/install-dev-tools.sh", "file")],
     [("pipx", "Ruff", "APPLIES_TO")],
     "how do contributors end up with matching Ruff and mypy versions across machines despite different system Pythons",
     "pipx ruff mypy pin version contributor system python install script"),
    # --- 6 reference ---
    ("Reference for the wheel build matrix: cibuildwheel drives manylinux2014 and musllinux_1_2 images, builds for CPython 3.10 through 3.13, and ships arm64 wheels for macOS and Linux.", "reference", "technical", False,
     [("cibuildwheel", "tool"), ("manylinux2014", "platform"), ("musllinux_1_2", "platform"), ("CPython", "language")],
     [("cibuildwheel", "manylinux2014", "USES")],
     "which wheel build driver and image set publish the cross-platform binaries for the C extensions",
     "cibuildwheel manylinux musllinux cpython arm64 wheel matrix"),
    # --- 7 architecture ---
    ("Test layout puts pytest at the top with hypothesis for property tests under tests/property/ and tox-driven matrices in tox.ini; nose2 is banned in new code and unittest.TestCase only survives where it subclasses a fixture helper.", "architecture", "technical", False,
     [("pytest", "tool"), ("hypothesis", "library"), ("tox", "tool"), ("nose2", "tool"), ("unittest.TestCase", "api"), ("tests/property/", "file")],
     [("pytest", "nose2", "REPLACES")],
     "which test stack drives the repo and what role do tox and hypothesis play alongside pytest",
     "pytest hypothesis tox nose2 unittest testcase property test matrix"),
    # --- 8 preference ---
    ("The team prefers Typer over raw Click for CLIs; type hints become flag definitions automatically and help text stays in sync with function signatures without a separate decorator pass.", "preference", "technical", False,
     [("Typer", "library"), ("Click", "library")],
     [("Typer", "Click", "PREFERS")],
     "which CLI builder does the team default to and what does it buy over plain Click",
     "typer click cli type hint flag help text sync preference"),
    # --- 9 decision ---
    ("Dropped pip-tools in favour of uv pip compile for lockfiles; output is byte-for-byte compatible with the old requirements.txt format so CI scripts didn't need changes beyond the binary swap.", "decision", "technical", False,
     [("pip-tools", "tool"), ("uv pip compile", "tool"), ("requirements.txt", "file"), ("CI", "infrastructure")],
     [("uv pip compile", "pip-tools", "REPLACES")],
     "which lockfile generator replaced pip-tools and what compatibility kept CI untouched",
     "pip tools uv pip compile lockfile requirements txt ci compatible"),
    # --- 10 noise ---
    ("The office coffee grinder started emitting a high-pitched whine on Tuesday and nobody has admitted to owning it.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("Documentation is split: user guides live in MkDocs with the Material theme, while the API reference is generated by Sphinx with autodoc; both sources run through MyST so authors write Markdown end to end.", "architecture", "technical", False,
     [("MkDocs", "tool"), ("Sphinx", "tool"), ("MyST", "framework"), ("Material", "library")],
     [("MyST", "MkDocs", "APPLIES_TO")],
     "how is documentation split between MkDocs and Sphinx and which parser lets authors stay in Markdown",
     "mkdocs sphinx myst material theme autodoc api guide markdown"),
    # --- 12 problem ---
    ("Editable installs broke on the plugin repo because setuptools develop mode skipped the src/ layout; switching the build backend to hatchling fixed the import path and PEP 660 editable wheels just worked.", "problem", "technical", False,
     [("Editable installs", "pattern"), ("setuptools", "tool"), ("src/", "file"), ("hatchling", "tool"), ("PEP 660", "protocol")],
     [("hatchling", "setuptools", "REPLACES")],
     "which build backend fixed editable installs on the src-layout plugin repo and which PEP formalised it",
     "editable install setuptools src layout hatchling pep 660 wheel"),
    # --- 13 decision ---
    ("Picked pydantic v2 over attrs for request models in the API service; the Rust-backed validator runs about six times faster than the v1 Python path and error messages now include the JSON pointer for free.", "decision", "technical", False,
     [("pydantic v2", "library"), ("attrs", "library"), ("JSON pointer", "protocol")],
     [("pydantic v2", "attrs", "PREFERS")],
     "which model library did the API service settle on and what validation speedup did the v2 core deliver",
     "pydantic v2 attrs validator rust speed json pointer api"),
    # --- 14 architecture ---
    ("The virtual-env layout is uv-managed: a .venv at the repo root created by uv venv, pyenv picks the Python version via .python-version, and no global packages land outside that envelope.", "architecture", "technical", False,
     [("uv venv", "tool"), ("pyenv", "tool"), (".venv", "file"), (".python-version", "file")],
     [("uv venv", "pyenv", "USES")],
     "how do uv and pyenv split responsibility for the repo-root virtual env and Python version",
     "uv venv pyenv python version env root global package repo"),
    # --- 15 reference ---
    ("Reference: PEP 517 defines the build-system interface, PEP 518 introduced pyproject.toml's build-system table, and PEP 621 standardised project metadata keys like name, version, and dependencies.", "reference", "technical", False,
     [("PEP 517", "protocol"), ("PEP 518", "protocol"), ("PEP 621", "protocol"), ("pyproject.toml", "file")],
     [("PEP 518", "pyproject.toml", "APPLIES_TO")],
     "which three PEPs together define today's pyproject.toml build and metadata surface",
     "pep 517 518 621 pyproject toml build system metadata interface"),
    # --- 16 milestone ---
    ("Finished the Pipenv eviction: the last internal service moved off Pipfile.lock to uv-managed pyproject.toml last Thursday, so the Pipenv install step can come out of the base Docker image next release.", "milestone", "technical", False,
     [("Pipenv", "tool"), ("Pipfile.lock", "file"), ("uv", "tool"), ("Docker", "tool")],
     [("uv", "Pipenv", "REPLACES")],
     "which legacy dependency manager finally got retired and what does the next Docker image get to drop",
     "pipenv pipfile lock uv docker base image eviction retire"),
    # --- 17 fact ---
    ("All formatting in the org-wide pre-commit config runs the Ruff formatter; black and isort stay in the historical config only for the frozen v2 maintenance branch where we aren't churning diffs.", "fact", "technical", False,
     [("Ruff", "tool"), ("black", "tool"), ("isort", "tool"), ("pre-commit", "tool")],
     [("Ruff", "black", "REPLACES")],
     "which formatter runs in the active pre-commit config and which two legacy tools still linger on a frozen branch",
     "ruff black isort pre commit formatter frozen branch maintain"),
    # --- 18 decision ---
    ("Chose msgspec over pydantic for the hot-path telemetry decoder; zero-copy decoding on the msgpack payload beat pydantic v2 by roughly three times on the same hardware and cut p99 by eight milliseconds.", "decision", "technical", False,
     [("msgspec", "library"), ("pydantic", "library"), ("msgpack", "protocol"), ("telemetry", "service")],
     [("msgspec", "pydantic", "PREFERS")],
     "which decoder replaced pydantic on the telemetry hot path and what p99 latency win followed",
     "msgspec pydantic msgpack telemetry hot path decode p99 zero copy"),
    # --- 19 architecture ---
    ("The Nox session file defines a matrix of Python 3.10 through Python 3.13 crossed with the sqlite and postgres backends; tox.ini survives for the public OSS mirrors that Nox hasn't been ported to yet.", "architecture", "technical", False,
     [("Nox", "tool"), ("tox.ini", "file"), ("sqlite", "database"), ("postgres", "database"), ("Python 3.13", "language")],
     [("Nox", "tox.ini", "REPLACES")],
     "which session runner drives the internal test matrix and why does tox.ini still exist on some mirrors",
     "nox tox ini matrix python sqlite postgres session oss mirror"),
    # --- 20 problem ---
    ("Reference for Rich CLI rendering: a Progress bar writing to a non-TTY log on Windows needs force_terminal=False and usually a fallback to Progress.console.log, otherwise the live-display loop stalls waiting on a terminal handshake.", "reference", "technical", False,
     [("Rich", "library"), ("Windows", "platform"), ("Progress", "api"), ("force_terminal", "config")],
     [],
     "which Rich progress-bar settings does the reference call out for non-TTY Windows log targets",
     "rich progress bar windows tty log force terminal reference fallback"),
    # --- 21 decision ---
    ("Adopted Hatch as the environment and build manager for the public SDK; hatch env for dev, hatch build for sdist and wheel, and plugins for the custom release step replaced a bespoke Makefile.", "decision", "technical", False,
     [("Hatch", "tool"), ("SDK", "project"), ("Makefile", "file"), ("sdist", "file"), ("wheel", "file")],
     [("Hatch", "Makefile", "REPLACES")],
     "which tool replaced the bespoke Makefile for the public SDK and which workflows did it subsume",
     "hatch sdk makefile env build sdist wheel plugin release public"),
    # --- 22 architecture ---
    ("Type checking is split by directory: strict pyright sits on the new code under services/ while the legacy lib/ tree stays on mypy in non-strict mode; pyrefly is being evaluated on a side branch.", "fact", "technical", False,
     [("pyright", "tool"), ("mypy", "tool"), ("pyrefly", "tool"), ("services/", "file"), ("lib/", "file")],
     [("pyright", "mypy", "REPLACES")],
     "how is type-checking split between pyright and mypy across the repo and which newer tool is on evaluation",
     "pyright mypy pyrefly strict service lib directory type check evaluate"),
    # --- 23 milestone ---
    ("Shipped the first conda-forge feedstock for the internal library; miniforge users can now install with mamba in about two seconds versus the fifteen-second pip path that pulled the wheel from the private index.", "milestone", "technical", False,
     [("conda-forge", "service"), ("miniforge", "tool"), ("mamba", "tool"), ("pip", "tool")],
     [("mamba", "pip", "PREFERS")],
     "which package channel did the internal library first land on and what install-time win did mamba deliver",
     "conda forge feedstock miniforge mamba pip install private index"),
    # --- 24 fact ---
    ("Security scanning runs Bandit on every PR with the severity filter set to medium and above; the custom config excludes the tests/ tree so assert-used warnings don't drown out the real findings.", "fact", "technical", False,
     [("Bandit", "tool"), ("PR", "concept"), ("tests/", "file")],
     [],
     "how is Bandit wired into PR checks and what exclusion keeps the test tree from dominating the report",
     "bandit security pr severity medium tests exclude assert used"),
    # --- 25 decision ---
    ("Replaced Pylint with Ruff on the main service; Pylint's cycle found duplicate lints already covered by Ruff's rule set and was doubling CI time for almost no unique signal.", "decision", "technical", False,
     [("Pylint", "tool"), ("Ruff", "tool"), ("CI", "infrastructure")],
     [("Ruff", "Pylint", "REPLACES")],
     "which linter replaced Pylint on the main service and what redundancy pushed the change",
     "pylint ruff main service ci lint duplicate signal rule"),
    # --- 26 architecture ---
    ("The CLI is built on Click groups with a Rich-backed console renderer; argparse survives only inside a handful of one-shot maintenance scripts under ops/ where a dependency-free entrypoint matters.", "fact", "technical", False,
     [("Click", "library"), ("Rich", "library"), ("argparse", "library"), ("ops/", "file")],
     [("Click", "argparse", "REPLACES")],
     "how are Click and Rich combined in the main CLI and where does argparse still earn its keep",
     "click rich argparse cli group console render ops script entrypoint"),
    # --- 27 problem ---
    ("Wheel uploads broke when a new maintainer's local build produced a linux_x86_64 tag instead of manylinux2014_x86_64; adding a cibuildwheel CI matrix and blocking direct twine uploads closed the gap.", "problem", "technical", False,
     [("linux_x86_64", "platform"), ("manylinux2014_x86_64", "platform"), ("cibuildwheel", "tool"), ("twine", "tool"), ("CI", "infrastructure")],
     [("cibuildwheel", "twine", "REPLACES")],
     "which wheel tag mismatch broke uploads and what policy closed the local-build bypass",
     "wheel linux x86 manylinux cibuildwheel twine upload tag maintainer"),
    # --- 28 preference ---
    ("When a config class doesn't need validation, the team reaches for dataclasses first and msgspec.Struct second; pydantic is reserved for anything that touches untrusted input or a schema boundary.", "preference", "technical", False,
     [("dataclasses", "library"), ("msgspec.Struct", "api"), ("pydantic", "library")],
     [("dataclasses", "pydantic", "PREFERS")],
     "which model library is the team's default for internal configs and where does pydantic earn the extra weight",
     "dataclass msgspec struct pydantic config validate untrusted schema"),
    # --- 29 decision ---
    ("Picked flit over setuptools for the pure-Python utility library; zero-configuration single-module builds kept the pyproject.toml down to seventeen lines and publishing from the repo root is a single flit publish call.", "decision", "technical", False,
     [("flit", "tool"), ("setuptools", "tool"), ("pyproject.toml", "file")],
     [("flit", "setuptools", "PREFERS")],
     "which build tool did the pure-Python utility library pick over setuptools and what workflow win kept things short",
     "flit setuptools pure python utility pyproject publish single module"),
    # --- 30 architecture ---
    ("Local dev uses venv and the stdlib virtualenv is off the table; every contributor creates .venv via python -m venv under pyenv-selected interpreters so a reinstall is a single rm -rf and a script call.", "architecture", "technical", False,
     [("venv", "library"), ("virtualenv", "tool"), ("pyenv", "tool"), (".venv", "file")],
     [("venv", "virtualenv", "PREFERS")],
     "which Python environment tool is standard for local dev and how does pyenv fit in the layout",
     "venv virtualenv pyenv local dev env python interpreter reinstall"),
    # --- 31 milestone ---
    ("Hit full strict-mode mypy on the core package last quarter; 4 200 files, zero Any leaks in the public API, and the tests/ tree is covered by pyright in a separate sweep so editor feedback stays instant.", "milestone", "technical", False,
     [("mypy", "tool"), ("pyright", "tool"), ("tests/", "file"), ("core package", "project")],
     [],
     "which type-check milestone did the core package hit and how is the tests tree covered alongside it",
     "mypy strict core package any public api pyright editor"),
    # --- 32 reference ---
    ("Reference cheat sheet: sdist is the tarball of source plus pyproject.toml, wheel is a pre-built zip with a platform tag, and manylinux wheels target a baseline set of Linux userland symbol versions.", "reference", "technical", False,
     [("sdist", "file"), ("wheel", "file"), ("manylinux", "platform"), ("pyproject.toml", "file")],
     [],
     "what distinguishes sdist, wheel, and manylinux wheels and which metadata file pins each",
     "sdist wheel manylinux pyproject toml tag platform build linux"),
    # --- 33 decision ---
    ("Chose PDM for the plugin SDK where the consumer base leans on PEP 582's __pypackages__ flow; uv handled our internal repos but couldn't offer the same zero-venv workflow for downstream authors.", "decision", "technical", False,
     [("PDM", "tool"), ("uv", "tool"), ("__pypackages__", "file"), ("PEP 582", "protocol"), ("SDK", "project")],
     [("PDM", "uv", "PREFERS")],
     "which manager did the plugin SDK pick instead of uv and which PEP's workflow drove the call",
     "pdm uv pep 582 pypackages plugin sdk zero venv downstream"),
    # --- 34 architecture ---
    ("The pre-commit hooks run Ruff check, Ruff format, and pyright in a staged set; the hypothesis and pytest passes stay in CI so local commits land in under three seconds even on the bigger packages.", "architecture", "technical", False,
     [("pre-commit", "tool"), ("Ruff", "tool"), ("pyright", "tool"), ("pytest", "tool"), ("hypothesis", "library"), ("CI", "infrastructure")],
     [("pre-commit", "Ruff", "USES")],
     "what runs inside the pre-commit hook set and what got pushed to CI to keep commits fast",
     "pre commit ruff pyright pytest hypothesis ci staged local commit"),
    # --- 35 problem ---
    ("Reference for uv cache wiring on CI: UV_CACHE_DIR should be set per repo and point into a dedicated volume rather than the runner root, otherwise cross-repo wheel caches compound and fill the shared disk.", "reference", "technical", False,
     [("uv", "tool"), ("UV_CACHE_DIR", "config"), ("CI", "infrastructure")],
     [],
     "which uv config variable and disk layout does the reference recommend for CI wheel caches",
     "uv cache dir ci runner disk volume reference wheel shared"),
    # --- 36 fact ---
    ("Typer, Rich, and Click are all pinned to a narrow compatible range in the shared tooling extra; pipx install darkmem-tools drags them in at fixed versions so CLIs stay visually consistent across machines.", "fact", "technical", False,
     [("Typer", "library"), ("Rich", "library"), ("Click", "library"), ("pipx", "tool"), ("darkmem-tools", "project")],
     [("pipx", "Typer", "APPLIES_TO")],
     "how do Typer, Rich, and Click stay in lockstep across contributor machines and what installs them",
     "typer rich click pipx darkmem tools pin version cli machine"),
    # --- 37 decision ---
    ("Adopted Hatch's environment plugin for the bench suite instead of tox; matrix expansion inlined in pyproject.toml removed a duplicate source of truth and dropped bench-env setup from eight seconds to about two.", "decision", "technical", False,
     [("Hatch", "tool"), ("tox", "tool"), ("pyproject.toml", "file"), ("bench suite", "project")],
     [("Hatch", "tox", "REPLACES")],
     "which tool replaced tox for the bench matrix and what duplication did the Hatch plugin remove",
     "hatch tox bench pyproject matrix plugin setup duplicate truth"),
    # --- 38 architecture ---
    ("Docs deploy pipeline builds MkDocs for the marketing site and Sphinx for the reference site in one GitHub Actions job; both targets share a MyST-rendered changelog sourced from CHANGES.md.", "architecture", "technical", False,
     [("MkDocs", "tool"), ("Sphinx", "tool"), ("MyST", "framework"), ("GitHub Actions", "service"), ("CHANGES.md", "file")],
     [("MyST", "CHANGES.md", "APPLIES_TO")],
     "how does the docs pipeline share a changelog between MkDocs and Sphinx in one CI job",
     "mkdocs sphinx myst github actions changelog changes md deploy"),
    # --- 39 milestone ---
    ("Finished the conda eviction from developer machines; the mamba-on-miniforge holdouts moved to uv-managed venvs, the last Anaconda license obligation dropped, and CI lost the final conda activate step.", "milestone", "technical", False,
     [("conda", "tool"), ("mamba", "tool"), ("miniforge", "tool"), ("uv", "tool"), ("Anaconda", "service")],
     [("uv", "conda", "REPLACES")],
     "which final holdouts came off conda and what licensing obligation was dropped with the move",
     "conda mamba miniforge uv anaconda license developer ci activate"),
    # --- 40 decision ---
    ("Picked the build backend duo of hatchling for pure-Python packages and setuptools only for the two C-extension ones; flit was dropped after its single-module constraint bit on a library that grew a submodule.", "decision", "technical", False,
     [("hatchling", "tool"), ("setuptools", "tool"), ("flit", "tool")],
     [("hatchling", "flit", "REPLACES")],
     "which build backend combo did the org standardise on and what made flit fall out of the picture",
     "hatchling setuptools flit backend pure python c extension submodule"),
    # --- 41 reference ---
    ("Reference config: pyproject.toml's [project] table holds name, version, requires-python, and dependencies per PEP 621; [build-system] stays minimal with requires and build-backend per PEP 517.", "reference", "technical", False,
     [("pyproject.toml", "file"), ("PEP 621", "protocol"), ("PEP 517", "protocol"), ("[project]", "config"), ("[build-system]", "config")],
     [("[project]", "pyproject.toml", "APPLIES_TO")],
     "which pyproject.toml tables map to PEP 621 and PEP 517 and what do they hold",
     "pyproject toml project build system pep 621 pep 517 table"),
    # --- 42 problem ---
    ("The hypothesis shrinker hung on the property test for the checksum helper; a stateful strategy without a reasonable bundle cap let the search space blow up, and capping max_examples plus adding a bundle limit cleared it.", "problem", "technical", False,
     [("hypothesis", "library"), ("max_examples", "config"), ("stateful strategy", "pattern")],
     [],
     "which hypothesis feature caused the checksum test to hang and which two knobs brought it back",
     "hypothesis shrink stateful strategy bundle max examples checksum cap"),
    # --- 43 noise ---
    ("The third-floor plant wall gained a new pothos cutting after someone's weekend divided theirs and the label just says 'Gerald II'.", "fact", "noise", True, [], [], None, None),
    # --- 44 architecture ---
    ("Release automation uses the build module to produce sdist and wheel, twine to upload to the private index, and a Hatch version plugin to bump pyproject.toml; nothing writes the version by hand anymore.", "architecture", "technical", False,
     [("build", "tool"), ("twine", "tool"), ("Hatch", "tool"), ("pyproject.toml", "file"), ("sdist", "file"), ("wheel", "file")],
     [("Hatch", "pyproject.toml", "APPLIES_TO")],
     "which tools produce, upload, and version-bump the release artefacts and what pyproject field ends up edited",
     "build twine hatch pyproject release sdist wheel version bump private"),
    # --- 45 fact ---
    ("The darkmem-cli entrypoint is declared in pyproject.toml under [project.scripts] and gets wired up automatically on pip install; the old console_scripts setup.cfg entry came out when we left setuptools.", "fact", "technical", False,
     [("darkmem-cli", "project"), ("pyproject.toml", "file"), ("[project.scripts]", "config"), ("setup.cfg", "file"), ("setuptools", "tool")],
     [("[project.scripts]", "setup.cfg", "REPLACES")],
     "which pyproject.toml table declares the darkmem-cli entrypoint and what older config did it replace",
     "darkmem cli entrypoint pyproject scripts console setup cfg setuptools"),
    # --- 46 preference ---
    ("Contributors prefer uv run for one-off scripts over activating the venv first; the sub-second launch and inherited lockfile state keep PATH drift from sneaking in during interactive sessions.", "preference", "technical", False,
     [("uv run", "tool"), ("venv", "library"), ("PATH", "config")],
     [("uv run", "venv", "PREFERS")],
     "which command does the team reach for instead of activating a venv and what does it avoid",
     "uv run venv activate path drift sub second lockfile script"),
    # --- 47 decision ---
    ("Adopted the pytest-xdist plugin for the flaky integration suite; parallel pytest workers cut wall time from twelve minutes to about three and the flake rate didn't change once we pinned worker count to four on the shared runner.", "decision", "technical", False,
     [("pytest-xdist", "library"), ("pytest", "tool"), ("integration suite", "project")],
     [],
     "which pytest plugin parallelised the integration suite and what wall-time change did it deliver",
     "pytest xdist integration suite parallel worker flake wall time runner"),
    # --- 48 preference ---
    ("attrs is the default when a class needs slotted storage and comparison helpers but no schema boundary; dataclasses comes out when the class is trivially a struct and pydantic when the field values cross the wire.", "preference", "technical", False,
     [("attrs", "library"), ("dataclasses", "library"), ("pydantic", "library")],
     [("attrs", "dataclasses", "PREFERS")],
     "how do attrs, dataclasses, and pydantic split responsibility across the code base's model classes",
     "attrs dataclass pydantic slot compare schema boundary wire struct"),
    # --- 49 milestone ---
    ("Completed the Ruff formatter rollout across ninety-two repos; isort and black configs came out of every pyproject.toml, the CI format step is one binary call, and the org-wide style guide finally matches reality.", "milestone", "technical", False,
     [("Ruff", "tool"), ("isort", "tool"), ("black", "tool"), ("pyproject.toml", "file"), ("CI", "infrastructure")],
     [("Ruff", "black", "REPLACES"), ("Ruff", "isort", "REPLACES")],
     "which formatter rollout finished across the org and what dropped out of pyproject.toml in the process",
     "ruff isort black formatter rollout pyproject ci org style guide"),
    # --- 50 milestone ---
    ("Cut the first SDK release under the new uv plus hatchling pipeline; lock solve, wheel build, and private-index upload wrapped in seventy seconds end to end, down from the six-minute tox-driven run.", "milestone", "technical", False,
     [("uv", "tool"), ("hatchling", "tool"), ("tox", "tool"), ("SDK", "project")],
     [("uv", "tox", "REPLACES")],
     "which first SDK release landed on the uv plus hatchling pipeline and what end-to-end time did it beat",
     "uv hatchling tox sdk release pipeline lock wheel upload private"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")

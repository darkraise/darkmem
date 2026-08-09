# The SDK generator's documented command (doc 15 §6, T3.25).
#
# `generate` is verified by `make generate && git diff --exit-code`: the
# output is deterministic, so a regeneration that changes the tree means the
# contract moved, and that is exactly the signal the check exists to give.

# Absolute, because `test` runs its recipes from the package directories: a
# path relative to sdks/ resolves to nothing one level down, and make reports
# that as a missing interpreter rather than as the wrong directory.
PY ?= $(CURDIR)/../backend/.venv/bin/python
TSC ?= $(CURDIR)/../frontend/node_modules/.bin/tsc

.PHONY: generate build test check

generate:
	$(PY) generate.py

# "Both packages build" (T3.25's done-when). The TypeScript package borrows
# the frontend's tsc rather than installing its own toolchain: a second
# node_modules for one generated file is cost with no corresponding check.
build:
	$(TSC) --noEmit --strict --target es2022 --module es2022 \
	  --moduleResolution bundler --lib es2022,dom ts/src/client.ts
	$(PY) -m compileall -q python/darkmem_sdk

# T3.14's Verify, in one place. Each package keeps its own runner so the task's
# two documented commands stay literally runnable; this only saves typing both.
# The TypeScript arm borrows the frontend's vitest for the same reason `build`
# borrows its tsc.
test:
	cd python && $(PY) -m pytest -q
	cd ts && npm test

check: generate build test
	git diff --exit-code -- .

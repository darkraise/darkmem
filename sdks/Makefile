# The SDK generator's documented command (doc 15 §6, T3.25).
#
# `generate` is verified by `make generate && git diff --exit-code`: the
# output is deterministic, so a regeneration that changes the tree means the
# contract moved, and that is exactly the signal the check exists to give.

PY ?= ../backend/.venv/bin/python
TSC ?= ../frontend/node_modules/.bin/tsc

.PHONY: generate build check

generate:
	$(PY) generate.py

# "Both packages build" (T3.25's done-when). The TypeScript package borrows
# the frontend's tsc rather than installing its own toolchain: a second
# node_modules for one generated file is cost with no corresponding check.
build:
	$(TSC) --noEmit --strict --target es2022 --module es2022 \
	  --moduleResolution bundler --lib es2022,dom ts/src/client.ts
	$(PY) -m compileall -q python/darkmem_sdk

check: generate build
	git diff --exit-code -- .

#!/usr/bin/env bash
#
# Cut a release: assert, sync, build, deploy, tag. Five steps that repeat every
# version, which is why this is a script and not a checklist.
#
#   ./scripts/release.sh v1.0.0
#
# Versions are full semver (vN.N.N). The older vN.N form is not accepted: the
# publish workflow derives its rolling `1.0` and `1` tags from a semver parse,
# and a partial version matches none of those patterns -- it would publish
# under its literal name alone while the job still went green.
#
# The tag is written LAST, after the deployment answers on /health. Spec §9 says
# a version is cut by demonstration rather than by assertion, so a tag that
# exists is a tag whose stack came up — a failed deploy leaves nothing to
# explain away.
#
# This script never pushes: it builds locally (`DARKMEM_PUSH=0`) and writes the
# tag in your repository. Publishing is the tag's own consequence -- pushing it
# runs .github/workflows/release.yml, which re-runs CI and only then pushes the
# image to Docker Hub and GHCR. So the irreversible step is `git push origin
# <tag>`, deliberately separate from cutting the release.
set -euo pipefail

VERSION="${1:?usage: release.sh vN.N.N}"
NUMERIC="${VERSION#v}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "release: expected vN.N.N, got '$VERSION'"
  echo "  full semver only — the publish workflow's rolling tags come from a semver parse"
  exit 1
}
[[ -z "$(git status --porcelain)" ]] || { echo "tree is dirty; commit first"; exit 1; }
if git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null; then
  echo "$VERSION already tagged"; exit 1
fi
grep -qE "^## $VERSION\b" CHANGELOG.md || {
  echo "CHANGELOG.md has no '## $VERSION' section; write it before releasing"; exit 1
}

echo "── gate ──"
./scripts/gate.sh --full

echo "── version fields -> $NUMERIC ──"
sed -i -E "s/^version = \"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$NUMERIC\"/" backend/pyproject.toml
sed -i -E "s/version=\"[0-9]+\.[0-9]+\.[0-9]+\"/version=\"$NUMERIC\"/" backend/app/main.py
sed -i -E "s/\"version\": \"[0-9]+\.[0-9]+\.[0-9]+\"/\"version\": \"$NUMERIC\"/" frontend/package.json

# `sed -i` with no match is a silent no-op exiting 0, and the drift test that
# would catch it runs inside the gate — BEFORE these lines. So a reformatted
# `FastAPI(...)` call would leave main.py on the old version, commit the partial
# sync, build, deploy and tag, and only red the NEXT gate run, after the tag
# exists. Assert each substitution landed instead.
for field in backend/pyproject.toml backend/app/main.py frontend/package.json; do
  grep -q "$NUMERIC" "$field" || {
    echo "version sync did not take in $field — its pattern no longer matches; fix the sed" >&2
    exit 1
  }
done

# Check for unexpected dirt BEFORE committing anything, so an abort leaves no
# `chore(release)` commit for a version that never tagged.
DIRTY="$(git status --porcelain | cut -c4-)"
UNEXPECTED="$(printf '%s\n' "$DIRTY" | grep -vE '^(docs/eval/|backend/pyproject\.toml$|backend/app/main\.py$|frontend/package\.json$)' | grep -v '^$' || true)"
if [ -n "$UNEXPECTED" ]; then
  echo "the gate left changes outside docs/eval/ and the version fields:" >&2
  printf '  %s\n' $UNEXPECTED >&2
  echo "commit or revert them first; NOT tagging" >&2
  exit 1
fi

# Stage the three fields BY NAME. The first cut used `git commit -a` and the
# gate had rewritten `docs/eval/<date>-retrieval-eval.md` in place — a fresh run
# id, sha and latency table — so an eval re-stamp shipped inside a commit whose
# subject says "chore(release)". A reader later asking why those numbers moved
# finds a release commit. Anything the gate touches gets its own honest commit.
git add backend/pyproject.toml backend/app/main.py frontend/package.json
git diff --cached --quiet || git commit -qm "chore(release): $VERSION"

if [ -n "$(git status --porcelain)" ]; then
  git add docs/eval
  git commit -qm "docs(eval): re-stamp the retrieval eval from the $VERSION gate run"
fi

echo "── build ──"
DARKMEM_PUSH=0 ./scripts/build-push.sh "$NUMERIC"

echo "── deploy ──"
DARKMEM_VERSION="$NUMERIC" docker compose up -d

# A 200 on :8000 does NOT prove the new container answered it.
# `start_dev_server.sh` is uvicorn on the same port, so a dev server already
# holding :8000 makes the container fail to publish its port and never come up,
# while curl cheerfully gets 200 from the dev process — and the tag
# would be written on a failed deploy, voiding the one guarantee this ordering
# buys. So probe the version the API serves in its own OpenAPI document, which
# is the field the sync above just moved.
echo "── health ──"
for _ in $(seq 1 30); do
  served="$(curl -sS http://localhost:8000/openapi.json 2>/dev/null \
            | sed -n 's/.*"version":"\([0-9][0-9.]*\)".*/\1/p' | head -1 || true)"
  [ "$served" = "$NUMERIC" ] && break
  sleep 2
done
[ "$served" = "$NUMERIC" ] || {
  echo "no deployment serving $NUMERIC on :8000 (saw: ${served:-nothing}); NOT tagging" >&2
  echo "if a dev server holds :8000, stop it — the container cannot publish its port" >&2
  exit 1
}

echo "── tag ──"
git tag -a "$VERSION" -m "$VERSION"

echo "$VERSION tagged and deployed; /health returned 200."

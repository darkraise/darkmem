#!/usr/bin/env bash
#
# Cut a release: assert, sync, build, deploy, tag. Five steps that repeat every
# version, which is why this is a script and not a checklist.
#
#   ./scripts/release.sh v0.1
#
# The tag is written LAST, after the deployment answers on /health. Spec §9 says
# a version is cut by demonstration rather than by assertion, so a tag that
# exists is a tag whose stack came up — a failed deploy leaves nothing to
# explain away.
#
# The image is built but NOT pushed (`DARKMEM_PUSH=0`): spec §10 puts publishing
# to any registry out of scope until the repo is published. A local tag is
# deletable; a pushed image is not.
set -euo pipefail

VERSION="${1:?usage: release.sh v0.N}"
NUMERIC="${VERSION#v}.0"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+$ ]] || { echo "release: expected vN.N, got '$VERSION'"; exit 1; }
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
git diff --quiet || git commit -aqm "chore(release): $VERSION"

echo "── build ──"
DARKMEM_PUSH=0 ./scripts/build-push.sh "$NUMERIC"

echo "── deploy ──"
DARKMEM_VERSION="$NUMERIC" docker compose up -d

echo "── health ──"
for _ in $(seq 1 30); do
  code="$(curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health || true)"
  [ "$code" = "200" ] && break
  sleep 2
done
[ "${code:-}" = "200" ] || { echo "deploy did not answer /health (last: ${code:-none}); NOT tagging"; exit 1; }

echo "── tag ──"
git tag -a "$VERSION" -m "$VERSION"

echo "$VERSION tagged and deployed; /health returned 200."

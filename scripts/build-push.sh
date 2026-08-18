#!/usr/bin/env bash
set -euo pipefail

REGISTRY="darkraise"
VERSION="${1:-latest}"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Building darkmem image..."
echo "  Version: $VERSION"
echo "  Git SHA: $GIT_SHA"

# One image, built from the repo root: it carries the Python runtime AND the
# built SPA, so the context has to see both trees -- which is why it is named
# `darkmem` rather than `darkmem-api`. Renamed from darkraise/darkmem-api on
# 2026-08-18; tags pinned in a DARKMEM_VERSION under the old name no longer
# resolve and must be rebuilt from their git tag.
docker build -t "${REGISTRY}/darkmem:${VERSION}" \
             -t "${REGISTRY}/darkmem:${GIT_SHA}" \
             -t "${REGISTRY}/darkmem:latest" \
             "$(dirname "$0")/.."

# Push. Releases build through here with DARKMEM_PUSH=0: doc "release
# milestones" §10 puts publishing to any registry out of scope until the repo
# is published, and a push is the one step of a release that cannot be undone
# by deleting a local tag.
if [ "${DARKMEM_PUSH:-1}" = "0" ]; then
  echo "DARKMEM_PUSH=0 — built locally, not pushed."
  echo "  ${REGISTRY}/darkmem:${VERSION} (${GIT_SHA})"
  exit 0
fi

echo "Pushing image..."
docker push "${REGISTRY}/darkmem:latest"
docker push "${REGISTRY}/darkmem:${GIT_SHA}"
if [ "$VERSION" != "latest" ]; then
  docker push "${REGISTRY}/darkmem:${VERSION}"
fi

echo "Done! Image pushed:"
echo "  ${REGISTRY}/darkmem:${VERSION} (${GIT_SHA})"

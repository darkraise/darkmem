#!/usr/bin/env bash
set -euo pipefail

REGISTRY="darkraise"
VERSION="${1:-latest}"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Building darkmem image..."
echo "  Version: $VERSION"
echo "  Git SHA: $GIT_SHA"

# One image, built from the repo root: it carries the Python runtime AND the
# built SPA, so the context has to see both trees. The name is historical --
# it predates the SPA moving in -- and is kept so pinned DARKMEM_VERSION tags
# keep resolving.
echo "Building darkmem-api..."
docker build -t "${REGISTRY}/darkmem-api:${VERSION}" \
             -t "${REGISTRY}/darkmem-api:${GIT_SHA}" \
             -t "${REGISTRY}/darkmem-api:latest" \
             "$(dirname "$0")/.."

# Push. Releases build through here with DARKMEM_PUSH=0: doc "release
# milestones" §10 puts publishing to any registry out of scope until the repo
# is published, and a push is the one step of a release that cannot be undone
# by deleting a local tag.
if [ "${DARKMEM_PUSH:-1}" = "0" ]; then
  echo "DARKMEM_PUSH=0 — built locally, not pushed."
  echo "  ${REGISTRY}/darkmem-api:${VERSION} (${GIT_SHA})"
  exit 0
fi

echo "Pushing image..."
docker push "${REGISTRY}/darkmem-api:latest"
docker push "${REGISTRY}/darkmem-api:${GIT_SHA}"
if [ "$VERSION" != "latest" ]; then
  docker push "${REGISTRY}/darkmem-api:${VERSION}"
fi

echo "Done! Image pushed:"
echo "  ${REGISTRY}/darkmem-api:${VERSION} (${GIT_SHA})"

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

# Push
echo "Pushing image..."
docker push "${REGISTRY}/darkmem-api:latest"
docker push "${REGISTRY}/darkmem-api:${GIT_SHA}"
if [ "$VERSION" != "latest" ]; then
  docker push "${REGISTRY}/darkmem-api:${VERSION}"
fi

echo "Done! Image pushed:"
echo "  ${REGISTRY}/darkmem-api:${VERSION} (${GIT_SHA})"

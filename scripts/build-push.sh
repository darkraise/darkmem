#!/usr/bin/env bash
set -euo pipefail

REGISTRY="darkraise"
VERSION="${1:-latest}"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Building darkmem images..."
echo "  Version: $VERSION"
echo "  Git SHA: $GIT_SHA"

# Build API
echo "Building darkmem-api..."
docker build -t "${REGISTRY}/darkmem-api:${VERSION}" \
             -t "${REGISTRY}/darkmem-api:${GIT_SHA}" \
             -t "${REGISTRY}/darkmem-api:latest" \
             ./backend

# Build UI
echo "Building darkmem-ui..."
docker build -t "${REGISTRY}/darkmem-ui:${VERSION}" \
             -t "${REGISTRY}/darkmem-ui:${GIT_SHA}" \
             -t "${REGISTRY}/darkmem-ui:latest" \
             ./frontend

# Push
echo "Pushing images..."
for img in darkmem-api darkmem-ui; do
  docker push "${REGISTRY}/${img}:latest"
  docker push "${REGISTRY}/${img}:${GIT_SHA}"
  if [ "$VERSION" != "latest" ]; then
    docker push "${REGISTRY}/${img}:${VERSION}"
  fi
done

echo "Done! Images pushed:"
echo "  ${REGISTRY}/darkmem-api:${VERSION} (${GIT_SHA})"
echo "  ${REGISTRY}/darkmem-ui:${VERSION} (${GIT_SHA})"

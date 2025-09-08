#!/usr/bin/env bash
set -euo pipefail

# Settings
IMAGE_REPO="${IMAGE_REPO:-suhailphotos/vips-uhdr}"
PLATFORMS="${PLATFORMS:-linux/amd64}"   # add ,linux/arm64 if you want multi-arch later

cd "$(dirname "$0")"  # docker/
get_ref() {
  local repo="$1" ref="${2:-}"
  if [[ -n "$ref" ]]; then echo "$ref"; return; fi
  git ls-remote --exit-code "$repo" HEAD | awk '{print $1}'
}

# Read pins from env or resolve HEAD
LIBVIPS_REF="${LIBVIPS_REF:-}"
LIBUHDR_REF="${LIBUHDR_REF:-}"
LIBVIPS_REF="$(get_ref https://github.com/libvips/libvips.git "$LIBVIPS_REF")"
LIBUHDR_REF="$(get_ref https://github.com/google/libultrahdr.git "$LIBUHDR_REF")"

TAG="${LIBVIPS_REF:0:12}-${LIBUHDR_REF:0:12}"
echo "Building ${IMAGE_REPO}:${TAG}  (vips=${LIBVIPS_REF}  uhdr=${LIBUHDR_REF})"

# Choose load vs push
PUSH=0
[[ "${1:-}" == "--push" ]] && PUSH=1

if [[ $PUSH -eq 1 ]]; then
  docker buildx build \
    --platform "$PLATFORMS" \
    --build-arg LIBVIPS_REF="$LIBVIPS_REF" \
    --build-arg LIBUHDR_REF="$LIBUHDR_REF" \
    -t "${IMAGE_REPO}:${TAG}" -t "${IMAGE_REPO}:current" \
    -f Dockerfile . \
    --push
else
  docker buildx build \
    --platform "$PLATFORMS" \
    --build-arg LIBVIPS_REF="$LIBVIPS_REF" \
    --build-arg LIBUHDR_REF="$LIBUHDR_REF" \
    -t "${IMAGE_REPO}:${TAG}" -t "${IMAGE_REPO}:current" \
    -f Dockerfile . \
    --load
fi

echo "Done. Tag: ${IMAGE_REPO}:${TAG}"

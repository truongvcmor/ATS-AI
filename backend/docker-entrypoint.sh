#!/bin/sh
set -e

# The container starts as root so it can fix ownership of /app/uploads —
# necessary because a named volume (or a bind mount) keeps whatever
# ownership it already had, which for anyone upgrading from an
# earlier/root-based version of this image means root:root, not the "app"
# user this image now runs as. Without this, every upload would fail with
# PermissionError the moment the volume already exists (a fresh volume
# happens to inherit the image's ownership and would work either way).
if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/uploads
    chown -R app:app /app/uploads
    exec gosu app "$0" "$@"
fi

exec "$@"

#!/bin/sh
set -e

# Vite normally inlines VITE_* env vars at BUILD time, but docker-compose sets
# VITE_API_URL as a container RUNTIME env var. To honor that without rebuilding,
# the image is built with a placeholder token baked into the JS bundle, which we
# substitute here for the real value before starting the static server.
API_URL="${VITE_API_URL:-http://localhost:8080/api}"

find /app/dist -type f -name "*.js" -exec grep -l "__RUNTIME_API_URL__" {} \; 2>/dev/null | while read -r file; do
  sed -i "s#__RUNTIME_API_URL__#${API_URL}#g" "$file"
done

exec serve -s /app/dist -l 5173

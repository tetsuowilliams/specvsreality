#!/usr/bin/env sh
# Deprecated: use scripts/reset.sh instead.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
echo "note: tools/redeploy.sh is deprecated; use scripts/reset.sh" >&2
exec "$ROOT/scripts/reset.sh"

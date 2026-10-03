#!/usr/bin/env bash
set -euo pipefail
if ! command -v python3 >/dev/null; then
  echo 'Python 3 is required. Install it with: sudo apt-get install python3' >&2
  exit 1
fi
exec python3 "$(dirname "$(readlink -f "$0")")/scripts/install.py" "$@"

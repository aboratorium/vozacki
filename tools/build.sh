#!/usr/bin/env bash
# One command build. Requires python3. Node is needed only when template.html classes change.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" == "--css" ]]; then
  npx --yes tailwindcss@3.4.17 -c tools/tailwind/tailwind.config.js -i tools/tailwind/in.css -o tools/tailwind/out.css --minify
fi
python3 tools/build.py

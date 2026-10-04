#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 proposals/build-storage-candidate.py
git diff --exit-code -- proposals/store-open-errors.patch
python3 -m unittest discover -s proposals/tests -v

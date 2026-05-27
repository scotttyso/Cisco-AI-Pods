#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_file="$repo_root/tests/sanity/ignore-2.20.txt"
target_file="$repo_root/tests/sanity/ignore-2.16.txt"

cp "$source_file" "$target_file"
echo "Synced $target_file from $source_file"
#!/usr/bin/env bash
set -euo pipefail

# Run ansible-lint with an environment preflight check.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"${REPO_ROOT}/scripts/check_ansible_env.sh"

if [[ $# -eq 0 ]]; then
    ansible-lint
else
    ansible-lint "$@"
fi

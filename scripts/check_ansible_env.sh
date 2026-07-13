#!/usr/bin/env bash
set -euo pipefail

# Verify Ansible CLI, ansible-lint, and Python module versions are aligned.

log() {
    printf "[INFO] %s\n" "$*"
}

warn() {
    printf "[WARN] %s\n" "$*"
}

fail() {
    printf "[ERROR] %s\n" "$*" >&2
    exit 1
}

require_cmd() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1 || fail "Required command not found in PATH: $cmd"
}

strip_ansi() {
    sed -r 's/\x1B\[[0-9;]*[A-Za-z]//g'
}

extract_core_version_from_ansible() {
    ansible --version | sed -n '1s/.*core \([0-9][0-9.]*\).*/\1/p'
}

extract_core_version_from_ansible_lint() {
    ansible-lint --version | strip_ansi | sed -n 's/.*ansible-core:\([0-9][0-9.]*\).*/\1/p'
}

extract_module_version_from_python() {
    python3 - <<'PY'
import ansible
print(ansible.__version__)
PY
}

main() {
    require_cmd ansible
    require_cmd ansible-lint
    require_cmd python3

    local ansible_path ansible_lint_path python_path
    ansible_path="$(command -v ansible)"
    ansible_lint_path="$(command -v ansible-lint)"
    python_path="$(command -v python3)"

    log "ansible path: $ansible_path"
    log "ansible-lint path: $ansible_lint_path"
    log "python3 path: $python_path"

    local cli_core lint_core module_ver
    cli_core="$(extract_core_version_from_ansible)"
    lint_core="$(extract_core_version_from_ansible_lint)"

    if ! module_ver="$(extract_module_version_from_python 2>/dev/null)"; then
        fail "Python could not import ansible module from $python_path"
    fi

    log "ansible CLI core version: $cli_core"
    log "ansible-lint ansible-core version: $lint_core"
    log "python ansible module version: $module_ver"

    if [[ -z "$cli_core" || -z "$lint_core" || -z "$module_ver" ]]; then
        fail "Could not parse one or more Ansible versions. Check your tool installation."
    fi

    # ansible module version should match ansible-core major.minor.patch used by CLI/lint.
    if [[ "$cli_core" != "$module_ver" ]]; then
        warn "Mismatch: ansible CLI core ($cli_core) vs python ansible module ($module_ver)"
        fail "Execution environment is inconsistent. Activate the correct venv or reinstall aligned packages."
    fi

    if [[ "$cli_core" != "$lint_core" ]]; then
        warn "Mismatch: ansible CLI core ($cli_core) vs ansible-lint core ($lint_core)"
        fail "ansible-lint is using a different environment. Ensure PATH/venv consistency."
    fi

    log "Environment is consistent."
}

main "$@"

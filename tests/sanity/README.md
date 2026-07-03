# Sanity Ignore Entries

This directory contains versioned Ansible sanity ignore files:

- `ignore-2.20.txt` is the source of truth.
- `ignore-2.16.txt` is kept in sync for compatibility.

## File Format Rules

The ignore files use a strict format. Each non-empty line must be a valid ignore rule.

- Do not add blank lines.
- Do not add comment-only lines.
- Keep one ignore rule per line.

If comments or blank lines are added, sanity can fail with errors similar to:
"Line cannot be empty or contain only a comment".

## Why These Entries Exist

Current sanity ignore entries are intentionally minimal:

- `roles/splunk_observability/library/get_helm.sh shellcheck!skip`
  - Shellcheck skip for helper script behavior not aligned with shellcheck expectations.

Important:

- `yamllint!skip` entries are not permitted by ansible sanity (`sanity[cannot-ignore]`).
- Helm template YAML under `roles/openshift_gitops/helm/**/templates/**/*.yaml` is ignored through `.yamllint`, not through sanity ignore files.

## Maintenance

When updating ignore entries:

1. Edit `tests/sanity/ignore-2.20.txt`.
2. Run `make sanity-ignore-sync`.
3. Run `make sanity-ignore-check`.
4. Run sanity checks as needed in CI/local validation.

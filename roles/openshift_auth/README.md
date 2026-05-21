# OpenShift Auth Role

Configures OpenShift OAuth to authenticate against Active Directory via LDAP/LDAPS with automatic group synchronization via CronJob.

**Main Documentation:** [docs/openshift.md — Authentication](../../docs/openshift.md#authentication)

## Role Tasks

- `main.yaml` — Validates prerequisites, creates LDAP OAuth provider, deploys LDAP sync resources

## What It Does

1. Validates `oc` CLI availability and required environment variables
2. Creates LDAP OAuth identity provider in OpenShift
3. Creates `ldap-sync` namespace and service account
4. Deploys LDAP sync secret with AD credentials
5. Creates ClusterRole for LDAP group sync
6. Deploys CronJob that runs `oc adm groups sync` hourly
7. Optionally creates group DN whitelist

## Files

| File | Description |
|------|-------------|
| `tasks/main.yaml` | Role entry point with validation and deployment logic |
| `defaults/main.yaml` | Role defaults |
| `templates/active-directory.yaml.j2` | OAuth identity provider manifest |
| `templates/ldap-sync.yaml.j2` | LDAPSyncConfig for group sync |
| `templates/ldap-cron.yaml.j2` | CronJob manifest (hourly sync) |
| `templates/project.yaml.j2` | `ldap-sync` namespace manifest |
| `templates/rbac-ldap-group-sync.yaml.j2` | ClusterRole for sync SA |
| `templates/whitelist.txt.j2` | Group DN whitelist (optional) |

## Key Variables

Set in `host_vars/openshift/ldap.ezai.yaml`:

- `openshift.auth.ldap.url` — LDAP server URL (e.g., `ldaps://ldap.example.com:636`)
- `openshift.auth.ldap.bind_dn` — Service account DN (e.g., `cn=bind,dc=example,dc=com`)
- `openshift.auth.ldap.bind_password_env` — Environment variable suffix for password
- `openshift.auth.ldap.users_search_base` — User search DN
- `openshift.auth.ldap.groups_search_base` — Group search DN

Set via environment variables:

- `ldap_bind_password` — LDAP service account password
- `openshift_api_url` — OpenShift API URL
- `openshift_token_id` — OpenShift API token

Optional:

- `openshift.auth.ldap.ca_certificate_file` — Path to LDAPS CA bundle

## Idempotency

Fully idempotent. Safe to re-run. Resources are reconciled to desired state.

## Manual LDAP Testing

Update secret with new configuration:
```bash
oc set env secret/ldap-sync -n ldap-sync LDAP_URL=<new-url> --overwrite
```

Run sync manually:
```bash
oc exec -n ldap-sync deployment/ldap-sync -- oc adm groups sync
```

Query AD directly:
```bash
ldapsearch -H ldaps://ldap.example.com -D <bind-dn> -w <password> \
  -b <search-base> cn=<group>
```

## Troubleshooting

- **Token expired:** Get fresh token from OpenShift web console (valid 24 hours)
- **LDAP bind fails:** Verify service account exists in AD and password is correct
- **Group sync not running:** Check CronJob status: `oc get cronjob -n ldap-sync`
- **Groups not appearing:** Ensure group DN search base is correct and groups exist in AD
- **No users syncing:** Verify user search base and LDAP filter includes all users

Check resources:
```bash
oc get oauth -o yaml
oc get ldapc -n ldap-sync
oc get cronjob -n ldap-sync
oc logs -n ldap-sync deployment/ldap-sync
```

See [docs/openshift.md — Authentication](../../docs/openshift.md#authentication) for full setup guide.

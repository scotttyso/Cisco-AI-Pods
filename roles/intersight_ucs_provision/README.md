# Intersight UCS Provision Role

Provisions Cisco UCS infrastructure through Cisco Intersight for Cisco AI Pods deployments.

## Purpose

This role validates deployment inputs and drives UCS provisioning operations by using custom library modules and templates under this role.

## Inputs

- Variables from host vars for Intersight deployment
- Environment variables and credentials required by Cisco Intersight APIs

## Role Structure

- `tasks/main.yml`: role entry point
- `library/`: custom modules and helpers used for provisioning and validation
- `templates/`: generated data and policy templates
- `defaults/`: role default variables

## Run

Run through playbook orchestration:

```bash
ansible-playbook playbooks/deploy_intersight_ucs.yaml
```

## Troubleshooting

- Verify API key and endpoint credentials.
- Confirm required variables are present in the selected host vars.
- Review task output for validation errors before retrying.
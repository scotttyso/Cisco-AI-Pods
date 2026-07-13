#!/usr/bin/env python3
"""Regenerate a kubeconfig with an updated cluster CA.

This helper preserves the selected context and user authentication from an
existing kubeconfig, then rewrites the target cluster entry with a new
certificate-authority-data value. It can also override the API server URL and
user token when needed.

Examples:
    python3 scripts/regenerate_kubeconfig.py \
            --kubeconfig-path ~/.kube/config \
      --ca-file ~/new-ca.crt \
      --output ~/new-kubeconfig

    python3 scripts/regenerate_kubeconfig.py \
            --kubeconfig-path ~/.kube/config \
      --context my-cluster-admin \
      --ca-file ~/new-ca.crt \
      --server https://api.example.com:6443 \
      --output ~/new-kubeconfig
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover - import guard
    print(
        "ERROR: PyYAML is required. Install it with 'python3 -m pip install pyyaml'.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


def parse_args() -> argparse.Namespace:
    kubeconfig_env = (Path.home() / ".kube" / "config")
    parser = argparse.ArgumentParser(
        description=(
            "Create a new kubeconfig from an existing one by replacing the "
            "cluster CA bundle and optionally the API server or token."
        )
    )
    parser.add_argument(
        "--kubeconfig-path",
        "--source",
        dest="kubeconfig_path",
        default=None,
        help=(
            "Path to the existing kubeconfig file. Defaults to the first path in "
            "KUBECONFIG when set, otherwise ~/.kube/config."
        ),
    )
    parser.add_argument(
        "--ca-file",
        required=True,
        help="Path to the new PEM-encoded certificate authority file.",
    )
    parser.add_argument(
        "--output",
        help=(
            "Path to the regenerated kubeconfig file. Defaults to overwriting "
            "--kubeconfig-path in place."
        ),
    )
    parser.add_argument(
        "--context",
        help="Kubeconfig context to update. Defaults to current-context.",
    )
    parser.add_argument(
        "--server",
        help="Override the cluster API server URL in the output kubeconfig.",
    )
    parser.add_argument(
        "--token",
        help="Override the selected user's bearer token in the output kubeconfig.",
    )
    parser.add_argument(
        "--flatten",
        action="store_true",
        help=(
            "Write only the selected cluster, user, and context into the output "
            "kubeconfig instead of preserving all other entries."
        ),
    )
    args = parser.parse_args()

    if not args.kubeconfig_path:
        kubeconfig_env_value = os.environ.get("KUBECONFIG")
        if kubeconfig_env_value:
            args.kubeconfig_path = kubeconfig_env_value.split(":", 1)[0]
        else:
            args.kubeconfig_path = str(kubeconfig_env)

    if not args.output:
        args.output = args.kubeconfig_path

    return args


def load_yaml_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")

    return data


def read_ca_bundle(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"CA file not found: {path}")

    content = path.read_text(encoding="utf-8").strip()
    if "-----BEGIN CERTIFICATE-----" not in content:
        raise ValueError(
            f"CA file does not look like a PEM certificate: {path}"
        )

    return base64.b64encode(content.encode("utf-8")).decode("ascii")


def find_named_entry(entries: Any, name: str, kind: str) -> Tuple[Dict[str, Any], int]:
    if not isinstance(entries, list):
        raise ValueError(f"kubeconfig field '{kind}' must be a list")

    for index, entry in enumerate(entries):
        if isinstance(entry, dict) and entry.get("name") == name:
            return entry, index

    raise ValueError(f"Could not find {kind[:-1]} named '{name}' in kubeconfig")


def resolve_target_context(config: Dict[str, Any], context_name: Optional[str]) -> Tuple[str, Dict[str, Any], int]:
    selected_context = context_name or config.get("current-context")
    if not selected_context:
        raise ValueError(
            "No kubeconfig context was provided and current-context is empty."
        )

    context_entry, context_index = find_named_entry(
        config.get("contexts"),
        selected_context,
        "contexts",
    )
    return selected_context, context_entry, context_index


def build_output_config(
    source_config: Dict[str, Any],
    context_name: str,
    context_entry: Dict[str, Any],
    cluster_entry: Dict[str, Any],
    user_entry: Dict[str, Any],
    flatten: bool,
) -> Dict[str, Any]:
    if flatten:
        return {
            "apiVersion": source_config.get("apiVersion", "v1"),
            "kind": source_config.get("kind", "Config"),
            "preferences": source_config.get("preferences", {}),
            "current-context": context_name,
            "clusters": [cluster_entry],
            "users": [user_entry],
            "contexts": [context_entry],
        }

    output_config = dict(source_config)
    output_config["current-context"] = context_name
    return output_config


def main() -> int:
    args = parse_args()

    source_path = Path(args.kubeconfig_path).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    ca_path = Path(args.ca_file).expanduser().resolve()

    source_config = load_yaml_file(source_path)
    ca_data = read_ca_bundle(ca_path)

    context_name, context_entry, context_index = resolve_target_context(
        source_config,
        args.context,
    )
    context_body = context_entry.get("context")
    if not isinstance(context_body, dict):
        raise ValueError(f"Context '{context_name}' is missing its context mapping")

    cluster_name = context_body.get("cluster")
    user_name = context_body.get("user")
    if not cluster_name or not user_name:
        raise ValueError(
            f"Context '{context_name}' must contain both cluster and user references"
        )

    cluster_entry, cluster_index = find_named_entry(
        source_config.get("clusters"),
        cluster_name,
        "clusters",
    )
    user_entry, user_index = find_named_entry(
        source_config.get("users"),
        user_name,
        "users",
    )

    cluster_body = cluster_entry.get("cluster")
    if not isinstance(cluster_body, dict):
        raise ValueError(f"Cluster '{cluster_name}' is missing its cluster mapping")

    cluster_body["certificate-authority-data"] = ca_data
    cluster_body.pop("certificate-authority", None)
    cluster_body.pop("insecure-skip-tls-verify", None)
    if args.server:
        cluster_body["server"] = args.server

    if args.token:
        user_body = user_entry.get("user")
        if not isinstance(user_body, dict):
            raise ValueError(f"User '{user_name}' is missing its user mapping")
        user_body["token"] = args.token
        user_body.pop("exec", None)
        user_body.pop("auth-provider", None)

    if args.flatten:
        selected_context_entry = source_config["contexts"][context_index]
        selected_cluster_entry = source_config["clusters"][cluster_index]
        selected_user_entry = source_config["users"][user_index]
    else:
        selected_context_entry = context_entry
        selected_cluster_entry = cluster_entry
        selected_user_entry = user_entry

    output_config = build_output_config(
        source_config,
        context_name,
        selected_context_entry,
        selected_cluster_entry,
        selected_user_entry,
        args.flatten,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(output_config, handle, default_flow_style=False, sort_keys=False)

    print(f"Wrote regenerated kubeconfig: {output_path}")
    print(f"  Source kubeconfig: {source_path}")
    print(f"  Context: {context_name}")
    print(f"  Cluster: {cluster_name}")
    print(f"  User: {user_name}")
    print(f"  New CA bundle: {ca_path}")
    if args.server:
        print(f"  API server override: {args.server}")
    if args.token:
        print("  Token override: applied")
    print("\nNext step:")
    print(f"  KUBECONFIG={output_path} oc get namespace default")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        raise SystemExit(1) from err
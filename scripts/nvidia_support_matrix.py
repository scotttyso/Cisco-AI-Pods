#!/usr/bin/env python3
"""
NVIDIA AI Enterprise Support Matrix Script

This script extracts GPU model compatibility data from the NVIDIA AI Enterprise
Support Matrix documentation and cross-references it with the local schema and
configuration files.

Usage:
    python nvidia_support_matrix.py [--format json|csv|table] [--version VERSION]
"""

import json
import yaml
import argparse
import sys
from pathlib import Path
from typing import Dict, List
from tabulate import tabulate

# Hardcoded support matrix data from NVIDIA documentation
# Source: https://docs.nvidia.com/ai-enterprise/support-matrix/latest/index.html
# Note: Some versions may have limited EOL support. Check NVIDIA docs for current support status.
NVIDIA_SUPPORT_MATRIX = {
    "8.1": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "595.71.05",
            "NVIDIA DOCA Driver for Networking": "3.4.0",
            "NVIDIA GPU Operator": "26.3.3",
            "NVIDIA Network Operator": "26.4.0",
            "NVIDIA Run:ai": "2.25",
        },
        "gpu_models": {
            "B300 SXM": {"architecture": "Blackwell Ultra", "deployment": "HGX Server"},
            "B200 SXM": {"architecture": "Blackwell", "deployment": "HGX Server"},
            "H200 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H200 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "RTX PRO 4500 Blackwell Server Edition": {
                "architecture": "Blackwell",
                "deployment": "PCIe GPU Server",
            },
            "RTX PRO 6000 Blackwell Server Edition": {
                "architecture": "Blackwell",
                "deployment": "PCIe GPU Server",
            },
        },
    },
    "8.0": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "595.58.03",
            "NVIDIA DOCA Driver for Networking": "3.3.0",
            "NVIDIA GPU Operator": "26.3.0",
            "NVIDIA Network Operator": "26.1.0",
            "NVIDIA Run:ai": "2.24",
        },
        "gpu_models": {
            "B300 SXM": {"architecture": "Blackwell Ultra", "deployment": "HGX Server"},
            "B200 SXM": {"architecture": "Blackwell", "deployment": "HGX Server"},
            "H200 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H200 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "RTX PRO 4500 Blackwell Server Edition": {
                "architecture": "Blackwell",
                "deployment": "PCIe GPU Server",
            },
            "RTX PRO 6000 Blackwell Server Edition": {
                "architecture": "Blackwell",
                "deployment": "PCIe GPU Server",
            },
        },
    },
    "7.7": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "550.107.02",
            "NVIDIA DOCA Driver for Networking": "3.2.0",
            "NVIDIA GPU Operator": "24.6.2",
            "NVIDIA Network Operator": "24.10.0",
            "NVIDIA Run:ai": "2.24",
        },
        "gpu_models": {
            "H200 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H200 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
        },
    },
    "7.6": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "550.107.02",
            "NVIDIA DOCA Driver for Networking": "3.1.0",
            "NVIDIA GPU Operator": "24.6.0",
            "NVIDIA Network Operator": "24.6.0",
            "NVIDIA Run:ai": "2.23",
        },
        "gpu_models": {
            "H200 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H200 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
        },
    },
    "7.5": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "550.90.07",
            "NVIDIA DOCA Driver for Networking": "3.1.0",
            "NVIDIA GPU Operator": "24.3.0",
            "NVIDIA Network Operator": "24.3.0",
            "NVIDIA Run:ai": "2.22",
        },
        "gpu_models": {
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
        },
    },
    "7.4": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "550.90.07",
            "NVIDIA DOCA Driver for Networking": "3.0.0",
            "NVIDIA GPU Operator": "24.3.0",
            "NVIDIA Network Operator": "24.3.0",
            "NVIDIA Run:ai": "2.21",
        },
        "gpu_models": {
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
        },
    },
    "7.3": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "545.23.06",
            "NVIDIA DOCA Driver for Networking": "3.0.0",
            "NVIDIA GPU Operator": "24.1.0",
            "NVIDIA Network Operator": "24.1.0",
            "NVIDIA Run:ai": "2.20",
        },
        "gpu_models": {
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
        },
    },
    "7.2": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "545.23.06",
            "NVIDIA DOCA Driver for Networking": "2.9.0",
            "NVIDIA GPU Operator": "23.9.1",
            "NVIDIA Network Operator": "23.10.0",
            "NVIDIA Run:ai": "2.19",
        },
        "gpu_models": {
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
        },
    },
    "7.1": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "545.23.06",
            "NVIDIA DOCA Driver for Networking": "2.8.0",
            "NVIDIA GPU Operator": "23.9.0",
            "NVIDIA Network Operator": "23.9.0",
            "NVIDIA Run:ai": "2.18",
        },
        "gpu_models": {
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "H100 NVL": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
        },
    },
    "7.0": {
        "infrastructure_software": {
            "NVIDIA Data Center GPU Driver": "535.104.05",
            "NVIDIA DOCA Driver for Networking": "2.7.0",
            "NVIDIA GPU Operator": "23.6.1",
            "NVIDIA Network Operator": "23.6.0",
            "NVIDIA Run:ai": "2.17",
        },
        "gpu_models": {
            "H100": {"architecture": "Hopper", "deployment": "DGX Server"},
            "H100 SXM": {"architecture": "Hopper", "deployment": "HGX Server"},
            "L40": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
            "L40S": {"architecture": "Ada", "deployment": "PCIe GPU Server"},
        },
    },
}


class NVIDIASupportMatrix:
    """Extract and process NVIDIA AI Enterprise support matrix data."""

    def __init__(self, schema_path: str = None, examples_path: str = None):
        """
        Initialize the support matrix processor.

        Args:
            schema_path: Path to cisco-ai-pods.json schema file
            examples_path: Path to operators.ezai.yaml example file
        """
        self.schema_path = Path(schema_path or "schema/cisco-ai-pods.json")
        self.examples_path = Path(examples_path or "examples/openshift/operators.ezai.yaml")
        self.schema_data = {}
        self.example_data = {}

    def load_schema(self) -> None:
        """Load the JSON schema file."""
        if not self.schema_path.exists():
            print(f"Warning: Schema file not found: {self.schema_path}")
            return

        try:
            with open(self.schema_path, "r") as f:
                self.schema_data = json.load(f)
            print(f"✓ Loaded schema from {self.schema_path}")
        except json.JSONDecodeError as e:
            print(f"Error parsing schema JSON: {e}")
            sys.exit(1)

    def load_examples(self) -> None:
        """Load the YAML examples file."""
        if not self.examples_path.exists():
            print(f"Warning: Examples file not found: {self.examples_path}")
            return

        try:
            with open(self.examples_path, "r") as f:
                self.example_data = yaml.safe_load(f)
            print(f"✓ Loaded examples from {self.examples_path}")
        except yaml.YAMLError as e:
            print(f"Error parsing YAML: {e}")
            sys.exit(1)

    def extract_gpu_models(self) -> List[str]:
        """Extract GPU models from the example configuration."""
        gpu_models = []
        if self.example_data:
            gpu_models = (
                self.example_data.get("openshift", {}).get("gpu_models", [])
            )
        return gpu_models

    def extract_ai_enterprise_version(self) -> str:
        """Extract NVIDIA AI Enterprise version from the example configuration."""
        if self.example_data:
            return (
                self.example_data.get("openshift", {})
                .get("nvidia_ai_enterprise_version", "8.1")
            )
        return "8.1"

    def get_gpu_models_from_schema(self) -> List[str]:
        """Extract supported GPU models from the schema."""
        try:
            # Navigate through the schema to find gpu_models enum
            definitions = self.schema_data.get("definitions", {})
            openshift_rhoai = definitions.get(
                "openshift.rhoai", {}
            )
            properties = openshift_rhoai.get("properties", {})
            gpu_models_def = properties.get("gpu_models", {})
            items = gpu_models_def.get("items", {})
            enum_values = items.get("enum", [])
            return enum_values
        except (KeyError, TypeError):
            return []

    def get_compatibility_report(self, format_type: str = "table") -> str:
        """
        Generate a compatibility report for selected GPU models.

        Args:
            format_type: Output format ('table', 'json', or 'csv')

        Returns:
            Formatted compatibility report
            
        Raises:
            ValueError: If GPU models are not supported by the selected AI Enterprise version
        """
        self.load_schema()
        self.load_examples()

        gpu_models = self.extract_gpu_models()
        ai_version = self.extract_ai_enterprise_version()
        
        # Debug: check version and available versions
        available_versions = list(NVIDIA_SUPPORT_MATRIX.keys())
        print(f"✓ NVIDIA AI Enterprise version: {ai_version}")
        print(f"✓ Available versions in matrix: {available_versions}")
        print(f"✓ GPU models found: {gpu_models}")
        
        # Ensure version is a string and convert if needed
        ai_version = str(ai_version).strip()
        
        if ai_version not in NVIDIA_SUPPORT_MATRIX:
            print(f"Warning: Version '{ai_version}' not found in support matrix.")
            print(f"Available versions: {', '.join(available_versions)}")
            ai_version = "8.1"  # Default to latest
        
        supported_software = NVIDIA_SUPPORT_MATRIX.get(ai_version, {}).get(
            "infrastructure_software", {}
        )

        if not gpu_models:
            return "No GPU models found in configuration."

        if not supported_software:
            return f"No support matrix data found for NVIDIA AI Enterprise version {ai_version}"

        # Validate that all selected GPU models are supported by the selected version
        supported_gpu_models = set(
            NVIDIA_SUPPORT_MATRIX.get(ai_version, {}).get("gpu_models", {}).keys()
        )
        selected_gpu_models = set(gpu_models)
        unsupported_models = selected_gpu_models - supported_gpu_models
        
        if unsupported_models:
            raise ValueError(
                f"Error: NVIDIA AI Enterprise v{ai_version} does not support the following GPU models:\n"
                f"  Unsupported: {', '.join(sorted(unsupported_models))}\n"
                f"  Supported for v{ai_version}: {', '.join(sorted(supported_gpu_models))}\n"
                f"\nPlease either:\n"
                f"  1. Update your GPU models to supported ones, or\n"
                f"  2. Change your NVIDIA AI Enterprise version"
            )

        # Build report data
        report_data = []
        for gpu_model in gpu_models:
            gpu_info = NVIDIA_SUPPORT_MATRIX.get(ai_version, {}).get(
                "gpu_models", {}
            ).get(gpu_model, {})

            row = {
                "GPU Model": gpu_model,
                "Architecture": gpu_info.get("architecture", "N/A"),
                "Deployment Type": gpu_info.get("deployment", "N/A"),
                "OpenShift Kubernetes": "Supported",
                "Data Center GPU Driver": supported_software.get(
                    "NVIDIA Data Center GPU Driver", "N/A"
                ),
                "DOCA Driver for Networking": supported_software.get(
                    "NVIDIA DOCA Driver for Networking", "N/A"
                ),
                "GPU Operator": supported_software.get(
                    "NVIDIA GPU Operator", "N/A"
                ),
                "Network Operator": supported_software.get(
                    "NVIDIA Network Operator", "N/A"
                ),
                "Run:ai": supported_software.get("NVIDIA Run:ai", "N/A"),
            }
            report_data.append(row)

        # Format output
        if format_type == "json":
            return self._format_json(report_data, ai_version)
        elif format_type == "csv":
            return self._format_csv(report_data, ai_version)
        else:  # table
            return self._format_table(report_data, ai_version)

    def _format_table(self, data: List[Dict], ai_version: str) -> str:
        """Format data as a human-readable table."""
        output = f"\n{'='*180}\n"
        output += f"NVIDIA AI Enterprise Infrastructure Support Matrix v{ai_version}\n"
        output += f"Deployment: Bare Metal - Kubernetes - OpenShift\n"
        output += f"{'='*180}\n\n"

        headers = [
            "GPU Model",
            "Architecture",
            "Deployment Type",
            "Platform",
            "GPU Driver",
            "DOCA Driver",
            "GPU Operator",
            "Network Operator",
            "Run:ai",
        ]

        table_data = [
            [
                row["GPU Model"],
                row["Architecture"],
                row["Deployment Type"],
                row["OpenShift Kubernetes"],
                row["Data Center GPU Driver"],
                row["DOCA Driver for Networking"],
                row["GPU Operator"],
                row["Network Operator"],
                row["Run:ai"],
            ]
            for row in data
        ]

        output += tabulate(table_data, headers=headers, tablefmt="grid")
        output += "\n\nSource: https://docs.nvidia.com/ai-enterprise/support-matrix/latest/index.html\n"
        return output

    def _format_json(self, data: List[Dict], ai_version: str) -> str:
        """Format data as JSON."""
        output = {
            "nvidia_ai_enterprise_version": ai_version,
            "deployment_type": "Bare Metal - Kubernetes - OpenShift",
            "support_matrix_url": "https://docs.nvidia.com/ai-enterprise/support-matrix/latest/index.html",
            "gpu_configurations": data,
        }
        return json.dumps(output, indent=2)

    def _format_csv(self, data: List[Dict], ai_version: str) -> str:
        """Format data as CSV."""
        import csv
        from io import StringIO

        output = StringIO()
        headers = [
            "GPU Model",
            "Architecture",
            "Deployment Type",
            "Platform",
            "GPU Driver",
            "DOCA Driver",
            "GPU Operator",
            "Network Operator",
            "Run:ai",
        ]

        writer = csv.writer(output)
        writer.writerow(headers)

        for row in data:
            writer.writerow(
                [
                    row["GPU Model"],
                    row["Architecture"],
                    row["Deployment Type"],
                    row["OpenShift Kubernetes"],
                    row["Data Center GPU Driver"],
                    row["DOCA Driver for Networking"],
                    row["GPU Operator"],
                    row["Network Operator"],
                    row["Run:ai"],
                ]
            )

        return output.getvalue()

    def get_version_info(self, ai_version: str = None) -> Dict[str, str]:
        """
        Get all software version information for a specific NVIDIA AI Enterprise version.

        Args:
            ai_version: NVIDIA AI Enterprise version (default: from examples)

        Returns:
            Dictionary of software versions
        """
        if ai_version is None:
            ai_version = self.extract_ai_enterprise_version()

        return NVIDIA_SUPPORT_MATRIX.get(ai_version, {}).get(
            "infrastructure_software", {}
        )

    def format_versions(self, ai_version: str, format_type: str = "table") -> str:
        """
        Format version information in the specified format.

        Args:
            ai_version: NVIDIA AI Enterprise version
            format_type: Output format (table, json, csv)

        Returns:
            Formatted version information
        """
        versions = self.get_version_info(ai_version)

        if format_type == "json":
            output = {
                "nvidia_ai_enterprise_version": ai_version,
                "infrastructure_software": versions,
                "support_matrix_url": "https://docs.nvidia.com/ai-enterprise/support-matrix/latest/index.html",
            }
            return json.dumps(output, indent=2)

        elif format_type == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["Software", "Version"])
            for software, version in versions.items():
                writer.writerow([software, version])
            return output.getvalue()

        else:  # table format
            output = f"\nNVIDIA AI Enterprise {ai_version} - Software Versions:\n"
            output += "=" * 60 + "\n"
            for software, version in versions.items():
                output += f"  {software:<40} {version}\n"
            return output


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NVIDIA AI Enterprise Support Matrix Tool"
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--version",
        type=str,
        help="NVIDIA AI Enterprise version (default: from examples)",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default="schema/cisco-ai-pods.json",
        help="Path to schema file",
    )
    parser.add_argument(
        "--examples",
        type=str,
        default="examples/openshift/operators.ezai.yaml",
        help="Path to examples file",
    )
    parser.add_argument(
        "--versions-only",
        action="store_true",
        help="Show only software versions",
    )

    args = parser.parse_args()

    matrix = NVIDIASupportMatrix(args.schema, args.examples)

    try:
        if args.versions_only:
            version = args.version or matrix.extract_ai_enterprise_version()
            output = matrix.format_versions(version, args.format)
            print(output)
        else:
            report = matrix.get_compatibility_report(args.format)
            print(report)
    except ValueError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

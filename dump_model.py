#!/usr/bin/python
"""
Dump Intersight model structure to JSON for inspection.
"""
import json
import sys
from pathlib import Path
import yaml


def _deep_merge(base, update):
    """Recursively merge update dict into base dict in-place."""
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_merge(base[key], value)
        elif isinstance(value, list) and key in base and isinstance(base[key], list):
            base[key].extend(value)
        else:
            base[key] = value


def load_yaml_files(model_dir):
    """Load and merge all YAML model files."""
    merged = {}

    # Find all .yaml and .yml files in the model directory
    yaml_files = sorted(Path(model_dir).glob('*.ezai.yaml')) + \
        sorted(Path(model_dir).glob('*.yaml'))
    yaml_files = [f for f in yaml_files if f.is_file()]

    print(f"Found {len(yaml_files)} YAML files in {model_dir}")

    for yaml_file in yaml_files:
        print(f"  Loading: {yaml_file.name}")
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    _deep_merge(merged, data)
        except (yaml.YAMLError, OSError) as e:
            print(f"  Error loading {yaml_file}: {e}")
            continue

    return merged


def main():
    """Dump Intersight YAML models to a JSON file and print a summary."""
    # Model directory
    model_dir = Path(
        '/home/tyscott@rich.ciscolabs.com/scotttyso/Cisco-AI-Pods/intersight/policies')

    if not model_dir.exists():
        print(f"Error: Model directory not found: {model_dir}")
        sys.exit(1)

    print(f"Loading models from: {model_dir}\n")

    merged = load_yaml_files(model_dir)

    # Output to JSON file
    output_file = Path(
        '/home/tyscott@rich.ciscolabs.com/scotttyso/Cisco-AI-Pods/model_structure.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, default=str)

    print(f"\nModel structure saved to: {output_file}")

    # Print a summary of top-level keys
    if 'intersight' in merged:
        print("\nTop-level Intersight structure:")
        for key in sorted(merged['intersight'].keys()):
            value = merged['intersight'][key]
            if isinstance(value, dict):
                subkeys = list(value.keys())[:5]
                print(f"  intersight.{key}: {len(value)} keys")
                print(f"    First few keys: {subkeys}")
            elif isinstance(value, list):
                print(f"  intersight.{key}: list with {len(value)} items")
            else:
                print(f"  intersight.{key}: {type(value).__name__}")

    # Check for profiles/templates
    if 'intersight' in merged:
        print("\nProfiles and Templates structure:")
        if 'profiles' in merged['intersight']:
            print(
                f"  intersight.profiles: {list(merged['intersight']['profiles'].keys())}")
        if 'templates' in merged['intersight']:
            print(
                f"  intersight.templates: {list(merged['intersight']['templates'].keys())}")


if __name__ == '__main__':
    main()

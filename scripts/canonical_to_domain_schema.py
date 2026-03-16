#!/usr/bin/env python3
"""Byg JSON Schema fra kanonisk model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = PROJECT_ROOT / "model_canonical" / "model.canonical.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "schema" / "domain.schema.json"


def to_json_schema(canonical: dict) -> dict:
    """Map canonical classes til $defs i JSON Schema."""
    defs = {}

    for class_obj in canonical.get("classes", []):
        class_name = class_obj["name"]
        properties = {}
        required = []

        for attr in class_obj.get("attributes", []):
            attr_name = attr["name"]
            attr_type = attr.get("type", "string")

            # Basis-felt fra canonical
            properties[attr_name] = {"type": attr_type}

            # Bevar format hvis det findes (fx date/date-time)
            if "format" in attr:
                properties[attr_name]["format"] = attr["format"]

            if attr.get("required", False):
                required.append(attr_name)

        class_schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }

        if required:
            class_schema["required"] = required

        defs[class_name] = class_schema

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.org/domain.schema.json",
        "title": "Domain Schema",
        "type": "object",
        "$defs": defs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert canonical JSON to JSON Schema"
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input canonical JSON path (default: {DEFAULT_INPUT})",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON Schema path (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = args.output.resolve()

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Reading canonical model from: {input_path}")
    print(f"Writing JSON Schema to: {output_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    canonical = json.loads(input_path.read_text(encoding="utf-8"))
    schema = to_json_schema(canonical)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Done.")


if __name__ == "__main__":
    main()

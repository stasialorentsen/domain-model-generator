#!/usr/bin/env python3
"""Byg JSON Schema fra kanonisk model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = PROJECT_ROOT / "model_canonical" / "model.canonical.json"
DEFAULT_PROFILE = PROJECT_ROOT / "profiles" / "person_domain_profile.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "schema" / "domain.schema.json"


def to_json_schema(canonical: dict, profile: dict) -> dict:
    """Map canonical classes til $defs i JSON Schema."""
    defs = {}

    # Domæneprofil mappings
    class_map = profile.get("class_mappings", {})
    attr_map = profile.get("attribute_mappings", {})
    required_map = profile.get("required", {})
    extra_attrs = profile.get("additional_attributes", {})

    for class_obj in canonical.get("classes", []):
        canonical_class = class_obj["name"]

        # Omdøb klasse hvis mapping findes
        class_name = class_map.get(canonical_class, canonical_class)

        properties = {}
        required = []

        for attr in class_obj.get("attributes", []):
            attr_name = attr["name"]
            attr_type = attr.get("type", "string")

            # Slå evt. attributmapping op
            lookup = f"{canonical_class}.{attr_name}"
            schema_attr = attr_map.get(lookup, attr_name)

            # Basis-felt fra canonical
            properties[schema_attr] = {"type": attr_type}

            # Bevar format hvis det findes (fx date/date-time)
            if "format" in attr:
                properties[schema_attr]["format"] = attr["format"]

            if attr.get("required", False):
                required.append(schema_attr)

        # Tilføj ekstra attributter fra domæneprofil
        for extra in extra_attrs.get(class_name, []):
            name = extra["name"]
            properties[name] = {"type": extra.get("type", "string")}

            if "format" in extra:
                properties[name]["format"] = extra["format"]

        # Override required fra profil hvis angivet
        required = required_map.get(class_name, required)

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
        "$id": f"https://example.org/{profile['domain']}.schema.json",
        "title": f"{profile['domain'].capitalize()} Domain Schema",
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
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help=f"Domain profile JSON (default: {DEFAULT_PROFILE})",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON Schema path (default: auto from profile domain)",
    )

    args = parser.parse_args()

    input_path = args.input.resolve()
    profile_path = args.profile.resolve()

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Reading canonical model from: {input_path}")
    print(f"Reading domain profile from: {profile_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    canonical = json.loads(input_path.read_text(encoding="utf-8"))

    # Indlæs domæneprofil
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    # Byg outputnavn fra domæne hvis default bruges
    if args.output == DEFAULT_OUTPUT:
        output_path = (PROJECT_ROOT / "schema" / f"{profile['domain']}.schema.json").resolve()
    else:
        output_path = args.output.resolve()

    print(f"Writing JSON Schema to: {output_path}")

    schema = to_json_schema(canonical, profile)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Done.")


if __name__ == "__main__":
    main()
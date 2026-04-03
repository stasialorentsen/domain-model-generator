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

def parse_cardinality(raw: str | None) -> tuple[int, int | None]:
    """Parse cardinality to min/max (max=None means unbounded)."""
    if not raw:
        return 0, None

    text = raw.strip()
    if text == "*":
        return 0, None
    if ".." in text:
        left, right = text.split("..", 1)
        min_items = int(left)
        max_items = None if right == "*" else int(right)
        return min_items, max_items

    exact = int(text)
    return exact, exact


def to_json_schema(canonical: dict, profile: dict) -> dict:
    """Map canonical classes til $defs i JSON Schema."""
    defs = {}

    # Domæneprofil mappings
    class_map = profile.get("class_mappings", {})
    attr_map = profile.get("attribute_mappings", {})
    required_map = profile.get("required", {})
    extra_attrs = profile.get("additional_attributes", {})
    
    class_schemas: dict[str, dict] = {}
    class_required: dict[str, list[str]] = {}


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
        class_schemas[class_name] = class_schema
        class_required[class_name] = required

    # Tilføj relationer som $ref/array-properties baseret på kardinalitet
    for rel in canonical.get("relationships", []):
        canonical_from = rel.get("from")
        canonical_to = rel.get("to")
        if not canonical_from or not canonical_to:
            continue
    
        from_class = class_map.get(canonical_from, canonical_from)
        to_class = class_map.get(canonical_to, canonical_to)
    
        if from_class not in class_schemas or to_class not in class_schemas:
            continue
    
        rel_name = rel.get("name", "").strip() or f"{canonical_to.lower()}Ref"
        from_schema = class_schemas[from_class]
        from_required = class_required[from_class]
    
        min_items, max_items = parse_cardinality(rel.get("target_cardinality"))
        ref_schema = {"$ref": f"#/$defs/{to_class}"}
    
        if max_items is None or max_items > 1:
            rel_schema = {
                "type": "array",
                "items": ref_schema,
            }
            if min_items > 0:
                rel_schema["minItems"] = min_items
            if max_items is not None:
                rel_schema["maxItems"] = max_items
        else:
            rel_schema = ref_schema
    
        prop_name = rel_name
        if prop_name in from_schema["properties"]:
            prop_name = f"{prop_name}Ref"
    
        from_schema["properties"][prop_name] = rel_schema
    
        if min_items > 0 and prop_name not in from_required:
            from_required.append(prop_name)
            from_schema["required"] = from_required

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
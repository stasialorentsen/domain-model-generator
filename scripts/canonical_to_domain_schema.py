#!/usr/bin/env python3
"""Build a JSON Schema from the canonical model."""

from __future__ import annotations

# Used for command line arguments
import argparse

# Used for reading and writing JSON files
import json

# Used for safe file and folder path handling
from pathlib import Path


# Find the project root based on this file's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default input/output paths
DEFAULT_INPUT = PROJECT_ROOT / "model_canonical" / "model.canonical.json"
DEFAULT_PROFILE = PROJECT_ROOT / "profiles" / "test_domain_profile.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "schema" / "domain.schema.json"


def parse_cardinality(raw: str | None) -> tuple[int, int | None]:
    """Convert cardinality text into min/max values."""

    # Missing cardinality means optional and unbounded
    if not raw:
        return 0, None

    text = raw.strip()

    # * means unlimited
    if text == "*":
        return 0, None

    # Handle ranges like 0..1 or 1..*
    if ".." in text:
        left, right = text.split("..", 1)

        min_items = int(left)

        # * means no upper limit
        max_items = None if right == "*" else int(right)

        return min_items, max_items

    # Single number means exact amount
    exact = int(text)

    return exact, exact


def to_json_schema(canonical: dict, profile: dict) -> dict:
    """Convert canonical classes into JSON Schema definitions."""

    defs = {}

    # Domain profile mappings/configuration
    class_map = profile.get("class_mappings", {})
    attr_map = profile.get("attribute_mappings", {})
    required_map = profile.get("required", {})
    extra_attrs = profile.get("additional_attributes", {})

    # Used later when relationships are added
    class_schemas: dict[str, dict] = {}
    class_required: dict[str, list[str]] = {}

    # --------------------------------------------------
    # PASS 1: Build schemas for all classes
    # --------------------------------------------------

    for class_obj in canonical.get("classes", []):

        canonical_class = class_obj["name"]

        # Rename class if a mapping exists in the profile
        class_name = class_map.get(canonical_class, canonical_class)

        properties = {}
        required = []

        # Process all attributes in the class
        for attr in class_obj.get("attributes", []):

            attr_name = attr["name"]
            attr_type = attr.get("type", "string")

            # Build lookup key like "Book.title"
            lookup = f"{canonical_class}.{attr_name}"

            # Rename attribute if profile mapping exists
            schema_attr = attr_map.get(lookup, attr_name)

            # Basic JSON Schema field
            properties[schema_attr] = {
                "type": attr_type
            }

            # Preserve formats like date/date-time
            if "format" in attr:
                properties[schema_attr]["format"] = attr["format"]

            # Add to required fields if marked as required
            if attr.get("required", False):
                required.append(schema_attr)

        # Add extra attributes from the domain profile
        for extra in extra_attrs.get(class_name, []):

            name = extra["name"]

            properties[name] = {
                "type": extra.get("type", "string")
            }

            # Preserve format if present
            if "format" in extra:
                properties[name]["format"] = extra["format"]

        # Profile required fields override canonical required fields
        required = required_map.get(class_name, required)

        # Build the final schema for this class
        class_schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }

        # Only add required if the list is not empty
        if required:
            class_schema["required"] = required

        defs[class_name] = class_schema
        class_schemas[class_name] = class_schema
        class_required[class_name] = required

    # --------------------------------------------------
    # PASS 2: Add relationships between classes
    # --------------------------------------------------

    for rel in canonical.get("relationships", []):

        canonical_from = rel.get("from")
        canonical_to = rel.get("to")

        # Skip incomplete relationships
        if not canonical_from or not canonical_to:
            continue

        # Apply possible class mappings
        from_class = class_map.get(canonical_from, canonical_from)
        to_class = class_map.get(canonical_to, canonical_to)

        # Skip if classes are missing
        if from_class not in class_schemas or to_class not in class_schemas:
            continue

        # Use relationship name or generate one automatically
        rel_name = (
            rel.get("name", "").strip()
            or f"{canonical_to.lower()}Ref"
        )

        from_schema = class_schemas[from_class]
        from_required = class_required[from_class]

        # Cardinality decides if this becomes object or array
        min_items, max_items = parse_cardinality(
            rel.get("target_cardinality")
        )

        # JSON Schema reference to another class
        ref_schema = {
            "$ref": f"#/$defs/{to_class}"
        }

        # Multiple items -> array relationship
        if max_items is None or max_items > 1:

            rel_schema = {
                "type": "array",
                "items": ref_schema,
            }

            # Only add limits if needed
            if min_items > 0:
                rel_schema["minItems"] = min_items

            if max_items is not None:
                rel_schema["maxItems"] = max_items

        # Single item -> direct reference
        else:
            rel_schema = ref_schema

        prop_name = rel_name

        # Avoid property name collisions
        if prop_name in from_schema["properties"]:
            prop_name = f"{prop_name}Ref"

        # Add relationship property
        from_schema["properties"][prop_name] = rel_schema

        # Required if minimum cardinality > 0
        if min_items > 0 and prop_name not in from_required:

            from_required.append(prop_name)

            from_schema["required"] = from_required

    # Final root JSON Schema
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://example.org/{profile['domain']}.schema.json",
        "title": f"{profile['domain'].capitalize()} Domain Schema",
        "type": "object",
        "$defs": defs,
    }


def main() -> None:

    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description="Convert canonical JSON to JSON Schema"
    )

    # Input canonical model
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input canonical JSON path (default: {DEFAULT_INPUT})",
    )

    # Domain profile file
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help=f"Domain profile JSON (default: {DEFAULT_PROFILE})",
    )

    # Output schema path
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON Schema path (default: auto from profile domain)",
    )

    args = parser.parse_args()

    input_path = args.input.resolve()
    profile_path = args.profile.resolve()

    # Print useful debug/info messages
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Reading canonical model from: {input_path}")
    print(f"Reading domain profile from: {profile_path}")

    # Stop if input files are missing
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    # Load canonical model JSON
    canonical = json.loads(
        input_path.read_text(encoding="utf-8")
    )

    # Load domain profile JSON
    profile = json.loads(
        profile_path.read_text(encoding="utf-8")
    )

    # Auto-generate output filename from domain name if default is used
    if args.output == DEFAULT_OUTPUT:

        output_path = (
            PROJECT_ROOT
            / "schema"
            / f"{profile['domain']}.schema.json"
        ).resolve()

    else:
        output_path = args.output.resolve()

    print(f"Writing JSON Schema to: {output_path}")

    # Build final schema
    schema = to_json_schema(canonical, profile)

    # Create output folder if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save pretty JSON output
    output_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Done.")


# Run main only when executed directly
if __name__ == "__main__":
    main()
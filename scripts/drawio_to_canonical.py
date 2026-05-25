#!/usr/bin/env python3
"""Convert draw.io XML class diagrams into a canonical JSON model."""

from __future__ import annotations

# Used for command line arguments
import argparse

# Used to write the canonical model as JSON
import json

# Used for parsing text patterns like attributes and cardinalities
import re

# Used for reading and navigating the draw.io XML file
import xml.etree.ElementTree as ET

# Used for safe file and folder paths
from pathlib import Path


# Find the project root based on this file's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default input and output paths
DEFAULT_INPUT = PROJECT_ROOT / "metamodel" / "InformationMetaModel_final.xml"
DEFAULT_OUTPUT = PROJECT_ROOT / "model_canonical" / "model.canonical.json"


def clean_value(raw: str) -> str:
    """Clean text values from draw.io."""

    # draw.io values can be empty
    if not raw:
        return ""

    # Remove extra whitespace around the text
    return raw.strip()


def parse_cardinality(raw: str) -> str | None:
    """Return normalized cardinality text, for example 0..1, 1..*, or 1."""

    # Clean input before checking it
    text = clean_value(raw)

    # No text means no cardinality
    if not text:
        return None

    # Match ranges like 0..1 or 1..*
    if re.fullmatch(r"\d+\.\.(\d+|\*)", text):
        return text

    # Match a single number like 1
    if re.fullmatch(r"\d+", text):
        return text

    # In UML, * usually means many
    if text == "*":
        return "0..*"

    # Ignore anything that is not a cardinality
    return None


def parse_attribute(value: str) -> dict | None:
    """Parse an attribute line like '+ field: Type'."""

    text = clean_value(value)

    # Remove possible inline notes/comments
    text = text.split("//", 1)[0].strip()

    # Match a simple UML-style attribute
    # Examples: + name: String, - age: Integer
    match = re.match(
        r"^[+#-]?\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)",
        text
    )

    # Ignore lines that do not match the expected attribute format
    if not match:
        return None

    attr_name = match.group(1)
    raw_type = match.group(2)

    # Map common UML/data types to JSON types
    type_map = {
        "String": "string",
        "Integer": "integer",
        "Int": "integer",
        "Float": "number",
        "Double": "number",
        "Boolean": "boolean",
        "Bool": "boolean",
        "DateTime": "string",
        "Date": "string",
    }

    # Unknown types are treated as strings
    attr_type = type_map.get(raw_type, "string")

    attr = {
        "name": attr_name,
        "type": attr_type,
    }

    # Add JSON format information for date/time types
    if raw_type == "DateTime":
        attr["format"] = "date-time"

    elif raw_type == "Date":
        attr["format"] = "date"

    return attr


def parse_drawio(xml_path: Path) -> dict:
    """Parse the draw.io XML file and build the canonical model."""

    # Read and parse the XML file
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Get all mxCell elements, which draw.io uses for shapes, text, and edges
    cells = root.findall(".//mxCell")

    # Helper structures for looking up classes later
    id_to_label = {}
    classes = []
    class_ids = set()

    # --------------------------------------------------
    # PASS 1: Find all classes
    # --------------------------------------------------

    for cell in cells:

        cell_id = cell.get("id")
        value = clean_value(cell.get("value") or "")
        style = cell.get("style") or ""
        vertex = cell.get("vertex")

        # In this diagram, classes are stored as swimlane shapes
        if cell_id and value and vertex == "1" and "swimlane" in style:

            class_obj = {
                "id": cell_id,
                "name": value,
                "attributes": [],
            }

            classes.append(class_obj)

            # Save class ids/names for relationships and attributes
            id_to_label[cell_id] = value
            class_ids.add(cell_id)

    # Fast lookup from class id to class object
    class_lookup = {c["id"]: c for c in classes}

    # --------------------------------------------------
    # PASS 2: Find attributes inside the classes
    # --------------------------------------------------

    for cell in cells:

        parent = cell.get("parent")
        value = clean_value(cell.get("value") or "")
        style = cell.get("style") or ""
        vertex = cell.get("vertex")

        # Attributes are text elements placed inside a class/swimlane
        if parent in class_ids and vertex == "1" and "text;" in style and value:

            attr = parse_attribute(value)

            # Only add valid attributes
            if attr:
                class_lookup[parent]["attributes"].append(attr)

    # --------------------------------------------------
    # PASS 3: Find relationships between classes
    # --------------------------------------------------

    # Edge labels can contain cardinalities, so they are collected first
    edge_labels: dict[str, list[tuple[float, str]]] = {}

    for cell in cells:

        parent = cell.get("parent")
        style = cell.get("style") or ""
        value = clean_value(cell.get("value") or "")

        # Only edge labels are useful in this loop
        if not parent or "edgeLabel" not in style:
            continue

        cardinality = parse_cardinality(value)

        # Ignore labels that are not cardinalities
        if not cardinality:
            continue

        # Geometry helps decide which side of the edge the label belongs to
        geom = cell.find("mxGeometry")

        try:
            x_pos = float(
                (geom.get("x") if geom is not None else "0") or "0"
            )

        except ValueError:
            x_pos = 0.0

        edge_labels.setdefault(parent, []).append((x_pos, cardinality))

    relationships = []

    # Now find the actual edges between classes
    for cell in cells:

        source = cell.get("source")
        target = cell.get("target")
        value = clean_value(cell.get("value") or "")

        # A relationship is valid only if both ends point to classes
        if source in class_ids and target in class_ids:

            source_cardinality = None
            target_cardinality = None

            # Get cardinality labels for this edge
            labels = edge_labels.get(cell.get("id", ""), [])

            if labels:

                # Sort labels from left to right
                labels = sorted(labels, key=lambda item: item[0])

                # If there is only one label, estimate the side by x-position
                if len(labels) == 1:

                    if labels[0][0] < 0:
                        source_cardinality = labels[0][1]

                    else:
                        target_cardinality = labels[0][1]

                # If there are multiple labels, use first and last
                else:
                    source_cardinality = labels[0][1]
                    target_cardinality = labels[-1][1]

            relationships.append(
                {
                    # Use the edge name if it exists, otherwise create one
                    "name": value or f"{id_to_label[source]}_to_{id_to_label[target]}",

                    "from": id_to_label[source],
                    "to": id_to_label[target],

                    "source_cardinality": source_cardinality,
                    "target_cardinality": target_cardinality,
                }
            )

    # Return the full canonical model
    return {
        "version": "0.1.0",
        "classes": classes,
        "relationships": relationships,
    }


def main() -> None:

    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description="Convert draw.io XML to canonical JSON"
    )

    # Optional input XML file path
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to draw.io XML file (default: {DEFAULT_INPUT})",
    )

    # Optional output JSON file path
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output canonical JSON path (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = args.output.resolve()

    # Print useful information when running the script
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Reading model from: {input_path}")
    print(f"Writing canonical model to: {output_path}")

    # Stop early if the input file does not exist
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Convert the draw.io XML into the canonical structure
    canonical = parse_drawio(input_path)

    # Create the output folder if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the canonical model as pretty JSON
    output_path.write_text(
        json.dumps(canonical, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Print a small summary after conversion
    print(f"Classes found: {len(canonical['classes'])}")
    print(f"Relationships found: {len(canonical['relationships'])}")
    print("Done.")


# Run main only when this file is executed directly
if __name__ == "__main__":
    main()
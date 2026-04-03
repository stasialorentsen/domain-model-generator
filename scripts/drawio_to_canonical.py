#!/usr/bin/env python3
"""Konverter draw.io XML-klassediagram til kanonisk JSON-model."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INPUT = PROJECT_ROOT / "metamodel" / "InformationMetaModel_final.xml"
DEFAULT_OUTPUT = PROJECT_ROOT / "model_canonical" / "model.canonical.json"


def clean_value(raw: str) -> str:
    """Trim draw.io value-felter."""
    if not raw:
        return ""
    return raw.strip()

def parse_cardinality(raw: str) -> str | None:
    """Return normalized cardinality text (e.g. 0..1, 1..*, 1)."""
    text = clean_value(raw)
    if not text:
        return None

    if re.fullmatch(r"\d+\.\.(\d+|\*)", text):
        return text
    if re.fullmatch(r"\d+", text):
        return text
    if text == "*":
        return "0..*"

    return None

def parse_attribute(value: str) -> dict | None:
    """Parse attributlinje i stil med '+ field: Type'."""
    text = clean_value(value)

    # Strip evt. inline note efter //
    text = text.split("//", 1)[0].strip()

    # Forventer UML-ish format: + name: Type
    match = re.match(r"^[+#-]?\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", text)
    if not match:
        return None

    attr_name = match.group(1)
    raw_type = match.group(2)

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

    attr_type = type_map.get(raw_type, "string")

    attr = {
        "name": attr_name,
        "type": attr_type,
    }

    if raw_type == "DateTime":
        attr["format"] = "date-time"
    elif raw_type == "Date":
        attr["format"] = "date"

    return attr


def parse_drawio(xml_path: Path) -> dict:
    """Parse draw.io XML og byg kanonisk model."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    cells = root.findall(".//mxCell")

    id_to_label = {}
    classes = []
    class_ids = set()

    # Pass 1: find klasser
    for cell in cells:
        cell_id = cell.get("id")
        value = clean_value(cell.get("value") or "")
        style = cell.get("style") or ""
        vertex = cell.get("vertex")

        # draw.io klasser ligger som swimlane + vertex=1
        if cell_id and value and vertex == "1" and "swimlane" in style:
            class_obj = {
                "id": cell_id,
                "name": value,
                "attributes": [],
            }
            classes.append(class_obj)
            id_to_label[cell_id] = value
            class_ids.add(cell_id)

    # Pass 2: find attributter under hver klasse
    class_lookup = {c["id"]: c for c in classes}

    for cell in cells:
        parent = cell.get("parent")
        value = clean_value(cell.get("value") or "")
        style = cell.get("style") or ""
        vertex = cell.get("vertex")

        # Attribut er tekstfelt i swimlane-body
        if parent in class_ids and vertex == "1" and "text;" in style and value:
            attr = parse_attribute(value)
            if attr:
                class_lookup[parent]["attributes"].append(attr)

    # Pass 3: find relationer mellem klasser
    # Edge labels (child cells) kan indeholde kardinaliteter.
    edge_labels: dict[str, list[tuple[float, str]]] = {}
    for cell in cells:
        parent = cell.get("parent")
        style = cell.get("style") or ""
        value = clean_value(cell.get("value") or "")
        if not parent or "edgeLabel" not in style:
            continue
    
        cardinality = parse_cardinality(value)
        if not cardinality:
            continue
    
        geom = cell.find("mxGeometry")
        try:
            x_pos = float((geom.get("x") if geom is not None else "0") or "0")
        except ValueError:
            x_pos = 0.0
    
        edge_labels.setdefault(parent, []).append((x_pos, cardinality))
        
    relationships = []

    for cell in cells:
        source = cell.get("source")
        target = cell.get("target")
        value = clean_value(cell.get("value") or "")

        # Tag kun edges hvor begge ender er kendte klasser
        if source in class_ids and target in class_ids:
            source_cardinality = None
            target_cardinality = None

            labels = edge_labels.get(cell.get("id", ""), [])
            if labels:
                labels = sorted(labels, key=lambda item: item[0])
                if len(labels) == 1:
                    if labels[0][0] < 0:
                        source_cardinality = labels[0][1]
                    else:
                        target_cardinality = labels[0][1]
                else:
                    source_cardinality = labels[0][1]
                    target_cardinality = labels[-1][1]

            relationships.append(
                {
                    "name": value or f"{id_to_label[source]}_to_{id_to_label[target]}",
                    "from": id_to_label[source],
                    "to": id_to_label[target],
                    "source_cardinality": source_cardinality,
                    "target_cardinality": target_cardinality,
                }
            )

    return {
        "version": "0.1.0",
        "classes": classes,
        "relationships": relationships,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert draw.io XML to canonical JSON"
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to draw.io XML file (default: {DEFAULT_INPUT})",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output canonical JSON path (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = args.output.resolve()

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Reading model from: {input_path}")
    print(f"Writing canonical model to: {output_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    canonical = parse_drawio(input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(canonical, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Classes found: {len(canonical['classes'])}")
    print(f"Relationships found: {len(canonical['relationships'])}")
    print("Done.")


if __name__ == "__main__":
    main()

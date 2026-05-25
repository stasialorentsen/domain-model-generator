# Solution Design

## Overview

The purpose of this solution is to transform a visual draw.io metamodel into a machine-readable and reusable JSON Schema structure.

The pipeline is designed as a layered transformation process:

1. draw.io XML → canonical JSON model
2. canonical model → domain profile mapping
3. canonical model + domain profile → JSON Schema

This separation makes the architecture modular and easier to maintain.

The solution separates:

- visual modeling (`draw.io`)
- generic model structure (canonical model)
- domain-specific specialization (domain profile)
- formal validation structure (`JSON Schema`)

---

# Pipeline


draw.io model
      ↓
drawio_to_canonical.py
      ↓
model.canonical.json
      ↓
person_domain_profile.json / biobank_domain_profile.json
      ↓
canonical_to_domain_schema.py
      ↓
person.schema.json / biobank.schema.json

---

# Architecture

The solution consists of:

* one parser script
* one schema generation script
* one or more domain profiles

---

# drawio_to_canonical.py

This script reads the draw.io XML file and extracts the structural elements of the model.

The script extracts:

* classes (`swimlanes`)
* attributes from class text fields
* relationships between classes
* relationship cardinalities

The output is a canonical JSON model:

model.canonical.json

This canonical model acts as a stable intermediate representation between the visual diagram and later transformations.

---

## Responsibilities

The script is responsible for:

* parsing draw.io XML
* identifying UML-like classes
* parsing attribute definitions
* extracting relationships
* normalizing cardinalities
* generating a generic canonical model

---

## Example Canonical Structure

{
  "classes": [
    {
      "name": "Person",
      "attributes": [
        {
          "name": "name",
          "type": "string"
        }
      ]
    }
  ],
  "relationships": [
    {
      "name": "owns",
      "from": "Person",
      "to": "Book",
      "target_cardinality": "0..*"
    }
  ]
}

---

# Domain Profiles

Domain profiles are used to specialize the canonical model for a specific domain.

A profile can:

* rename classes
* rename attributes
* define required fields
* add additional attributes
* customize generated schemas without changing the metamodel

This makes the solution reusable across multiple domains.

Examples:
person_domain_profile.json
biobank_domain_profile.json
library_domain_profile.json

---

# canonical_to_domain_schema.py

This script converts the canonical model into a valid JSON Schema.

The script combines:

* the canonical model
* a selected domain profile

and generates *.schema.json

---

## Responsibilities

The script is responsible for:

* converting canonical classes into JSON Schema definitions
* mapping attributes to JSON Schema properties
* applying domain-specific mappings
* generating `$ref` relationships
* converting cardinalities into:

  * arrays
  * required fields
  * `minItems`
  * `maxItems`

---

# Relationship Handling

Relationships from the canonical model are transformed into JSON Schema references.

Examples:

| Cardinality | Result                           |
| ----------- | -------------------------------- |
| `1`         | required object reference        |
| `0..1`      | optional object reference        |
| `0..*`      | optional array                   |
| `1..*`      | required array with `minItems=1` |

---

# Benefits of the Architecture

The layered architecture provides several advantages:

## Separation of Concerns

Each layer has a single responsibility:

| Layer           | Responsibility       |
| --------------- | -------------------- |
| draw.io         | Visual modeling      |
| Canonical Model | Generic structure    |
| Domain Profile  | Domain customization |
| JSON Schema     | Validation format    |

---

## Reusability

The same canonical model can generate multiple schemas for different domains.

Only the domain profile needs to change.

---

## Extensibility

New domains can be added without changing the parser logic.

The solution can also be extended later with:

* OpenAPI generation
* GraphQL schema generation
* RDF/OWL export
* database schema generation

---

# Current Implementation Status

## Implemented

* extraction of classes from draw.io
* extraction of attributes
* extraction of relationships
* canonical model generation
* domain specialization using profiles
* JSON Schema generation
* relationship conversion to `$ref`
* cardinality conversion to:

  * required/optional fields
  * arrays
  * `minItems`
  * `maxItems`

---

# Repository Structure

scripts/
  drawio_to_canonical.py
  canonical_to_domain_schema.py

profiles/
  person_domain_profile.json
  biobank_domain_profile.json

model_canonical/
  model.canonical.json

schema/
  person.schema.json
  biobank.schema.json

docs/
  solution_design.md

---

# Summary

The solution demonstrates a model-driven transformation pipeline where:

* a visual metamodel is parsed from draw.io
* transformed into a canonical intermediate representation
* specialized through domain profiles
* and finally converted into formal JSON Schema definitions

The architecture emphasizes:

* modularity
* reusability
* maintainability
* separation of concerns
* domain adaptability

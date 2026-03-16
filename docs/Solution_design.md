# Løsningsdesign - automatisk modelafledning

Denne løsning implementerer en simpel pipeline, der omsætter en informationsmodel fra et draw.io-diagram til et domænespecifikt JSON Schema.

Formålet er at gøre metamodellen maskinelt analyserbar og at kunne generere forskellige domænemodeller ud fra den samme generiske struktur.

Pipeline består af tre trin:

1. draw.io XML → kanonisk JSON-model
2. kanonisk model → domæneprofil (mapping)
3. kanonisk model + domæneprofil → JSON Schema

Dette adskiller:

* visuel modellering (draw.io)
* generisk modelstruktur (kanonisk model)
* domænespecifik specialisering (domæneprofil)
* formel struktur til validering (JSON Schema)

---

# Pipeline

```
draw.io model
      ↓
drawio_to_canonical.py
      ↓
model.canonical.json
      ↓
person_domain_profile.json
      ↓
canonical_to_domain_schema.py
      ↓
person.schema.json
```

---

# Arkitektur

Løsningen består af to scripts og en domæneprofil.

## drawio_to_canonical.py

Læser draw.io XML og udtrækker modellens strukturelle elementer.

Udtrækker:

* klasser (swimlanes)
* attributter fra klassens tekst
* relationer mellem klasser

Output er en kanonisk JSON-model:

```
model.canonical.json
```

Denne model fungerer som et stabilt mellemformat mellem diagrammet og de efterfølgende transformationer.

---

## canonical_to_domain_schema.py

Genererer et JSON Schema ud fra:

* den kanoniske model
* en domæneprofil

Transformationen omsætter:

* klasser → `$defs`
* attributter → `properties`

Domæneprofilen bruges til at:

* omdøbe klasser
* omdøbe attributter
* definere obligatoriske felter
* tilføje domænespecifikke attributter

Output bliver et schema for det valgte domæne, fx:

```
person.schema.json
```

---

# Domæneprofil

Metamodellen bruger generelle begreber som fx:

```
Subject
Resource
ProcessEvent
```

En domæneprofil beskriver hvordan disse begreber oversættes til et konkret domæne.

Eksempel:

```
Subject → Person
subjectId → personId
name → fullName
```

Profilen fungerer derfor som et mapping-lag mellem den generiske model og det konkrete domæne.

---

# Transformationslogik

Schema-generatoren arbejder efter en simpel regelbaseret proces.

Pseudoalgoritme:

```
læs canonical model
læs domain profile

for hver klasse i canonical model:
    find domænenavn for klassen
    opret tom properties-liste

    for hver attribut i klassen:
        find domænenavn for attributten
        opret property med type
        bevar format hvis det findes

    tilføj ekstra attributter fra domain profile
    fastlæg required-felter
    opret schema-definition for klassen

saml alle definitioner i $defs
skriv JSON Schema til fil
```

Den samme transformationslogik kan derfor bruges til flere domæner.
Kun domæneprofilen ændres.

---

# Scope (prototype)

### Implementeret

* udtræk af klasser fra draw.io
* udtræk af attributter
* udtræk af relationer
* generering af kanonisk model
* domænespecialisering via profil
* generering af JSON Schema

### Ikke implementeret endnu

* kardinaliteter (`0..1`, `1..*`)
* `$ref`-relationer i schema
* semantiske regler (Schematron/XSD)

---

# Repo struktur

```
scripts/
  drawio_to_canonical.py
  canonical_to_domain_schema.py

profiles/
  person_domain_profile.json

model_canonical/
  model.canonical.json

schema/
  person.schema.json

docs/
  solution_design.md
```

---

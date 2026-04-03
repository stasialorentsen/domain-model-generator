diff --git a/docs/Solution_design.md b/docs/Solution_design.md
index afc0aa3bd3f069f93fa718b2ec04f99bc8fca2dd..d40a50470be3e8256e0cc4484c3ec65ee7e04071 100644
--- a/docs/Solution_design.md
+++ b/docs/Solution_design.md
@@ -6,55 +6,55 @@ Formålet er at gøre metamodellen maskinelt analyserbar og at kunne generere fo
 
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
person_domain_profile.json / biobank_domain_profile.json
       ↓
 canonical_to_domain_schema.py
       ↓
person.schema.json / biobank.schema.json
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
@@ -150,37 +150,39 @@ Kun domæneprofilen ændres.
 
 * udtræk af klasser fra draw.io
 * udtræk af attributter
 * udtræk af relationer
 * generering af kanonisk model
 * domænespecialisering via profil
 * generering af JSON Schema
 
### Delvist implementeret

* relationer i canonical-model omsættes nu til `$ref` og arrays i schema
* kardinaliteter (`0..1`, `1`, `0..*`, `1..*`) omsættes til optional/required samt array-min/max

 
 ---
 
 # Repo struktur
 
 ```
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
 ```
 
 ---

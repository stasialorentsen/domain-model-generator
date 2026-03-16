\# Løsningsdesign - automatisk modelafledning



\## Formål

Løsningen operationaliserer pipeline for automatisk modelafledning:



1\. \*\*draw.io XML → kanonisk JSON-model\*\*

2\. \*\*kanonisk JSON-model → JSON Schema\*\*



Målet er at gøre metamodellen maskinelt analyserbar via en enkel, regelbaseret transformation med tydelige mellemrepræsentationer.



\---



\## Scope (prototype)



\### Indgår

\- Udtræk af klasser fra draw.io XML.

\- Udtræk af attributter (UML-lignende tekstlinjer).

\- Udtræk af relationer mellem klasser.

\- Generering af JSON Schema med `$defs`, `properties`, `required` og `additionalProperties: false`.



\### Indgår ikke endnu

\- Kardinaliteter (`0..1`, `1..\*`, osv.) som formelle schema-regler.

\- Semantiske constraints (Schematron/XSD-regler).

\- Avanceret relationel validering med `$ref` mellem klasser.



\---



\## Arkitektur



Pipeline består af to scripts i `scripts/`:



\- `drawio\_to\_canonical.py`

&#x20; - Input: draw.io XML

&#x20; - Output: kanonisk model (`model.canonical.json`)

\- `canonical\_to\_schema.py`

&#x20; - Input: kanonisk model

&#x20; - Output: JSON Schema (`domain.schema.json`)



Designvalg:

\- Bevidst simpel og transparent implementation.

\- Mellemformat (kanonisk JSON) holder visualisering adskilt fra formel validering.

\- Regler er eksplicitte i kode, så afledningen er reproducerbar.



\---



\## Funktionelt design



\## 1) draw.io XML → kanonisk model



\### Inputforventning

\- XML med `mxCell`-noder fra draw.io eksport.

\- Klasser er markeret som `vertex="1"` + `style` indeholder `swimlane`.

\- Attributter er tekstfelter under klasse (`parent` peger på klasse-id, `style` indeholder `text;`).

\- Relationer er edges med `source`/`target` der matcher kendte klasse-id'er.



\### Transformationsregler

\- `swimlane` → klasse.

\- Attributlinje i format `+ name: Type` → attribut med `name` + JSON type.

\- Edge mellem to klasser → relation `{name, from, to}`.



\### Type-mapping

\- `String` → `string`

\- `Integer` / `Int` → `integer`

\- `Float` / `Double` → `number`

\- `Boolean` / `Bool` → `boolean`

\- `Date` → `string` + `format: date`

\- `DateTime` → `string` + `format: date-time`

\- Ukendt type → fallback `string`



\### Outputstruktur

```json

{

&#x20; "version": "0.1.0",

&#x20; "classes": \[

&#x20;   {

&#x20;     "id": "...",

&#x20;     "name": "Subject",

&#x20;     "attributes": \[

&#x20;       {"name": "subjectId", "type": "string"}

&#x20;     ]

&#x20;   }

&#x20; ],

&#x20; "relationships": \[

&#x20;   {"name": "Subject\_to\_Resource", "from": "Subject", "to": "Resource"}

&#x20; ]

}

```



\---



\## 2) kanonisk model → JSON Schema



\### Inputforventning

\- JSON-dokument med `classes\[]`.

\- Hver klasse har `name` og evt. `attributes\[]`.



\### Transformationsregler

\- Klasse → entry i `$defs`.

\- Attribut → `properties.<attr\_name>.type`.

\- Hvis attribut har `format`, videreføres den.

\- Hvis attribut har `required=true`, tilføjes navn i klassens `required`-liste.

\- Hver klasse får `additionalProperties: false`.



\### Outputstruktur (forenklet)

```json

{

&#x20; "$schema": "https://json-schema.org/draft/2020-12/schema",

&#x20; "$defs": {

&#x20;   "Subject": {

&#x20;     "type": "object",

&#x20;     "properties": {

&#x20;       "subjectId": {"type": "string"}

&#x20;     },

&#x20;     "additionalProperties": false

&#x20;   }

&#x20; }

}

```



\---



\## Ikke-funktionelle krav

\- \*\*Reproducerbarhed:\*\* Samme input giver samme output.

\- \*\*Læsbarhed:\*\* Korte kommentarer og tydelig regelkode.

\- \*\*Simpel CLI:\*\* `--input` og `--output` med standardstier.

\- \*\*Robust IO:\*\* Fejl ved manglende inputfil; outputmapper oprettes automatisk.



\---



\## Kvalitet og validering

Nuværende minimumsvalidering:

\- Python syntaks/kompilering (`py\_compile`).



Anbefalet næste testniveau:

\- Referencefiler i `experiments/` med forventet canonical/schema output.

\- Golden-file tests (snapshot-lignende).

\- Negative tests for ugyldig attributsyntaks og manglende felter.



\---



\## Næste iterationer

1\. Udvid relationer til formelle `$ref`-koblinger i schema.

2\. Modelér kardinaliteter fra diagram i canonical-format.

3\. Tilføj constraints-lag (fx Schematron-regler) til semantisk validering.

4\. Etabler testpakke med små domæneeksempler (fx HR/studieadministration).



\---



\## Leverancer i repo

\- `scripts/drawio\_to\_canonical.py`

\- `scripts/canonical\_to\_schema.py`

\- `docs/loesningsdesign.md` (dette dokument)




# FORENSIC_DOSSIER_ENGINE

> Forensische dossieranalyse — Uitsluitend lokale data  
> Versie: 1.0.0

## Doel

Analyseer en structureer uitsluitend lokaal aangeleverde dossierdata.  
Reconstrueer tijdlijnen, detecteer inconsistenties en genereer juridisch bruikbare rapportstructuren.

## Regels

- ✅ Werkt **enkel** met bestanden uit de geselecteerde opslagplaats
- ❌ Geen externe accounts, geen scraping, geen intrusie
- 🔗 Elke conclusie is herleidbaar naar brondata
- 🇳🇱 Output in gestructureerd Nederlands

## Mapstructuur

```
dossier/
├── data/           ← Ruwe data en bronbestanden
├── evidence/       ← Bewijsstukken
├── timeline/       ← Tijdlijn-gerelateerde documenten
├── output/         ← Gegenereerde rapporten (automatisch aangemaakt)
│   ├── hoofdrapport.md
│   ├── tijdlijn.md
│   ├── risico_analyse.md
│   └── samenvatting.json
├── engine/         ← Python-engine modules
│   ├── models.py           — Datamodellen
│   ├── importer.py         — Bestandsimporter
│   ├── tijdlijn.py         — Tijdlijnreconstructie
│   ├── consistency_scan.py — Consistency scan
│   ├── risico_analyse.py   — Risico-analyse
│   ├── bewijs_structuur.py — Bewijsstructuur per map
│   ├── rapport_export.py   — Rapport export (Markdown)
│   ├── orchestrator.py     — Hoofdorchestrator
│   └── cli.py              — CLI entry point
├── run_analyse.js  ← Node.js runner (aanbevolen)
└── run_analyse.py  ← Python runner
```

## Gebruik

### Stap 1: Voeg bewijsstukken toe

Plaats bestanden in de juiste mappen:

| Map | Inhoud |
|-----|--------|
| `dossier/data/` | Ruwe data, bronbestanden, contracten |
| `dossier/evidence/` | Bewijsstukken, correspondentie, verklaringen |
| `dossier/timeline/` | Tijdlijn-notities, chronologische overzichten |

**Ondersteunde bestandsformaten:** `.txt`, `.pdf`, `.json`, `.html`, `.eml`, `.csv`, `.md`

### Stap 2: Voer de analyse uit

```bash
# Met Node.js (aanbevolen — geen installatie vereist)
node dossier/run_analyse.js

# Met Python 3.8+
python dossier/run_analyse.py

# Of als module
python -m dossier.engine
```

### Stap 3: Bekijk de rapporten

Rapporten worden opgeslagen in `dossier/output/`:

- **`hoofdrapport.md`** — Volledig forensisch rapport
- **`tijdlijn.md`** — Chronologische tijdlijn
- **`risico_analyse.md`** — Risico-overzicht
- **`samenvatting.json`** — Machine-leesbare samenvatting

## Functies

### 1. Tijdlijnreconstructie
- Extraheert datums uit bestandsinhoud en bestandsnamen
- Sorteert chronologisch
- Detecteert temporele gaten (> 90 dagen)
- Vertrouwensniveaus: hoog (importtijdstip) / middel (tekst) / laag (bestandsnaam)

### 2. Consistency Scan
- **Feitelijke tegenspraken**: Detecteert tegenstrijdige uitspraken tussen documenten
- **Datumconflicten**: Signaleert conflicterende datumvermeldingen
- **Persoonconflicten**: Detecteert tegenstrijdige uitspraken over dezelfde persoon
- **Duplicaatdetectie**: Identificeert identieke bestanden via SHA-256 hash

### 3. Risico-analyse
- **Juridische risico's**: Bewijsgewicht, relevantie, ontbrekende documenten
- **Procedurele risico's**: Termijnen, verjaring (5-jaar drempel), lege mappen
- **Bewijstechnische risico's**: Authenticiteit, chain of custody, inconsistenties
- **Temporele risico's**: Tijdsgaten, toekomstige datums

### 4. Bewijsstructuur per map
- Overzicht per dossiermapstructuur
- Dominante persoon en zaak per map
- Tijdspanne per map
- Bewijsgewicht en relevantie statistieken

### 5. Rapport export (Markdown)
- Volledig forensisch rapport met alle secties
- Juridisch bruikbare structuur
- Elke bevinding herleidbaar naar bronbewijsstuk
- SHA-256 hashes voor integriteitsverificatie

## Bewijsgewicht Berekening

| Factor | Score |
|--------|-------|
| Documentlengte (per 1000 tekens) | 0-3 |
| Aantal gevonden datums | 0-2 |
| Juridische termen aanwezig | 0-3 |
| **Totaal ≥ 6** | **Hoog** |
| **Totaal ≥ 3** | **Middel** |
| **Totaal < 3** | **Laag** |

## Risiconiveaus

| Niveau | Beschrijving |
|--------|-------------|
| 🔴 KRITIEK | Onmiddellijke actie vereist |
| 🟠 HOOG | Aandacht vereist |
| 🟡 MIDDEL | Monitoren |
| 🟢 LAAG | Ter informatie |

## Disclaimer

Dit rapport is gegenereerd door de FORENSIC_DOSSIER_ENGINE op basis van uitsluitend lokaal aangeleverde dossierdata. Elke conclusie is herleidbaar naar brondata. Dit rapport vervangt geen juridisch advies van een gekwalificeerde advocaat.

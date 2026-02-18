"""
FORENSIC_DOSSIER_ENGINE — Rapport Export (Markdown)
Genereert juridisch bruikbare rapportstructuren in Markdown-formaat.
Elke sectie is herleidbaar naar brondata.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import (
    BewijsGewicht,
    BewijsItem,
    DossierRapport,
    InconsistentieBevinding,
    MapBewijsStructuur,
    RisicoItem,
    RisicoNiveau,
    TijdlijnGebeurtenis,
    VertrouwensNiveau,
)

# ─── Opmaakhulpfuncties ───────────────────────────────────────────────────────

def _ernst_badge(niveau: RisicoNiveau) -> str:
    """Retourneert een tekstbadge voor het risiconiveau."""
    badges = {
        RisicoNiveau.KRITIEK: "🔴 KRITIEK",
        RisicoNiveau.HOOG: "🟠 HOOG",
        RisicoNiveau.MIDDEL: "🟡 MIDDEL",
        RisicoNiveau.LAAG: "🟢 LAAG",
        RisicoNiveau.GEEN: "⚪ GEEN",
    }
    return badges.get(niveau, "❓ ONBEKEND")


def _gewicht_badge(gewicht: BewijsGewicht) -> str:
    """Retourneert een tekstbadge voor het bewijsgewicht."""
    badges = {
        BewijsGewicht.HOOG: "⬆️ Hoog",
        BewijsGewicht.MIDDEL: "➡️ Middel",
        BewijsGewicht.LAAG: "⬇️ Laag",
        BewijsGewicht.ONBEKEND: "❓ Onbekend",
    }
    return badges.get(gewicht, "❓ Onbekend")


def _vertrouwen_badge(vertrouwen: VertrouwensNiveau) -> str:
    """Retourneert een tekstbadge voor het vertrouwensniveau."""
    badges = {
        VertrouwensNiveau.HOOG: "✅ Hoog",
        VertrouwensNiveau.MIDDEL: "⚠️ Middel",
        VertrouwensNiveau.LAAG: "❌ Laag",
    }
    return badges.get(vertrouwen, "❓ Onbekend")


def _scheidingslijn(breedte: int = 80) -> str:
    return "─" * breedte


def _sectie_header(titel: str, niveau: int = 2) -> str:
    prefix = "#" * niveau
    return f"\n{prefix} {titel}\n"


# ─── Rapportsecties ───────────────────────────────────────────────────────────

def _genereer_voorblad(rapport: DossierRapport) -> str:
    """Genereert het voorblad van het rapport."""
    gegenereerd = datetime.fromisoformat(rapport.gegenereerd_op).strftime(
        "%d %B %Y om %H:%M:%S UTC"
    )
    return f"""# FORENSISCH DOSSIERRAPPORT

{_scheidingslijn()}

**Rapport ID:** `{rapport.rapport_id}`  
**Gegenereerd op:** {gegenereerd}  
**Dossierlocatie:** `{rapport.dossier_pad}`  

{_scheidingslijn()}

## Samenvatting

{rapport.samenvatting}

### Statistieken

| Categorie | Aantal |
|-----------|--------|
| Totaal bestanden geanalyseerd | {rapport.totaal_bestanden} |
| Bewijsstukken verwerkt | {rapport.totaal_bewijs_items} |
| Tijdlijngebeurtenissen | {rapport.totaal_tijdlijn_gebeurtenissen} |
| Inconsistenties gedetecteerd | {rapport.totaal_inconsistenties} |
| Risico's geïdentificeerd | {rapport.totaal_risicos} |

> **Disclaimer:** Dit rapport is gegenereerd door de FORENSIC_DOSSIER_ENGINE op basis van 
> uitsluitend lokaal aangeleverde dossierdata. Elke conclusie is herleidbaar naar brondata.
> Dit rapport vervangt geen juridisch advies van een gekwalificeerde advocaat.

{_scheidingslijn()}
"""


def _genereer_conclusies_aanbevelingen(rapport: DossierRapport) -> str:
    """Genereert de conclusies en aanbevelingen sectie."""
    secties = [_sectie_header("Conclusies en Aanbevelingen", 2)]

    if rapport.conclusies:
        secties.append("### Conclusies\n")
        for i, conclusie in enumerate(rapport.conclusies, 1):
            secties.append(f"{i}. {conclusie}")
        secties.append("")

    if rapport.aanbevelingen:
        secties.append("### Aanbevelingen\n")
        for i, aanbeveling in enumerate(rapport.aanbevelingen, 1):
            secties.append(f"{i}. {aanbeveling}")
        secties.append("")

    return "\n".join(secties)


def _genereer_tijdlijn_sectie(tijdlijn: list[TijdlijnGebeurtenis]) -> str:
    """Genereert de tijdlijnsectie van het rapport."""
    secties = [_sectie_header("Tijdlijnreconstructie", 2)]

    if not tijdlijn:
        secties.append("*Geen tijdlijngebeurtenissen gedetecteerd.*\n")
        return "\n".join(secties)

    secties.append(
        f"Totaal **{len(tijdlijn)}** tijdlijngebeurtenissen gereconstrueerd, "
        f"chronologisch gesorteerd.\n"
    )

    # Groepeer per jaar voor overzichtelijkheid
    per_jaar: dict[str, list[TijdlijnGebeurtenis]] = {}
    for g in tijdlijn:
        jaar = g.tijdstip[:4] if len(g.tijdstip) >= 4 else "Onbekend"
        if jaar not in per_jaar:
            per_jaar[jaar] = []
        per_jaar[jaar].append(g)

    for jaar in sorted(per_jaar.keys()):
        secties.append(f"### {jaar}\n")
        for g in per_jaar[jaar]:
            datum = g.tijdstip[:10] if len(g.tijdstip) >= 10 else g.tijdstip
            vertrouwen = _vertrouwen_badge(g.vertrouwen)
            bewijs_refs = (
                ", ".join(f"`{id_[:8]}…`" for id_ in g.gerelateerde_bewijs_ids[:3])
                if g.gerelateerde_bewijs_ids
                else "*geen*"
            )
            secties.append(
                f"**{datum}** — {g.titel}  \n"
                f"*Vertrouwen: {vertrouwen} | Bron: {g.bron_bestand or 'onbekend'} | "
                f"Bewijs-ID: {bewijs_refs}*  \n"
                f"{g.beschrijving}\n"
            )

    return "\n".join(secties)


def _genereer_inconsistenties_sectie(
    inconsistenties: list[InconsistentieBevinding],
) -> str:
    """Genereert de inconsistentiessectie van het rapport."""
    secties = [_sectie_header("Consistency Scan — Inconsistenties", 2)]

    if not inconsistenties:
        secties.append("✅ *Geen inconsistenties gedetecteerd.*\n")
        return "\n".join(secties)

    secties.append(
        f"Totaal **{len(inconsistenties)}** inconsistentie(s) gedetecteerd.\n"
    )

    # Groepeer per type
    per_type: dict[str, list[InconsistentieBevinding]] = {}
    for b in inconsistenties:
        if b.type not in per_type:
            per_type[b.type] = []
        per_type[b.type].append(b)

    type_labels = {
        "datum_conflict": "Datumconflicten",
        "persoon_conflict": "Persoonconflicten",
        "feit_tegenspraak": "Feitelijke tegenspraken",
        "duplicaat_bestand": "Duplicaatbestanden",
    }

    for type_, bevindingen in per_type.items():
        label = type_labels.get(type_, type_.replace("_", " ").title())
        secties.append(f"### {label} ({len(bevindingen)})\n")
        for b in bevindingen:
            ernst = _ernst_badge(b.ernst)
            secties.append(
                f"**Bevinding `{b.bevinding_id}`** — Ernst: {ernst}  \n"
                f"*Bewijs A: `{b.bewijs_id_a[:8]}…` | Bewijs B: `{b.bewijs_id_b[:8]}…`*  \n"
                f"{b.beschrijving}  \n"
                f"**Aanbeveling:** {b.aanbeveling}\n"
            )

    return "\n".join(secties)


def _genereer_risico_sectie(risicos: list[RisicoItem]) -> str:
    """Genereert de risicosectie van het rapport."""
    secties = [_sectie_header("Risico-analyse", 2)]

    if not risicos:
        secties.append("✅ *Geen risico's geïdentificeerd.*\n")
        return "\n".join(secties)

    secties.append(
        f"Totaal **{len(risicos)}** risico('s) geïdentificeerd.\n"
    )

    # Overzichtstabel
    secties.append("### Risico-overzicht\n")
    secties.append("| # | Categorie | Niveau | Omschrijving |")
    secties.append("|---|-----------|--------|--------------|")
    for i, risico in enumerate(risicos, 1):
        ernst = _ernst_badge(risico.niveau)
        omschrijving_kort = risico.omschrijving[:80] + "…" if len(risico.omschrijving) > 80 else risico.omschrijving
        secties.append(
            f"| {i} | {risico.categorie.title()} | {ernst} | {omschrijving_kort} |"
        )
    secties.append("")

    # Gedetailleerde risico's per categorie
    per_categorie: dict[str, list[RisicoItem]] = {}
    for r in risicos:
        if r.categorie not in per_categorie:
            per_categorie[r.categorie] = []
        per_categorie[r.categorie].append(r)

    for categorie, items in per_categorie.items():
        secties.append(f"### {categorie.title()} Risico's\n")
        for r in items:
            ernst = _ernst_badge(r.niveau)
            bewijs_refs = (
                ", ".join(f"`{id_[:8]}…`" for id_ in r.betrokken_bewijs_ids[:3])
                if r.betrokken_bewijs_ids
                else "*geen specifiek bewijs*"
            )
            secties.append(
                f"**Risico `{r.risico_id}`** — {ernst}  \n"
                f"*Betrokken bewijs: {bewijs_refs}*  \n"
                f"{r.omschrijving}  \n"
                f"**Mitigatie:** {r.mitigatie_advies}\n"
            )

    return "\n".join(secties)


def _genereer_bewijs_structuur_sectie(
    map_structuren: list[MapBewijsStructuur],
) -> str:
    """Genereert de bewijsstructuursectie per map."""
    secties = [_sectie_header("Bewijsstructuur per Map", 2)]

    for structuur in map_structuren:
        secties.append(f"### Map: `{structuur.map_naam}/`\n")
        secties.append(f"**Pad:** `{structuur.map_pad}`  ")
        secties.append(f"**Aantal bestanden:** {structuur.aantal_bestanden}  ")
        secties.append(f"**Dominante persoon:** {structuur.dominante_persoon}  ")
        secties.append(f"**Dominante zaak:** {structuur.dominante_zaak}  ")
        if structuur.tijdspanne_van and structuur.tijdspanne_tot:
            secties.append(
                f"**Tijdspanne:** {structuur.tijdspanne_van} → {structuur.tijdspanne_tot}  "
            )
        secties.append(f"\n{structuur.samenvatting}\n")

        if structuur.bewijs_items:
            secties.append("#### Bewijsstukken\n")
            secties.append("| Bestand | Persoon | Relevantie | Gewicht | Bewijs-ID |")
            secties.append("|---------|---------|------------|---------|-----------|")
            for item in structuur.bewijs_items:
                gewicht = _gewicht_badge(item.bewijsgewicht)
                secties.append(
                    f"| `{item.bestandsnaam}` | {item.gedetecteerde_persoon} | "
                    f"{item.juridische_relevantie} | {gewicht} | `{item.bewijs_id[:8]}…` |"
                )
            secties.append("")

    return "\n".join(secties)


def _genereer_bewijs_details_sectie(bewijs_items: list[BewijsItem]) -> str:
    """Genereert gedetailleerde bewijsstukken sectie."""
    secties = [_sectie_header("Gedetailleerde Bewijsstukken", 2)]

    if not bewijs_items:
        secties.append("*Geen bewijsstukken beschikbaar.*\n")
        return "\n".join(secties)

    secties.append(
        f"Totaal **{len(bewijs_items)}** bewijsstuk(ken) geanalyseerd.\n"
    )

    for item in bewijs_items:
        gewicht = _gewicht_badge(item.bewijsgewicht)
        secties.append(f"### `{item.bestandsnaam}`\n")
        secties.append(f"**Bewijs-ID:** `{item.bewijs_id}`  ")
        secties.append(f"**Bronmap:** `{item.bron_map}/`  ")
        secties.append(f"**Geïmporteerd:** {item.geimporteerd_op[:19]}  ")
        secties.append(f"**Persoon:** {item.gedetecteerde_persoon}  ")
        secties.append(f"**Zaak:** {item.gedetecteerde_zaak}  ")
        secties.append(f"**Juridische relevantie:** {item.juridische_relevantie}  ")
        secties.append(f"**Bewijsgewicht:** {gewicht}  ")
        secties.append(f"**SHA-256:** `{item.inhoud_hash[:32]}…`  ")
        secties.append("")

        # Bewijs-keten
        if item.bewijs_keten:
            secties.append("**Bewijs-keten (Chain of Custody):**")
            for stap in item.bewijs_keten:
                secties.append(f"- {stap}")
            secties.append("")

        # Gevonden datums
        if item.analyse.datums_gevonden:
            secties.append(
                f"**Gevonden datums:** {', '.join(item.analyse.datums_gevonden[:10])}"
            )
            secties.append("")

        # Juridische termen
        if item.analyse.juridische_termen:
            secties.append(
                f"**Juridische termen:** {', '.join(item.analyse.juridische_termen)}"
            )
            secties.append("")

        # Feiten (eerste 5)
        if item.analyse.feiten:
            secties.append("**Geëxtraheerde feiten (eerste 5):**")
            for feit in item.analyse.feiten[:5]:
                secties.append(f"- {feit[:150]}")
            secties.append("")

        # Aannames (eerste 3)
        if item.analyse.aannames:
            secties.append("**Gedetecteerde aannames (eerste 3):**")
            for aanname in item.analyse.aannames[:3]:
                secties.append(f"- ⚠️ {aanname[:150]}")
            secties.append("")

        # Interne inconsistenties
        if item.analyse.inconsistenties:
            secties.append("**Interne inconsistenties:**")
            for inc in item.analyse.inconsistenties[:3]:
                secties.append(f"- ❗ {inc[:150]}")
            secties.append("")

        secties.append(_scheidingslijn(40))
        secties.append("")

    return "\n".join(secties)


# ─── Hoofdexportfunctie ───────────────────────────────────────────────────────

def exporteer_rapport_markdown(
    rapport: DossierRapport,
    uitvoer_pad: Path,
) -> Path:
    """
    Exporteert het volledige forensische dossierrapport als Markdown-bestand.
    
    Structuur:
    1. Voorblad met samenvatting en statistieken
    2. Conclusies en aanbevelingen
    3. Tijdlijnreconstructie
    4. Consistency scan — Inconsistenties
    5. Risico-analyse
    6. Bewijsstructuur per map
    7. Gedetailleerde bewijsstukken
    
    Retourneert het pad naar het gegenereerde rapport.
    """
    uitvoer_pad.parent.mkdir(parents=True, exist_ok=True)

    secties = [
        _genereer_voorblad(rapport),
        _genereer_conclusies_aanbevelingen(rapport),
        _genereer_tijdlijn_sectie(rapport.tijdlijn),
        _genereer_inconsistenties_sectie(rapport.inconsistenties),
        _genereer_risico_sectie(rapport.risicos),
        _genereer_bewijs_structuur_sectie(rapport.map_structuren),
        _genereer_bewijs_details_sectie(rapport.bewijs_items),
    ]

    # Voettekst
    secties.append(
        f"\n{_scheidingslijn()}\n"
        f"*Rapport gegenereerd door FORENSIC_DOSSIER_ENGINE v1.0.0 — "
        f"{rapport.gegenereerd_op[:19]} UTC*  \n"
        f"*Alle conclusies zijn herleidbaar naar lokale brondata. "
        f"Geen externe bronnen geraadpleegd.*\n"
    )

    inhoud = "\n".join(secties)
    uitvoer_pad.write_text(inhoud, encoding="utf-8")

    return uitvoer_pad


def exporteer_tijdlijn_markdown(
    tijdlijn: list[TijdlijnGebeurtenis],
    uitvoer_pad: Path,
) -> Path:
    """Exporteert alleen de tijdlijn als apart Markdown-bestand."""
    uitvoer_pad.parent.mkdir(parents=True, exist_ok=True)
    inhoud = f"# Tijdlijn Export\n\n{_genereer_tijdlijn_sectie(tijdlijn)}"
    uitvoer_pad.write_text(inhoud, encoding="utf-8")
    return uitvoer_pad


def exporteer_risicos_markdown(
    risicos: list[RisicoItem],
    uitvoer_pad: Path,
) -> Path:
    """Exporteert alleen de risico-analyse als apart Markdown-bestand."""
    uitvoer_pad.parent.mkdir(parents=True, exist_ok=True)
    inhoud = f"# Risico-analyse Export\n\n{_genereer_risico_sectie(risicos)}"
    uitvoer_pad.write_text(inhoud, encoding="utf-8")
    return uitvoer_pad

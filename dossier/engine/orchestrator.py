"""
FORENSIC_DOSSIER_ENGINE — Hoofdorchestrator
Coördineert alle analysestappen en genereert het eindrapport.
Werkt uitsluitend met lokale dossierdata.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from .bewijs_structuur import bouw_bewijs_structuur, genereer_bewijs_index
from .consistency_scan import voer_consistency_scan_uit
from .importer import importeer_bestanden
from .models import DossierRapport, RisicoNiveau
from .rapport_export import (
    exporteer_rapport_markdown,
    exporteer_risicos_markdown,
    exporteer_tijdlijn_markdown,
)
from .risico_analyse import voer_risico_analyse_uit
from .tijdlijn import bouw_tijdlijn, detecteer_temporele_gaten

# ─── Logger ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("forensic_dossier_engine")


# ─── Samenvatting generator ───────────────────────────────────────────────────

def _genereer_samenvatting(
    totaal_bewijs: int,
    totaal_tijdlijn: int,
    totaal_inconsistenties: int,
    totaal_risicos: int,
    kritieke_risicos: int,
    hoge_risicos: int,
) -> str:
    """Genereert een beknopte samenvatting van het dossier."""
    status = "KRITIEK" if kritieke_risicos > 0 else ("AANDACHT VEREIST" if hoge_risicos > 0 else "NORMAAL")
    return (
        f"Het forensisch dossier bevat {totaal_bewijs} bewijsstuk(ken) "
        f"met {totaal_tijdlijn} tijdlijngebeurtenissen. "
        f"Er zijn {totaal_inconsistenties} inconsistentie(s) en "
        f"{totaal_risicos} risico('s) geïdentificeerd "
        f"(waarvan {kritieke_risicos} kritiek en {hoge_risicos} hoog). "
        f"Algehele dossierstatus: **{status}**."
    )


def _genereer_conclusies(
    bewijs_items,
    tijdlijn,
    inconsistenties,
    risicos,
    temporele_gaten,
) -> list[str]:
    """Genereert juridisch bruikbare conclusies op basis van de analyse."""
    conclusies: list[str] = []

    # Bewijsconclusies
    if not bewijs_items:
        conclusies.append(
            "Het dossier bevat geen bewijsstukken. "
            "Voeg bestanden toe aan dossier/data, dossier/evidence of dossier/timeline."
        )
    else:
        hoog_gewicht = sum(1 for i in bewijs_items if i.bewijsgewicht.value == "hoog")
        hoog_relevantie = sum(1 for i in bewijs_items if i.juridische_relevantie == "Hoog")
        conclusies.append(
            f"Van de {len(bewijs_items)} bewijsstukken hebben "
            f"{hoog_gewicht} een hoog bewijsgewicht en "
            f"{hoog_relevantie} een hoge juridische relevantie."
        )

    # Tijdlijnconclusies
    if tijdlijn:
        vroegste = tijdlijn[0].tijdstip[:10] if tijdlijn else "onbekend"
        laatste = tijdlijn[-1].tijdstip[:10] if tijdlijn else "onbekend"
        conclusies.append(
            f"De tijdlijn beslaat de periode van {vroegste} tot {laatste} "
            f"met {len(tijdlijn)} geregistreerde gebeurtenissen."
        )

    # Temporele gaten
    if temporele_gaten:
        grootste_gat = max(temporele_gaten, key=lambda g: g["duur_dagen"])
        conclusies.append(
            f"Er zijn {len(temporele_gaten)} tijdsgat(en) gedetecteerd. "
            f"Het grootste gat bedraagt {grootste_gat['duur_dagen']} dagen "
            f"({grootste_gat['van']} → {grootste_gat['tot']})."
        )

    # Inconsistentieconclusies
    if inconsistenties:
        hoge_ernst = sum(
            1 for b in inconsistenties
            if b.ernst in (RisicoNiveau.KRITIEK, RisicoNiveau.HOOG)
        )
        conclusies.append(
            f"Er zijn {len(inconsistenties)} inconsistentie(s) gedetecteerd, "
            f"waarvan {hoge_ernst} van hoge of kritieke ernst. "
            f"Deze vereisen nader onderzoek."
        )
    else:
        conclusies.append(
            "Geen significante inconsistenties gedetecteerd tussen de bewijsstukken."
        )

    # Risiconconclusies
    kritieke = [r for r in risicos if r.niveau == RisicoNiveau.KRITIEK]
    if kritieke:
        conclusies.append(
            f"KRITIEK: {len(kritieke)} kritiek risico('s) geïdentificeerd. "
            f"Onmiddellijke actie vereist: "
            f"{'; '.join(r.omschrijving[:80] for r in kritieke[:2])}."
        )

    return conclusies


def _genereer_aanbevelingen(risicos, inconsistenties, bewijs_items) -> list[str]:
    """Genereert prioritaire aanbevelingen."""
    aanbevelingen: list[str] = []

    # Kritieke risico-aanbevelingen eerst
    for risico in risicos:
        if risico.niveau == RisicoNiveau.KRITIEK:
            aanbevelingen.append(f"[KRITIEK] {risico.mitigatie_advies}")

    # Hoge risico-aanbevelingen
    for risico in risicos:
        if risico.niveau == RisicoNiveau.HOOG:
            aanbevelingen.append(f"[HOOG] {risico.mitigatie_advies}")

    # Inconsistentie-aanbevelingen
    for bevinding in inconsistenties[:3]:
        if bevinding.ernst in (RisicoNiveau.KRITIEK, RisicoNiveau.HOOG):
            aanbevelingen.append(f"[INCONSISTENTIE] {bevinding.aanbeveling}")

    # Algemene aanbevelingen
    if not bewijs_items:
        aanbevelingen.append(
            "Voeg bewijsstukken toe aan de dossiermappen "
            "(dossier/data, dossier/evidence, dossier/timeline)."
        )

    if not aanbevelingen:
        aanbevelingen.append(
            "Het dossier is in goede staat. "
            "Blijf bewijsstukken actueel houden en documenteer nieuwe ontwikkelingen."
        )

    return aanbevelingen[:15]  # Maximaal 15 aanbevelingen


# ─── Hoofdorchestrator ────────────────────────────────────────────────────────

def voer_volledige_analyse_uit(
    dossier_root: Path,
    uitvoer_map: Path | None = None,
) -> DossierRapport:
    """
    Voert de volledige forensische dossieranalyse uit.
    
    Stappen:
    1. Importeer alle bestanden uit dossier/data, dossier/evidence, dossier/timeline
    2. Bouw tijdlijn
    3. Detecteer temporele gaten
    4. Voer consistency scan uit
    5. Voer risico-analyse uit
    6. Bouw bewijsstructuur per map
    7. Genereer rapport
    8. Exporteer naar Markdown
    
    Werkt uitsluitend met lokale dossierdata.
    Elke conclusie is herleidbaar naar brondata.
    """
    if uitvoer_map is None:
        uitvoer_map = dossier_root / "output"

    uitvoer_map.mkdir(parents=True, exist_ok=True)

    logger.info("═" * 60)
    logger.info("FORENSIC_DOSSIER_ENGINE — Analyse gestart")
    logger.info("Dossierlocatie: %s", dossier_root)
    logger.info("═" * 60)

    # ── Stap 1: Importeer bestanden ───────────────────────────────────────────
    logger.info("Stap 1/6: Bestanden importeren...")
    bewijs_items = importeer_bestanden(dossier_root)
    logger.info("  → %d bewijsstuk(ken) geïmporteerd", len(bewijs_items))

    # ── Stap 2: Tijdlijn bouwen ───────────────────────────────────────────────
    logger.info("Stap 2/6: Tijdlijn reconstrueren...")
    tijdlijn = bouw_tijdlijn(bewijs_items)
    temporele_gaten = detecteer_temporele_gaten(tijdlijn, drempel_dagen=90)
    logger.info(
        "  → %d tijdlijngebeurtenissen, %d temporele gaten",
        len(tijdlijn),
        len(temporele_gaten),
    )

    # ── Stap 3: Consistency scan ──────────────────────────────────────────────
    logger.info("Stap 3/6: Consistency scan uitvoeren...")
    inconsistenties = voer_consistency_scan_uit(bewijs_items)
    logger.info("  → %d inconsistentie(s) gedetecteerd", len(inconsistenties))

    # ── Stap 4: Risico-analyse ────────────────────────────────────────────────
    logger.info("Stap 4/6: Risico-analyse uitvoeren...")
    risicos = voer_risico_analyse_uit(
        bewijs_items, tijdlijn, inconsistenties, temporele_gaten
    )
    kritieke_risicos = sum(1 for r in risicos if r.niveau == RisicoNiveau.KRITIEK)
    hoge_risicos = sum(1 for r in risicos if r.niveau == RisicoNiveau.HOOG)
    logger.info(
        "  → %d risico('s) (%d kritiek, %d hoog)",
        len(risicos),
        kritieke_risicos,
        hoge_risicos,
    )

    # ── Stap 5: Bewijsstructuur per map ───────────────────────────────────────
    logger.info("Stap 5/6: Bewijsstructuur per map bouwen...")
    map_structuren = bouw_bewijs_structuur(bewijs_items, dossier_root)
    logger.info("  → %d mapstructuren gebouwd", len(map_structuren))

    # ── Stap 6: Rapport genereren ─────────────────────────────────────────────
    logger.info("Stap 6/6: Rapport genereren...")
    gegenereerd_op = datetime.utcnow().isoformat()
    rapport_id = hashlib.md5(
        f"{dossier_root}-{gegenereerd_op}".encode()
    ).hexdigest()[:16]

    samenvatting = _genereer_samenvatting(
        len(bewijs_items),
        len(tijdlijn),
        len(inconsistenties),
        len(risicos),
        kritieke_risicos,
        hoge_risicos,
    )

    conclusies = _genereer_conclusies(
        bewijs_items, tijdlijn, inconsistenties, risicos, temporele_gaten
    )
    aanbevelingen = _genereer_aanbevelingen(risicos, inconsistenties, bewijs_items)

    rapport = DossierRapport(
        rapport_id=rapport_id,
        gegenereerd_op=gegenereerd_op,
        dossier_pad=str(dossier_root),
        totaal_bestanden=len(bewijs_items),
        totaal_bewijs_items=len(bewijs_items),
        totaal_tijdlijn_gebeurtenissen=len(tijdlijn),
        totaal_inconsistenties=len(inconsistenties),
        totaal_risicos=len(risicos),
        bewijs_items=bewijs_items,
        tijdlijn=tijdlijn,
        inconsistenties=inconsistenties,
        risicos=risicos,
        map_structuren=map_structuren,
        samenvatting=samenvatting,
        conclusies=conclusies,
        aanbevelingen=aanbevelingen,
    )

    # ── Export naar Markdown ──────────────────────────────────────────────────
    hoofdrapport_pad = uitvoer_map / "hoofdrapport.md"
    exporteer_rapport_markdown(rapport, hoofdrapport_pad)
    logger.info("  → Hoofdrapport: %s", hoofdrapport_pad)

    tijdlijn_pad = uitvoer_map / "tijdlijn.md"
    exporteer_tijdlijn_markdown(tijdlijn, tijdlijn_pad)
    logger.info("  → Tijdlijn: %s", tijdlijn_pad)

    risico_pad = uitvoer_map / "risico_analyse.md"
    exporteer_risicos_markdown(risicos, risico_pad)
    logger.info("  → Risico-analyse: %s", risico_pad)

    # ── JSON-export voor machine-leesbaarheid ─────────────────────────────────
    _exporteer_json_samenvatting(rapport, uitvoer_map / "samenvatting.json")
    logger.info("  → JSON-samenvatting: %s", uitvoer_map / "samenvatting.json")

    logger.info("═" * 60)
    logger.info("Analyse voltooid. Rapporten opgeslagen in: %s", uitvoer_map)
    logger.info("═" * 60)

    return rapport


def _exporteer_json_samenvatting(rapport: DossierRapport, pad: Path) -> None:
    """Exporteert een JSON-samenvatting voor machine-leesbaarheid."""
    samenvatting = {
        "rapport_id": rapport.rapport_id,
        "gegenereerd_op": rapport.gegenereerd_op,
        "dossier_pad": rapport.dossier_pad,
        "statistieken": {
            "totaal_bestanden": rapport.totaal_bestanden,
            "totaal_bewijs_items": rapport.totaal_bewijs_items,
            "totaal_tijdlijn_gebeurtenissen": rapport.totaal_tijdlijn_gebeurtenissen,
            "totaal_inconsistenties": rapport.totaal_inconsistenties,
            "totaal_risicos": rapport.totaal_risicos,
        },
        "samenvatting": rapport.samenvatting,
        "conclusies": rapport.conclusies,
        "aanbevelingen": rapport.aanbevelingen,
        "risico_niveaus": {
            "kritiek": sum(1 for r in rapport.risicos if r.niveau == RisicoNiveau.KRITIEK),
            "hoog": sum(1 for r in rapport.risicos if r.niveau == RisicoNiveau.HOOG),
            "middel": sum(1 for r in rapport.risicos if r.niveau == RisicoNiveau.MIDDEL),
            "laag": sum(1 for r in rapport.risicos if r.niveau == RisicoNiveau.LAAG),
        },
        "bewijs_ids": [item.bewijs_id for item in rapport.bewijs_items],
        "inconsistentie_types": list(
            set(b.type for b in rapport.inconsistenties)
        ),
    }
    pad.write_text(
        json.dumps(samenvatting, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

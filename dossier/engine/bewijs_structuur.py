"""
FORENSIC_DOSSIER_ENGINE — Bewijsstructuur per map
Bouwt een gestructureerd overzicht van bewijsstukken per dossiermapstructuur.
Elke structuur is herleidbaar naar de bronbestanden.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    BewijsGewicht,
    BewijsItem,
    MapBewijsStructuur,
)

# ─── Hulpfuncties ─────────────────────────────────────────────────────────────

def _meest_voorkomende(waarden: list[str]) -> str:
    """Retourneert de meest voorkomende waarde in een lijst."""
    if not waarden:
        return "Onbekend"
    teller = Counter(waarden)
    return teller.most_common(1)[0][0]


def _vroegste_datum(datums: list[str]) -> str:
    """Retourneert de vroegste datum uit een lijst van ISO-datumstrings."""
    geldige: list[datetime] = []
    for d in datums:
        try:
            geldige.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
        except Exception:
            continue
    if not geldige:
        return ""
    return min(geldige).isoformat()[:10]


def _laatste_datum(datums: list[str]) -> str:
    """Retourneert de laatste datum uit een lijst van ISO-datumstrings."""
    geldige: list[datetime] = []
    for d in datums:
        try:
            geldige.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
        except Exception:
            continue
    if not geldige:
        return ""
    return max(geldige).isoformat()[:10]


def _genereer_map_samenvatting(
    map_naam: str,
    items: list[BewijsItem],
) -> str:
    """Genereert een tekstuele samenvatting van de bewijsstukken in een map."""
    if not items:
        return f"Map '{map_naam}' bevat geen bewijsstukken."

    hoog_gewicht = sum(1 for i in items if i.bewijsgewicht == BewijsGewicht.HOOG)
    middel_gewicht = sum(1 for i in items if i.bewijsgewicht == BewijsGewicht.MIDDEL)
    laag_gewicht = sum(1 for i in items if i.bewijsgewicht == BewijsGewicht.LAAG)

    hoog_relevantie = sum(1 for i in items if i.juridische_relevantie == "Hoog")
    middel_relevantie = sum(1 for i in items if i.juridische_relevantie == "Middel")

    personen = [i.gedetecteerde_persoon for i in items if i.gedetecteerde_persoon != "Onbekend"]
    dominante_persoon = _meest_voorkomende(personen) if personen else "Onbekend"

    zaken = [i.gedetecteerde_zaak for i in items]
    dominante_zaak = _meest_voorkomende(zaken)

    alle_datums = []
    for item in items:
        alle_datums.extend(item.analyse.datums_gevonden)

    tijdspanne = ""
    if alle_datums:
        vroeg = _vroegste_datum(alle_datums)
        laat = _laatste_datum(alle_datums)
        if vroeg and laat:
            tijdspanne = f" Tijdspanne: {vroeg} tot {laat}."

    return (
        f"Map '{map_naam}' bevat {len(items)} bewijsstuk(ken). "
        f"Bewijsgewicht: {hoog_gewicht} hoog, {middel_gewicht} middel, {laag_gewicht} laag. "
        f"Juridische relevantie: {hoog_relevantie} hoog, {middel_relevantie} middel. "
        f"Dominante persoon: {dominante_persoon}. "
        f"Dominante zaak: {dominante_zaak}.{tijdspanne}"
    )


# ─── Structuurbouwer ──────────────────────────────────────────────────────────

def bouw_bewijs_structuur(
    bewijs_items: list[BewijsItem],
    dossier_root: Path,
) -> list[MapBewijsStructuur]:
    """
    Bouwt een gestructureerd overzicht van bewijsstukken per map.
    
    Mappen:
    - dossier/data: Ruwe data en bronbestanden
    - dossier/evidence: Bewijsstukken
    - dossier/timeline: Tijdlijn-gerelateerde documenten
    
    Elke structuur bevat:
    - Lijst van bewijsstukken
    - Samenvatting
    - Dominante persoon en zaak
    - Tijdspanne
    """
    # Groepeer per map
    per_map: dict[str, list[BewijsItem]] = defaultdict(list)
    for item in bewijs_items:
        per_map[item.bron_map].append(item)

    # Zorg dat alle verwachte mappen aanwezig zijn
    verwachte_mappen = ["data", "evidence", "timeline"]
    for map_naam in verwachte_mappen:
        if map_naam not in per_map:
            per_map[map_naam] = []

    structuren: list[MapBewijsStructuur] = []

    for map_naam in verwachte_mappen:
        items = per_map[map_naam]
        map_pad = dossier_root / map_naam

        # Verzamel alle datums
        alle_datums: list[str] = []
        for item in items:
            alle_datums.extend(item.analyse.datums_gevonden)
        # Voeg importtijdstippen toe
        alle_datums.extend(item.geimporteerd_op for item in items)

        personen = [
            item.gedetecteerde_persoon
            for item in items
            if item.gedetecteerde_persoon != "Onbekend"
        ]
        zaken = [item.gedetecteerde_zaak for item in items]

        structuur = MapBewijsStructuur(
            map_naam=map_naam,
            map_pad=str(map_pad),
            aantal_bestanden=len(items),
            bewijs_items=items,
            samenvatting=_genereer_map_samenvatting(map_naam, items),
            dominante_persoon=_meest_voorkomende(personen) if personen else "Onbekend",
            dominante_zaak=_meest_voorkomende(zaken) if zaken else "Onbekend",
            tijdspanne_van=_vroegste_datum(alle_datums),
            tijdspanne_tot=_laatste_datum(alle_datums),
        )
        structuren.append(structuur)

    # Voeg ook eventuele onverwachte mappen toe
    for map_naam, items in per_map.items():
        if map_naam not in verwachte_mappen:
            map_pad = dossier_root / map_naam
            alle_datums = []
            for item in items:
                alle_datums.extend(item.analyse.datums_gevonden)
            alle_datums.extend(item.geimporteerd_op for item in items)

            personen = [
                item.gedetecteerde_persoon
                for item in items
                if item.gedetecteerde_persoon != "Onbekend"
            ]
            zaken = [item.gedetecteerde_zaak for item in items]

            structuur = MapBewijsStructuur(
                map_naam=map_naam,
                map_pad=str(map_pad),
                aantal_bestanden=len(items),
                bewijs_items=items,
                samenvatting=_genereer_map_samenvatting(map_naam, items),
                dominante_persoon=_meest_voorkomende(personen) if personen else "Onbekend",
                dominante_zaak=_meest_voorkomende(zaken) if zaken else "Onbekend",
                tijdspanne_van=_vroegste_datum(alle_datums),
                tijdspanne_tot=_laatste_datum(alle_datums),
            )
            structuren.append(structuur)

    return structuren


def genereer_bewijs_index(bewijs_items: list[BewijsItem]) -> dict:
    """
    Genereert een index van alle bewijsstukken voor snelle opzoeking.
    
    Retourneert:
    - Index op bewijs_id
    - Index op persoon
    - Index op zaak
    - Index op bewijsgewicht
    """
    op_id: dict[str, BewijsItem] = {item.bewijs_id: item for item in bewijs_items}

    op_persoon: dict[str, list[str]] = defaultdict(list)
    for item in bewijs_items:
        op_persoon[item.gedetecteerde_persoon].append(item.bewijs_id)

    op_zaak: dict[str, list[str]] = defaultdict(list)
    for item in bewijs_items:
        op_zaak[item.gedetecteerde_zaak].append(item.bewijs_id)

    op_gewicht: dict[str, list[str]] = defaultdict(list)
    for item in bewijs_items:
        op_gewicht[item.bewijsgewicht.value].append(item.bewijs_id)

    return {
        "op_id": op_id,
        "op_persoon": dict(op_persoon),
        "op_zaak": dict(op_zaak),
        "op_gewicht": dict(op_gewicht),
        "totaal": len(bewijs_items),
    }

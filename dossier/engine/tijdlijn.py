"""
FORENSIC_DOSSIER_ENGINE — Tijdlijnreconstructie
Reconstrueert een chronologische tijdlijn uit alle bewijsstukken.
Elke gebeurtenis is herleidbaar naar het bronbewijsstuk.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from .models import BewijsItem, TijdlijnGebeurtenis, VertrouwensNiveau

# ─── Datumparser ──────────────────────────────────────────────────────────────

MAANDEN_NL = {
    "januari": "01", "februari": "02", "maart": "03", "april": "04",
    "mei": "05", "juni": "06", "juli": "07", "augustus": "08",
    "september": "09", "oktober": "10", "november": "11", "december": "12",
}

DATUM_FORMATEN = [
    # ISO: 2024-01-15
    (re.compile(r"\b(20\d{2})[-/](\d{2})[-/](\d{2})\b"), "iso"),
    # NL: 15-01-2024 of 15/01/2024
    (re.compile(r"\b(\d{2})[-/](\d{2})[-/](20\d{2})\b"), "nl"),
    # Uitgeschreven: 15 januari 2024
    (re.compile(
        r"\b(\d{1,2})\s+(januari|februari|maart|april|mei|juni|"
        r"juli|augustus|september|oktober|november|december)\s+(20\d{2})\b",
        re.IGNORECASE,
    ), "nl_uitgeschreven"),
]


def _normaliseer_datum(datum_str: str) -> Optional[str]:
    """Converteert een datumstring naar ISO 8601 formaat (YYYY-MM-DD)."""
    for patroon, formaat in DATUM_FORMATEN:
        match = patroon.search(datum_str)
        if not match:
            continue
        try:
            if formaat == "iso":
                jaar, maand, dag = match.group(1), match.group(2), match.group(3)
            elif formaat == "nl":
                dag, maand, jaar = match.group(1), match.group(2), match.group(3)
            else:  # nl_uitgeschreven
                dag = match.group(1).zfill(2)
                maand = MAANDEN_NL.get(match.group(2).lower(), "01")
                jaar = match.group(3)
            # Valideer
            datetime(int(jaar), int(maand), int(dag))
            return f"{jaar}-{maand.zfill(2)}-{dag.zfill(2)}"
        except (ValueError, AttributeError):
            continue
    return None


def _als_datetime(tijdstip: str) -> datetime:
    """Converteert tijdstip-string naar datetime voor sortering."""
    try:
        return datetime.fromisoformat(tijdstip.replace("Z", "+00:00"))
    except Exception:
        return datetime.min


def _extraheer_context_rond_datum(tekst: str, datum: str, venster: int = 150) -> str:
    """Extraheert de tekstcontext rondom een gevonden datum."""
    pos = tekst.lower().find(datum.lower())
    if pos == -1:
        # Probeer gedeeltelijke match
        jaar = datum[:4]
        pos = tekst.find(jaar)
    if pos == -1:
        return tekst[:200]
    start = max(0, pos - venster)
    einde = min(len(tekst), pos + len(datum) + venster)
    fragment = tekst[start:einde].strip()
    # Verwijder regelafbrekingen voor leesbaarheid
    return " ".join(fragment.split())[:300]


# ─── Tijdlijnbouwer ───────────────────────────────────────────────────────────

def bouw_tijdlijn(bewijs_items: list[BewijsItem]) -> list[TijdlijnGebeurtenis]:
    """
    Reconstrueert een chronologische tijdlijn uit alle bewijsstukken.
    
    Bronnen van tijdlijngebeurtenissen:
    1. Importtijdstip van elk bewijsstuk (hoge betrouwbaarheid)
    2. Datums gedetecteerd in de tekst (middel betrouwbaarheid)
    3. Datums in bestandsnamen (lage betrouwbaarheid)
    
    Elke gebeurtenis bevat een verwijzing naar het bronbewijsstuk.
    """
    gebeurtenissen: list[TijdlijnGebeurtenis] = []
    teller: dict[str, int] = {}

    for item in bewijs_items:
        # ── 1. Importgebeurtenis ──────────────────────────────────────────────
        import_id = f"import-{item.bewijs_id[:8]}"
        gebeurtenissen.append(
            TijdlijnGebeurtenis(
                gebeurtenis_id=import_id,
                tijdstip=item.geimporteerd_op,
                titel=f"Bestand geïmporteerd: {item.bestandsnaam}",
                beschrijving=(
                    f"Bestand '{item.bestandsnaam}' geïmporteerd uit map '{item.bron_map}'. "
                    f"Juridische relevantie: {item.juridische_relevantie}. "
                    f"Bewijsgewicht: {item.bewijsgewicht.value}. "
                    f"Gedetecteerde persoon: {item.gedetecteerde_persoon}."
                ),
                gerelateerde_bewijs_ids=[item.bewijs_id],
                vertrouwen=VertrouwensNiveau.HOOG,
                bron_bestand=item.bestandsnaam,
            )
        )

        # ── 2. Datums uit tekst ───────────────────────────────────────────────
        for datum_str in item.analyse.datums_gevonden:
            genormaliseerd = _normaliseer_datum(datum_str)
            if not genormaliseerd:
                continue

            teller_key = f"{item.bewijs_id}-{genormaliseerd}"
            teller[teller_key] = teller.get(teller_key, 0) + 1
            index = teller[teller_key]

            context = _extraheer_context_rond_datum(
                item.geextraheerde_tekst, datum_str
            )

            gebeurtenis_id = f"datum-{item.bewijs_id[:8]}-{genormaliseerd}-{index}"
            gebeurtenissen.append(
                TijdlijnGebeurtenis(
                    gebeurtenis_id=gebeurtenis_id,
                    tijdstip=f"{genormaliseerd}T00:00:00",
                    titel=f"Datum gedetecteerd in {item.bestandsnaam}",
                    beschrijving=(
                        f"Datum '{datum_str}' gevonden in '{item.bestandsnaam}'. "
                        f"Context: {context}"
                    ),
                    gerelateerde_bewijs_ids=[item.bewijs_id],
                    vertrouwen=VertrouwensNiveau.MIDDEL,
                    bron_bestand=item.bestandsnaam,
                )
            )

        # ── 3. Datum in bestandsnaam ──────────────────────────────────────────
        datum_in_naam = _normaliseer_datum(item.bestandsnaam)
        if datum_in_naam:
            naam_id = f"bestandsnaam-{item.bewijs_id[:8]}"
            gebeurtenissen.append(
                TijdlijnGebeurtenis(
                    gebeurtenis_id=naam_id,
                    tijdstip=f"{datum_in_naam}T00:00:00",
                    titel=f"Datum in bestandsnaam: {item.bestandsnaam}",
                    beschrijving=(
                        f"Bestandsnaam '{item.bestandsnaam}' bevat datum '{datum_in_naam}'. "
                        f"Persoon: {item.gedetecteerde_persoon}. "
                        f"Zaak: {item.gedetecteerde_zaak}."
                    ),
                    gerelateerde_bewijs_ids=[item.bewijs_id],
                    vertrouwen=VertrouwensNiveau.LAAG,
                    bron_bestand=item.bestandsnaam,
                )
            )

    # ── Sorteren op tijdstip ──────────────────────────────────────────────────
    gesorteerd = sorted(gebeurtenissen, key=lambda g: _als_datetime(g.tijdstip))

    # ── Duplicaten verwijderen (zelfde tijdstip + zelfde bewijs_id) ───────────
    gezien: set[str] = set()
    uniek: list[TijdlijnGebeurtenis] = []
    for g in gesorteerd:
        sleutel = f"{g.tijdstip[:10]}-{g.gerelateerde_bewijs_ids[0] if g.gerelateerde_bewijs_ids else ''}"
        if sleutel not in gezien or g.vertrouwen == VertrouwensNiveau.HOOG:
            uniek.append(g)
            gezien.add(sleutel)

    return uniek


def detecteer_temporele_gaten(
    tijdlijn: list[TijdlijnGebeurtenis],
    drempel_dagen: int = 90,
) -> list[dict]:
    """
    Detecteert onverklaarbare tijdsgaten in de tijdlijn.
    Retourneert een lijst van gaten met begin, einde en duur.
    """
    gaten: list[dict] = []
    if len(tijdlijn) < 2:
        return gaten

    vorige_dt = _als_datetime(tijdlijn[0].tijdstip)
    for gebeurtenis in tijdlijn[1:]:
        huidige_dt = _als_datetime(gebeurtenis.tijdstip)
        if huidige_dt == datetime.min or vorige_dt == datetime.min:
            vorige_dt = huidige_dt
            continue
        verschil = (huidige_dt - vorige_dt).days
        if verschil > drempel_dagen:
            gaten.append({
                "van": vorige_dt.isoformat()[:10],
                "tot": huidige_dt.isoformat()[:10],
                "duur_dagen": verschil,
                "beschrijving": (
                    f"Tijdsgat van {verschil} dagen gedetecteerd "
                    f"({vorige_dt.strftime('%d-%m-%Y')} → "
                    f"{huidige_dt.strftime('%d-%m-%Y')})"
                ),
            })
        vorige_dt = huidige_dt

    return gaten

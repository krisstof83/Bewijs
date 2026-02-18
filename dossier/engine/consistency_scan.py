"""
FORENSIC_DOSSIER_ENGINE — Consistency Scan
Detecteert inconsistenties en tegenstrijdigheden tussen bewijsstukken.
Elke bevinding is herleidbaar naar de bronbewijsstukken.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime
from typing import Optional

from .models import BewijsItem, InconsistentieBevinding, RisicoNiveau

# ─── Constanten ───────────────────────────────────────────────────────────────

DATUM_REGEX = re.compile(r"\b(20\d{2}[-/]\d{2}[-/]\d{2})\b")

NEGATIE_WOORDEN = {"niet", "nooit", "geen", "nimmer", "ontkent", "betwist", "weigert"}

BEVESTIGING_WOORDEN = {"wel", "heeft", "is", "was", "deed", "erkent", "bevestigt", "akkoord"}


# ─── Hulpfuncties ─────────────────────────────────────────────────────────────

def _genereer_bevinding_id(type_: str, id_a: str, id_b: str) -> str:
    """Genereert een uniek ID voor een inconsistentiebevinding."""
    sleutel = f"{type_}-{id_a[:8]}-{id_b[:8]}"
    return hashlib.md5(sleutel.encode()).hexdigest()[:12]


def _extraheer_datums_iso(tekst: str) -> list[str]:
    """Extraheert ISO-datums uit tekst."""
    return DATUM_REGEX.findall(tekst)


def _heeft_negatie(zin: str) -> bool:
    """Controleert of een zin een negatie bevat."""
    woorden = set(zin.lower().split())
    return bool(woorden & NEGATIE_WOORDEN)


def _heeft_bevestiging(zin: str) -> bool:
    """Controleert of een zin een bevestiging bevat."""
    woorden = set(zin.lower().split())
    return bool(woorden & BEVESTIGING_WOORDEN)


def _gemeenschappelijke_tokens(tekst_a: str, tekst_b: str, min_lengte: int = 5) -> list[str]:
    """Vindt gemeenschappelijke betekenisvolle tokens tussen twee teksten."""
    tokens_a = set(t.lower() for t in tekst_a.split() if len(t) >= min_lengte)
    tokens_b = set(t.lower() for t in tekst_b.split() if len(t) >= min_lengte)
    return list(tokens_a & tokens_b)


# ─── Scanmodules ──────────────────────────────────────────────────────────────

def _scan_datum_conflicten(
    bewijs_items: list[BewijsItem],
) -> list[InconsistentieBevinding]:
    """
    Detecteert conflicterende datumvermeldingen voor dezelfde gebeurtenis.
    Vergelijkt datums per persoon/zaak combinatie.
    """
    bevindingen: list[InconsistentieBevinding] = []

    # Groepeer per persoon+zaak
    groepen: dict[str, list[BewijsItem]] = defaultdict(list)
    for item in bewijs_items:
        sleutel = f"{item.gedetecteerde_persoon}|{item.gedetecteerde_zaak}"
        groepen[sleutel].append(item)

    for sleutel, items in groepen.items():
        if len(items) < 2:
            continue

        # Verzamel alle datums per item
        datums_per_item: dict[str, set[str]] = {}
        for item in items:
            datums = set(_extraheer_datums_iso(item.geextraheerde_tekst))
            if datums:
                datums_per_item[item.bewijs_id] = datums

        # Vergelijk paren
        item_ids = list(datums_per_item.keys())
        for i in range(len(item_ids)):
            for j in range(i + 1, len(item_ids)):
                id_a, id_b = item_ids[i], item_ids[j]
                datums_a = datums_per_item[id_a]
                datums_b = datums_per_item[id_b]

                # Zoek overlappende datums (zelfde datum, mogelijk andere context)
                overlap = datums_a & datums_b
                alleen_a = datums_a - datums_b
                alleen_b = datums_b - datums_a

                # Als er significante datumverschillen zijn
                if alleen_a and alleen_b and len(alleen_a) + len(alleen_b) >= 3:
                    item_a = next(x for x in items if x.bewijs_id == id_a)
                    item_b = next(x for x in items if x.bewijs_id == id_b)
                    bevinding_id = _genereer_bevinding_id("datum_conflict", id_a, id_b)
                    bevindingen.append(
                        InconsistentieBevinding(
                            bevinding_id=bevinding_id,
                            type="datum_conflict",
                            beschrijving=(
                                f"Datumconflict gedetecteerd tussen '{item_a.bestandsnaam}' "
                                f"en '{item_b.bestandsnaam}'. "
                                f"Unieke datums in A: {sorted(alleen_a)[:3]}. "
                                f"Unieke datums in B: {sorted(alleen_b)[:3]}. "
                                f"Gedeelde datums: {sorted(overlap)[:3]}."
                            ),
                            bewijs_id_a=id_a,
                            bewijs_id_b=id_b,
                            ernst=RisicoNiveau.MIDDEL,
                            aanbeveling=(
                                "Controleer de chronologische volgorde van beide documenten "
                                "en verifieer welke datums correct zijn."
                            ),
                        )
                    )

    return bevindingen


def _scan_persoon_conflicten(
    bewijs_items: list[BewijsItem],
) -> list[InconsistentieBevinding]:
    """
    Detecteert conflicterende persoonsvermeldingen.
    Signaleert wanneer dezelfde persoon in tegenstrijdige rollen verschijnt.
    """
    bevindingen: list[InconsistentieBevinding] = []

    # Groepeer per zaak
    per_zaak: dict[str, list[BewijsItem]] = defaultdict(list)
    for item in bewijs_items:
        per_zaak[item.gedetecteerde_zaak].append(item)

    for zaak, items in per_zaak.items():
        if len(items) < 2:
            continue

        # Verzamel personen per item
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item_a = items[i]
                item_b = items[j]

                personen_a = set(item_a.analyse.personen_gevonden)
                personen_b = set(item_b.analyse.personen_gevonden)
                gemeenschappelijk = personen_a & personen_b

                if not gemeenschappelijk:
                    continue

                # Controleer op tegenstrijdige uitspraken over dezelfde persoon
                for persoon in gemeenschappelijk:
                    zinnen_a = [
                        z for z in item_a.geextraheerde_tekst.splitlines()
                        if persoon.lower() in z.lower() and len(z.strip()) > 20
                    ]
                    zinnen_b = [
                        z for z in item_b.geextraheerde_tekst.splitlines()
                        if persoon.lower() in z.lower() and len(z.strip()) > 20
                    ]

                    # Zoek tegenstrijdige uitspraken
                    for zin_a in zinnen_a[:5]:
                        for zin_b in zinnen_b[:5]:
                            heeft_neg_a = _heeft_negatie(zin_a)
                            heeft_neg_b = _heeft_negatie(zin_b)
                            gemeenschappelijke_tok = _gemeenschappelijke_tokens(zin_a, zin_b)

                            if (
                                len(gemeenschappelijke_tok) >= 3
                                and heeft_neg_a != heeft_neg_b
                            ):
                                bevinding_id = _genereer_bevinding_id(
                                    "persoon_conflict", item_a.bewijs_id, item_b.bewijs_id
                                )
                                bevindingen.append(
                                    InconsistentieBevinding(
                                        bevinding_id=bevinding_id,
                                        type="persoon_conflict",
                                        beschrijving=(
                                            f"Tegenstrijdige uitspraken over '{persoon}' "
                                            f"in '{item_a.bestandsnaam}' vs '{item_b.bestandsnaam}'. "
                                            f"Uitspraak A: '{zin_a.strip()[:120]}'. "
                                            f"Uitspraak B: '{zin_b.strip()[:120]}'."
                                        ),
                                        bewijs_id_a=item_a.bewijs_id,
                                        bewijs_id_b=item_b.bewijs_id,
                                        ernst=RisicoNiveau.HOOG,
                                        aanbeveling=(
                                            f"Verifieer de uitspraken over '{persoon}' "
                                            "door aanvullende bronnen te raadplegen."
                                        ),
                                    )
                                )
                                break  # Één bevinding per paar is voldoende

    return bevindingen


def _scan_feit_tegenspraken(
    bewijs_items: list[BewijsItem],
) -> list[InconsistentieBevinding]:
    """
    Detecteert feitelijke tegenspraken binnen en tussen documenten.
    Vergelijkt feiten en aannames op tegenstrijdige inhoud.
    """
    bevindingen: list[InconsistentieBevinding] = []

    for i in range(len(bewijs_items)):
        for j in range(i + 1, len(bewijs_items)):
            item_a = bewijs_items[i]
            item_b = bewijs_items[j]

            # Vergelijk feiten van A met aannames van B en vice versa
            paren = [
                (item_a.analyse.feiten, item_b.analyse.aannames, item_a, item_b),
                (item_b.analyse.feiten, item_a.analyse.aannames, item_b, item_a),
            ]

            for feiten, aannames, bron_feit, bron_aanname in paren:
                for aanname in aannames[:10]:
                    al = aanname.lower()
                    for feit in feiten[:20]:
                        fl = feit.lower()
                        gemeenschappelijk = _gemeenschappelijke_tokens(al, fl)
                        if len(gemeenschappelijk) < 3:
                            continue
                        # Tegenspraak: negatie in één maar niet in andere
                        if _heeft_negatie(aanname) != _heeft_negatie(feit):
                            bevinding_id = _genereer_bevinding_id(
                                "feit_tegenspraak",
                                bron_feit.bewijs_id,
                                bron_aanname.bewijs_id,
                            )
                            bevindingen.append(
                                InconsistentieBevinding(
                                    bevinding_id=bevinding_id,
                                    type="feit_tegenspraak",
                                    beschrijving=(
                                        f"Feitelijke tegenspraak tussen "
                                        f"'{bron_feit.bestandsnaam}' en "
                                        f"'{bron_aanname.bestandsnaam}'. "
                                        f"Feit: '{feit[:120]}'. "
                                        f"Aanname: '{aanname[:120]}'."
                                    ),
                                    bewijs_id_a=bron_feit.bewijs_id,
                                    bewijs_id_b=bron_aanname.bewijs_id,
                                    ernst=RisicoNiveau.MIDDEL,
                                    aanbeveling=(
                                        "Verifieer welke stelling correct is "
                                        "door aanvullend bewijs te verzamelen."
                                    ),
                                )
                            )
                            break

    # Verwijder duplicaten op basis van bevinding_id
    gezien: set[str] = set()
    uniek: list[InconsistentieBevinding] = []
    for b in bevindingen:
        if b.bevinding_id not in gezien:
            uniek.append(b)
            gezien.add(b.bevinding_id)

    return uniek


def _scan_hash_duplicaten(
    bewijs_items: list[BewijsItem],
) -> list[InconsistentieBevinding]:
    """
    Detecteert identieke bestanden (zelfde hash) op verschillende locaties.
    Dit kan wijzen op kopiëren of manipulatie.
    """
    bevindingen: list[InconsistentieBevinding] = []
    hash_naar_items: dict[str, list[BewijsItem]] = defaultdict(list)

    for item in bewijs_items:
        hash_naar_items[item.inhoud_hash].append(item)

    for hash_waarde, items in hash_naar_items.items():
        if len(items) < 2:
            continue
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item_a, item_b = items[i], items[j]
                if item_a.bestand_pad != item_b.bestand_pad:
                    bevinding_id = _genereer_bevinding_id(
                        "duplicaat", item_a.bewijs_id, item_b.bewijs_id
                    )
                    bevindingen.append(
                        InconsistentieBevinding(
                            bevinding_id=bevinding_id,
                            type="duplicaat_bestand",
                            beschrijving=(
                                f"Identieke bestanden gedetecteerd: "
                                f"'{item_a.bestandsnaam}' en '{item_b.bestandsnaam}' "
                                f"hebben dezelfde SHA-256 hash ({hash_waarde[:16]}…). "
                                f"Locatie A: {item_a.bron_map}. "
                                f"Locatie B: {item_b.bron_map}."
                            ),
                            bewijs_id_a=item_a.bewijs_id,
                            bewijs_id_b=item_b.bewijs_id,
                            ernst=RisicoNiveau.LAAG,
                            aanbeveling=(
                                "Controleer of het duplicaat intentioneel is "
                                "of het gevolg van ongeautoriseerd kopiëren."
                            ),
                        )
                    )

    return bevindingen


# ─── Hoofdscanner ─────────────────────────────────────────────────────────────

def voer_consistency_scan_uit(
    bewijs_items: list[BewijsItem],
) -> list[InconsistentieBevinding]:
    """
    Voert een volledige consistency scan uit op alle bewijsstukken.
    
    Scant op:
    - Datumconflicten
    - Persoonconflicten
    - Feitelijke tegenspraken
    - Duplicaatbestanden
    
    Elke bevinding is herleidbaar naar de bronbewijsstukken.
    """
    alle_bevindingen: list[InconsistentieBevinding] = []

    alle_bevindingen.extend(_scan_datum_conflicten(bewijs_items))
    alle_bevindingen.extend(_scan_persoon_conflicten(bewijs_items))
    alle_bevindingen.extend(_scan_feit_tegenspraken(bewijs_items))
    alle_bevindingen.extend(_scan_hash_duplicaten(bewijs_items))

    # Sorteer op ernst (kritiek eerst)
    ernst_volgorde = {
        RisicoNiveau.KRITIEK: 0,
        RisicoNiveau.HOOG: 1,
        RisicoNiveau.MIDDEL: 2,
        RisicoNiveau.LAAG: 3,
        RisicoNiveau.GEEN: 4,
    }
    alle_bevindingen.sort(key=lambda b: ernst_volgorde.get(b.ernst, 5))

    return alle_bevindingen

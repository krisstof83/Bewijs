"""
FORENSIC_DOSSIER_ENGINE — Bestandsimporter
Leest en verwerkt alle bestanden uit dossier/data, dossier/evidence, dossier/timeline.
Elke conclusie is herleidbaar naar brondata.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .models import (
    BestandsMetadata,
    BewijsGewicht,
    BewijsItem,
    DocumentAnalyse,
)

# ─── Constanten ───────────────────────────────────────────────────────────────

ONDERSTEUNDE_EXTENSIES = {".pdf", ".txt", ".json", ".html", ".eml", ".csv", ".md"}

DATUM_REGEX = re.compile(
    r"\b(20\d{2}[-/]\d{2}[-/]\d{2}|"          # 2024-01-15 of 2024/01/15
    r"\d{2}[-/]\d{2}[-/]20\d{2}|"              # 15-01-2024 of 15/01/2024
    r"\d{1,2}\s+(?:januari|februari|maart|april|mei|juni|"
    r"juli|augustus|september|oktober|november|december)\s+20\d{2})\b",
    re.IGNORECASE,
)

PERSOON_PATRONEN = [
    r"\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b",  # Voornaam Achternaam
]

JURIDISCHE_TERMEN = [
    "contract", "bewijs", "zaak", "advocaat", "rechtbank", "procedure",
    "klacht", "vonnis", "uitspraak", "dagvaarding", "verweer", "eis",
    "gedaagde", "eiser", "rechter", "hoger beroep", "cassatie",
    "bewijslast", "aanklacht", "verzoekschrift", "beschikking",
    "executie", "beslaglegging", "faillissement", "curator",
]

AANNAME_MARKERS = [
    "ik denk", "vermoed", "misschien", "waarschijnlijk", "volgens mij",
    "zou kunnen", "lijkt erop", "vermoedelijk", "mogelijk", "wellicht",
    "naar mijn mening", "ik geloof", "het schijnt",
]

FEIT_MARKERS = [
    "op datum", "is vastgesteld", "blijkt uit", "conform", "overeenkomstig",
    "bewezen", "aangetoond", "gedocumenteerd", "ondertekend", "geregistreerd",
]


# ─── Hulpfuncties ─────────────────────────────────────────────────────────────

def _bereken_hash(bestand: Path) -> str:
    """Berekent SHA-256 hash van een bestand."""
    digest = hashlib.sha256()
    with bestand.open("rb") as f:
        while chunk := f.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _lees_tekst(bestand: Path) -> str:
    """Leest tekstinhoud van een bestand, inclusief PDF-ondersteuning."""
    ext = bestand.suffix.lower()
    if ext in {".txt", ".json", ".html", ".eml", ".csv", ".md"}:
        return bestand.read_text(encoding="utf-8", errors="replace")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
            reader = PdfReader(str(bestand))
            return "\n".join(
                (page.extract_text() or "") for page in reader.pages
            )
        except ImportError:
            pass
        except Exception as exc:
            return f"[PDF-leesfout: {exc}]"
    # Fallback: binaire bytes als tekst
    return bestand.read_bytes()[:20000].decode("utf-8", errors="replace")


def _extraheer_datums(tekst: str) -> list[str]:
    """Extraheert alle datumvermeldingen uit tekst."""
    gevonden = DATUM_REGEX.findall(tekst)
    uniek = list(dict.fromkeys(gevonden))  # volgorde behouden, duplicaten weg
    return uniek[:30]


def _extraheer_personen(tekst: str) -> list[str]:
    """Extraheert mogelijke persoonsnamen uit tekst (heuristisch)."""
    kandidaten: list[str] = []
    for patroon in PERSOON_PATRONEN:
        matches = re.findall(patroon, tekst)
        kandidaten.extend(matches)
    # Filter korte/generieke namen
    gefilterd = [
        naam for naam in kandidaten
        if len(naam) > 5
        and not any(
            woord in naam.lower()
            for woord in ["de heer", "mevrouw", "datum", "pagina", "bijlage"]
        )
    ]
    uniek = list(dict.fromkeys(gefilterd))
    return uniek[:20]


def _extraheer_juridische_termen(tekst: str) -> list[str]:
    """Detecteert juridische termen in tekst."""
    tekst_lower = tekst.lower()
    return [term for term in JURIDISCHE_TERMEN if term in tekst_lower]


def _splits_feiten_aannames(tekst: str) -> tuple[list[str], list[str]]:
    """Splitst tekstregels in feiten en aannames."""
    feiten: list[str] = []
    aannames: list[str] = []
    for regel in tekst.splitlines():
        schoon = regel.strip()
        if len(schoon) < 15:
            continue
        laag = schoon.lower()
        if any(marker in laag for marker in AANNAME_MARKERS):
            aannames.append(schoon)
        elif any(marker in laag for marker in FEIT_MARKERS):
            feiten.append(f"[FEIT] {schoon}")
        else:
            feiten.append(schoon)
    return feiten[:60], aannames[:40]


def _detecteer_inconsistenties_lokaal(
    feiten: list[str], aannames: list[str]
) -> list[str]:
    """Detecteert mogelijke tegenspraken binnen één document."""
    bevindingen: list[str] = []
    for aanname in aannames:
        al = aanname.lower()
        for feit in feiten:
            fl = feit.lower()
            # Zoek overlappende sleutelwoorden maar tegengestelde stelling
            tokens_aanname = [t for t in al.split() if len(t) > 4]
            overlap = [t for t in tokens_aanname if t in fl]
            if len(overlap) >= 2:
                if ("niet" in al) != ("niet" in fl):
                    bevindingen.append(
                        f"Mogelijke tegenspraak: "
                        f"Aanname: '{aanname[:100]}' ↔ Feit: '{feit[:100]}'"
                    )
                    break
    return bevindingen[:20]


def _bepaal_juridische_relevantie(tekst: str) -> str:
    """Bepaalt juridische relevantie op basis van trefwoorden."""
    score = sum(1 for term in JURIDISCHE_TERMEN if term in tekst.lower())
    if score >= 4:
        return "Hoog"
    if score >= 2:
        return "Middel"
    return "Laag"


def _bepaal_bewijsgewicht(tekst: str, datums: list[str]) -> BewijsGewicht:
    """Bepaalt bewijsgewicht op basis van lengte, datums en juridische inhoud."""
    lengte_score = min(len(tekst) // 1000, 3)
    datum_score = min(len(datums), 2)
    juridisch_score = min(
        sum(1 for term in JURIDISCHE_TERMEN if term in tekst.lower()), 3
    )
    totaal = lengte_score + datum_score + juridisch_score
    if totaal >= 6:
        return BewijsGewicht.HOOG
    if totaal >= 3:
        return BewijsGewicht.MIDDEL
    return BewijsGewicht.LAAG


def _detecteer_persoon(tekst: str, personen: list[str]) -> str:
    """Detecteert de meest prominente persoon in de tekst."""
    # Bekende namen uit het dossier
    bekende_namen = [
        "Kristof Huibers", "Anneke Coenen", "Yolanda Dello",
        "Yolanda Anne", "Kristof",
    ]
    for naam in bekende_namen:
        if naam.lower() in tekst.lower():
            return naam
    if personen:
        return personen[0]
    return "Onbekend"


def _detecteer_zaak(bestand: Path, tekst: str) -> str:
    """Detecteert de zaakidentificatie."""
    zaak_patroon = re.search(
        r"\b(zaak[-\s]?\w+|dossier[-\s]?\w+|procedure[-\s]?\w+)\b",
        tekst,
        re.IGNORECASE,
    )
    if zaak_patroon:
        return zaak_patroon.group(0).replace(" ", "_").lower()
    if "zaak" in tekst.lower():
        return "algemene_zaak"
    return f"{bestand.parent.name}_{bestand.stem}".replace(" ", "_")[:50]


def _map_categorie(bestand: Path, dossier_root: Path) -> str:
    """Bepaalt de mapcategorie (data/evidence/timeline)."""
    try:
        relatief = bestand.relative_to(dossier_root)
        return relatief.parts[0] if relatief.parts else "onbekend"
    except ValueError:
        return "onbekend"


# ─── Hoofdimporter ────────────────────────────────────────────────────────────

def importeer_bestanden(dossier_root: Path) -> list[BewijsItem]:
    """
    Importeert alle bestanden uit dossier/data, dossier/evidence, dossier/timeline.
    Retourneert een lijst van BewijsItem objecten.
    Elke conclusie is herleidbaar naar het bronbestand.
    """
    mappen = [
        dossier_root / "data",
        dossier_root / "evidence",
        dossier_root / "timeline",
    ]

    bewijs_items: list[BewijsItem] = []
    verwerkt_hashes: set[str] = set()

    for map_pad in mappen:
        map_pad.mkdir(parents=True, exist_ok=True)
        for bestand in _itereer_bestanden(map_pad):
            sha256 = _bereken_hash(bestand)
            if sha256 in verwerkt_hashes:
                continue  # Duplicaat overslaan
            verwerkt_hashes.add(sha256)

            tekst = _lees_tekst(bestand)
            datums = _extraheer_datums(tekst)
            personen = _extraheer_personen(tekst)
            juridische_termen = _extraheer_juridische_termen(tekst)
            feiten, aannames = _splits_feiten_aannames(tekst)
            inconsistenties = _detecteer_inconsistenties_lokaal(feiten, aannames)

            analyse = DocumentAnalyse(
                feiten=feiten,
                aannames=aannames,
                inconsistenties=inconsistenties,
                datums_gevonden=datums,
                personen_gevonden=personen,
                juridische_termen=juridische_termen,
            )

            geimporteerd_op = datetime.utcnow().isoformat()
            bewijs_id = hashlib.md5(
                f"{bestand.resolve()}-{sha256}".encode("utf-8")
            ).hexdigest()

            categorie = _map_categorie(bestand, dossier_root)
            gedetecteerde_persoon = _detecteer_persoon(tekst, personen)
            gedetecteerde_zaak = _detecteer_zaak(bestand, tekst)
            juridische_relevantie = _bepaal_juridische_relevantie(tekst)
            bewijsgewicht = _bepaal_bewijsgewicht(tekst, datums)

            metadata = BestandsMetadata(
                pad=str(bestand.resolve()),
                bestandsnaam=bestand.name,
                extensie=bestand.suffix.lower(),
                grootte_bytes=bestand.stat().st_size,
                sha256_hash=sha256,
                geimporteerd_op=geimporteerd_op,
                map_categorie=categorie,
            )

            item = BewijsItem(
                bewijs_id=bewijs_id,
                bron_map=categorie,
                bestand_pad=str(bestand.resolve()),
                bestandsnaam=bestand.name,
                gedetecteerde_persoon=gedetecteerde_persoon,
                gedetecteerde_zaak=gedetecteerde_zaak,
                geimporteerd_op=geimporteerd_op,
                inhoud_hash=sha256,
                geextraheerde_tekst=tekst[:12000],
                juridische_relevantie=juridische_relevantie,
                bewijsgewicht=bewijsgewicht,
                bewijs_keten=[
                    f"{geimporteerd_op} — Geïmporteerd: {bestand.name} "
                    f"(SHA-256: {sha256[:16]}…)"
                ],
                analyse=analyse,
                metadata=metadata,
            )
            bewijs_items.append(item)

    return bewijs_items


def _itereer_bestanden(map_pad: Path) -> Iterator[Path]:
    """Itereert recursief over alle ondersteunde bestanden in een map."""
    for bestand in sorted(map_pad.rglob("*")):
        if bestand.is_file() and bestand.suffix.lower() in ONDERSTEUNDE_EXTENSIES:
            yield bestand

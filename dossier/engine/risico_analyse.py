"""
FORENSIC_DOSSIER_ENGINE — Risico-analyse
Identificeert juridische, procedurele en bewijstechnische risico's.
Elke risicobeoordeling is herleidbaar naar brondata.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from datetime import datetime

from .models import (
    BewijsGewicht,
    BewijsItem,
    InconsistentieBevinding,
    RisicoItem,
    RisicoNiveau,
    TijdlijnGebeurtenis,
)

# ─── Constanten ───────────────────────────────────────────────────────────────

VERJARINGS_DREMPEL_JAREN = 5  # Standaard verjaringstermijn (civiel)

KRITIEKE_JURIDISCHE_TERMEN = [
    "dagvaarding", "vonnis", "uitspraak", "hoger beroep", "cassatie",
    "executie", "beslaglegging", "faillissement",
]

PROCEDURELE_RISICO_TERMEN = [
    "termijn", "deadline", "uiterlijk", "vóór", "binnen", "vervaltermijn",
    "bezwaartermijn", "beroepstermijn",
]

BEWIJSTECHNISCHE_RISICO_TERMEN = [
    "origineel", "kopie", "afschrift", "gewaarmerkt", "notarieel",
    "handtekening", "paraaf", "stempel",
]


# ─── Hulpfuncties ─────────────────────────────────────────────────────────────

def _genereer_risico_id(categorie: str, omschrijving: str) -> str:
    """Genereert een uniek risico-ID."""
    sleutel = f"{categorie}-{omschrijving[:50]}"
    return hashlib.md5(sleutel.encode()).hexdigest()[:12]


def _als_jaar(tijdstip: str) -> int:
    """Extraheert het jaar uit een tijdstip-string."""
    try:
        return datetime.fromisoformat(tijdstip.replace("Z", "+00:00")).year
    except Exception:
        return 0


# ─── Risicomodules ────────────────────────────────────────────────────────────

def _analyseer_juridische_risicos(
    bewijs_items: list[BewijsItem],
) -> list[RisicoItem]:
    """
    Analyseert juridische risico's op basis van bewijsinhoud.
    Detecteert: ontbrekende kritieke documenten, lage bewijsgewichten,
    ontbrekende juridische termen.
    """
    risicos: list[RisicoItem] = []

    # Controleer op kritieke juridische termen
    aanwezige_termen: set[str] = set()
    for item in bewijs_items:
        tekst_lower = item.geextraheerde_tekst.lower()
        for term in KRITIEKE_JURIDISCHE_TERMEN:
            if term in tekst_lower:
                aanwezige_termen.add(term)

    ontbrekende_termen = set(KRITIEKE_JURIDISCHE_TERMEN) - aanwezige_termen
    if ontbrekende_termen:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("juridisch", "ontbrekende_termen"),
                categorie="juridisch",
                omschrijving=(
                    f"Kritieke juridische documenten mogelijk ontbrekend. "
                    f"Niet gevonden termen: {', '.join(sorted(ontbrekende_termen))}."
                ),
                niveau=RisicoNiveau.MIDDEL,
                betrokken_bewijs_ids=[],
                mitigatie_advies=(
                    "Controleer of alle relevante juridische documenten "
                    "(dagvaarding, vonnis, etc.) aanwezig zijn in het dossier."
                ),
            )
        )

    # Controleer bewijsgewichten
    laag_gewicht_items = [
        item for item in bewijs_items
        if item.bewijsgewicht == BewijsGewicht.LAAG
    ]
    if len(laag_gewicht_items) > len(bewijs_items) * 0.5 and bewijs_items:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("juridisch", "laag_bewijsgewicht"),
                categorie="juridisch",
                omschrijving=(
                    f"{len(laag_gewicht_items)} van {len(bewijs_items)} bewijsstukken "
                    f"hebben een laag bewijsgewicht. "
                    f"Dit verzwakt de juridische positie."
                ),
                niveau=RisicoNiveau.HOOG,
                betrokken_bewijs_ids=[item.bewijs_id for item in laag_gewicht_items],
                mitigatie_advies=(
                    "Verzamel aanvullend bewijs met hogere juridische waarde: "
                    "officiële documenten, notariële akten, rechterlijke uitspraken."
                ),
            )
        )

    # Controleer op hoog-relevante items
    hoog_relevante = [
        item for item in bewijs_items
        if item.juridische_relevantie == "Hoog"
    ]
    if not hoog_relevante and bewijs_items:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("juridisch", "geen_hoog_relevante"),
                categorie="juridisch",
                omschrijving=(
                    "Geen enkel bewijsstuk heeft een hoge juridische relevantie. "
                    "Het dossier mist mogelijk kernbewijzen."
                ),
                niveau=RisicoNiveau.KRITIEK,
                betrokken_bewijs_ids=[],
                mitigatie_advies=(
                    "Identificeer en voeg kernbewijzen toe: contracten, "
                    "officiële correspondentie, rechterlijke beslissingen."
                ),
            )
        )

    return risicos


def _analyseer_procedurele_risicos(
    bewijs_items: list[BewijsItem],
    tijdlijn: list[TijdlijnGebeurtenis],
) -> list[RisicoItem]:
    """
    Analyseert procedurele risico's: termijnen, verjaring, ontbrekende stappen.
    """
    risicos: list[RisicoItem] = []
    huidig_jaar = datetime.utcnow().year

    # Controleer op termijnvermeldingen
    termijn_items: list[BewijsItem] = []
    for item in bewijs_items:
        tekst_lower = item.geextraheerde_tekst.lower()
        if any(term in tekst_lower for term in PROCEDURELE_RISICO_TERMEN):
            termijn_items.append(item)

    if termijn_items:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("procedureel", "termijn_vermeldingen"),
                categorie="procedureel",
                omschrijving=(
                    f"{len(termijn_items)} bewijsstuk(ken) bevatten termijnvermeldingen. "
                    f"Controleer of alle termijnen zijn nageleefd."
                ),
                niveau=RisicoNiveau.HOOG,
                betrokken_bewijs_ids=[item.bewijs_id for item in termijn_items],
                mitigatie_advies=(
                    "Maak een overzicht van alle genoemde termijnen en "
                    "verifieer of deze zijn nageleefd. Raadpleeg een advocaat."
                ),
            )
        )

    # Controleer op verjaringsrisico
    if tijdlijn:
        vroegste_jaar = min(
            (_als_jaar(g.tijdstip) for g in tijdlijn if _als_jaar(g.tijdstip) > 2000),
            default=0,
        )
        if vroegste_jaar > 0:
            jaren_verstreken = huidig_jaar - vroegste_jaar
            if jaren_verstreken >= VERJARINGS_DREMPEL_JAREN:
                risicos.append(
                    RisicoItem(
                        risico_id=_genereer_risico_id("procedureel", "verjaring"),
                        categorie="procedureel",
                        omschrijving=(
                            f"Verjaringsrisico: de vroegste tijdlijngebeurtenis dateert "
                            f"uit {vroegste_jaar} ({jaren_verstreken} jaar geleden). "
                            f"Standaard civiele verjaringstermijn is {VERJARINGS_DREMPEL_JAREN} jaar."
                        ),
                        niveau=RisicoNiveau.KRITIEK,
                        betrokken_bewijs_ids=[],
                        mitigatie_advies=(
                            "Raadpleeg onmiddellijk een advocaat over de toepasselijke "
                            "verjaringstermijnen en mogelijke stuiting of verlenging."
                        ),
                    )
                )

    # Controleer op lege mappen
    mappen_met_data = set(item.bron_map for item in bewijs_items)
    verwachte_mappen = {"data", "evidence", "timeline"}
    lege_mappen = verwachte_mappen - mappen_met_data
    if lege_mappen:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("procedureel", "lege_mappen"),
                categorie="procedureel",
                omschrijving=(
                    f"Lege dossiermappen gedetecteerd: {', '.join(sorted(lege_mappen))}. "
                    f"Mogelijk ontbreken er bewijsstukken."
                ),
                niveau=RisicoNiveau.MIDDEL,
                betrokken_bewijs_ids=[],
                mitigatie_advies=(
                    f"Voeg relevante bestanden toe aan de lege mappen: "
                    f"{', '.join(sorted(lege_mappen))}."
                ),
            )
        )

    return risicos


def _analyseer_bewijstechnische_risicos(
    bewijs_items: list[BewijsItem],
    inconsistenties: list[InconsistentieBevinding],
) -> list[RisicoItem]:
    """
    Analyseert bewijstechnische risico's: authenticiteit, volledigheid,
    keten van bewaring, inconsistenties.
    """
    risicos: list[RisicoItem] = []

    # Risico op basis van inconsistenties
    hoge_ernst_inconsistenties = [
        b for b in inconsistenties
        if b.ernst in (RisicoNiveau.KRITIEK, RisicoNiveau.HOOG)
    ]
    if hoge_ernst_inconsistenties:
        betrokken_ids = list(set(
            id_
            for b in hoge_ernst_inconsistenties
            for id_ in [b.bewijs_id_a, b.bewijs_id_b]
        ))
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("bewijstechnisch", "hoge_inconsistenties"),
                categorie="bewijstechnisch",
                omschrijving=(
                    f"{len(hoge_ernst_inconsistenties)} hoge/kritieke inconsistenties "
                    f"gedetecteerd in het dossier. "
                    f"Dit ondermijnt de bewijskracht."
                ),
                niveau=RisicoNiveau.HOOG,
                betrokken_bewijs_ids=betrokken_ids[:10],
                mitigatie_advies=(
                    "Los de gedetecteerde inconsistenties op door aanvullend "
                    "bewijs te verzamelen of de tegenstrijdige documenten te verklaren."
                ),
            )
        )

    # Controleer bewijs-keten volledigheid
    items_zonder_keten = [
        item for item in bewijs_items
        if not item.bewijs_keten
    ]
    if items_zonder_keten:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("bewijstechnisch", "ontbrekende_keten"),
                categorie="bewijstechnisch",
                omschrijving=(
                    f"{len(items_zonder_keten)} bewijsstuk(ken) missen een "
                    f"bewijs-keten (chain of custody). "
                    f"Dit kan de juridische bruikbaarheid beperken."
                ),
                niveau=RisicoNiveau.MIDDEL,
                betrokken_bewijs_ids=[item.bewijs_id for item in items_zonder_keten],
                mitigatie_advies=(
                    "Documenteer de herkomst en bewaargeschiedenis van elk bewijsstuk."
                ),
            )
        )

    # Controleer op authenticiteitsmarkers
    authenticiteits_items: list[BewijsItem] = []
    for item in bewijs_items:
        tekst_lower = item.geextraheerde_tekst.lower()
        if any(term in tekst_lower for term in BEWIJSTECHNISCHE_RISICO_TERMEN):
            authenticiteits_items.append(item)

    if authenticiteits_items:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("bewijstechnisch", "authenticiteit"),
                categorie="bewijstechnisch",
                omschrijving=(
                    f"{len(authenticiteits_items)} bewijsstuk(ken) bevatten "
                    f"verwijzingen naar authenticiteitsmarkers "
                    f"(origineel, kopie, handtekening, etc.). "
                    f"Verifieer de authenticiteit."
                ),
                niveau=RisicoNiveau.MIDDEL,
                betrokken_bewijs_ids=[item.bewijs_id for item in authenticiteits_items],
                mitigatie_advies=(
                    "Laat de authenticiteit van kritieke documenten verifiëren "
                    "door een deskundige of notaris."
                ),
            )
        )

    return risicos


def _analyseer_temporele_risicos(
    tijdlijn: list[TijdlijnGebeurtenis],
    temporele_gaten: list[dict],
) -> list[RisicoItem]:
    """
    Analyseert temporele risico's: tijdsgaten, chronologische inconsistenties.
    """
    risicos: list[RisicoItem] = []

    # Grote tijdsgaten
    grote_gaten = [g for g in temporele_gaten if g["duur_dagen"] > 180]
    if grote_gaten:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("temporeel", "grote_tijdsgaten"),
                categorie="temporeel",
                omschrijving=(
                    f"{len(grote_gaten)} grote tijdsgat(en) gedetecteerd "
                    f"(> 180 dagen). "
                    f"Grootste gat: {max(g['duur_dagen'] for g in grote_gaten)} dagen. "
                    f"Periodes: {', '.join(g['van'] + ' → ' + g['tot'] for g in grote_gaten[:3])}."
                ),
                niveau=RisicoNiveau.MIDDEL,
                betrokken_bewijs_ids=[],
                mitigatie_advies=(
                    "Verklaar de tijdsgaten of verzamel aanvullend bewijs "
                    "voor de ontbrekende periodes."
                ),
            )
        )

    # Controleer op toekomstige datums (mogelijke fout)
    huidig_jaar = datetime.utcnow().year
    toekomstige_gebeurtenissen = [
        g for g in tijdlijn
        if _als_jaar(g.tijdstip) > huidig_jaar
    ]
    if toekomstige_gebeurtenissen:
        risicos.append(
            RisicoItem(
                risico_id=_genereer_risico_id("temporeel", "toekomstige_datums"),
                categorie="temporeel",
                omschrijving=(
                    f"{len(toekomstige_gebeurtenissen)} tijdlijngebeurtenis(sen) "
                    f"hebben een datum in de toekomst. "
                    f"Dit kan wijzen op invoerfouten of gemanipuleerde documenten."
                ),
                niveau=RisicoNiveau.HOOG,
                betrokken_bewijs_ids=[
                    g.gerelateerde_bewijs_ids[0]
                    for g in toekomstige_gebeurtenissen
                    if g.gerelateerde_bewijs_ids
                ],
                mitigatie_advies=(
                    "Controleer de datums van de betreffende documenten op correctheid."
                ),
            )
        )

    return risicos


# ─── Hoofdanalyse ─────────────────────────────────────────────────────────────

def voer_risico_analyse_uit(
    bewijs_items: list[BewijsItem],
    tijdlijn: list[TijdlijnGebeurtenis],
    inconsistenties: list[InconsistentieBevinding],
    temporele_gaten: list[dict],
) -> list[RisicoItem]:
    """
    Voert een volledige risico-analyse uit op het dossier.
    
    Analyseert:
    - Juridische risico's (bewijsgewicht, relevantie, ontbrekende documenten)
    - Procedurele risico's (termijnen, verjaring, lege mappen)
    - Bewijstechnische risico's (authenticiteit, keten, inconsistenties)
    - Temporele risico's (tijdsgaten, toekomstige datums)
    
    Elke risicobeoordeling is herleidbaar naar brondata.
    """
    alle_risicos: list[RisicoItem] = []

    alle_risicos.extend(_analyseer_juridische_risicos(bewijs_items))
    alle_risicos.extend(_analyseer_procedurele_risicos(bewijs_items, tijdlijn))
    alle_risicos.extend(
        _analyseer_bewijstechnische_risicos(bewijs_items, inconsistenties)
    )
    alle_risicos.extend(_analyseer_temporele_risicos(tijdlijn, temporele_gaten))

    # Sorteer op ernst (kritiek eerst)
    ernst_volgorde = {
        RisicoNiveau.KRITIEK: 0,
        RisicoNiveau.HOOG: 1,
        RisicoNiveau.MIDDEL: 2,
        RisicoNiveau.LAAG: 3,
        RisicoNiveau.GEEN: 4,
    }
    alle_risicos.sort(key=lambda r: ernst_volgorde.get(r.niveau, 5))

    return alle_risicos

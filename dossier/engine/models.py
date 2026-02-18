"""
FORENSIC_DOSSIER_ENGINE — Datamodellen
Alle datastructuren voor forensische dossieranalyse.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class BewijsGewicht(str, Enum):
    HOOG = "hoog"
    MIDDEL = "middel"
    LAAG = "laag"
    ONBEKEND = "onbekend"


class RisicoNiveau(str, Enum):
    KRITIEK = "kritiek"
    HOOG = "hoog"
    MIDDEL = "middel"
    LAAG = "laag"
    GEEN = "geen"


class VertrouwensNiveau(str, Enum):
    HOOG = "hoog"
    MIDDEL = "middel"
    LAAG = "laag"


@dataclass
class BestandsMetadata:
    """Metadata van een geanalyseerd bestand."""
    pad: str
    bestandsnaam: str
    extensie: str
    grootte_bytes: int
    sha256_hash: str
    geimporteerd_op: str
    map_categorie: str  # data / evidence / timeline


@dataclass
class DocumentAnalyse:
    """Resultaat van tekstanalyse op een document."""
    feiten: list[str] = field(default_factory=list)
    aannames: list[str] = field(default_factory=list)
    inconsistenties: list[str] = field(default_factory=list)
    datums_gevonden: list[str] = field(default_factory=list)
    personen_gevonden: list[str] = field(default_factory=list)
    juridische_termen: list[str] = field(default_factory=list)


@dataclass
class BewijsItem:
    """Eén bewijsstuk in het dossier."""
    bewijs_id: str
    bron_map: str                    # data / evidence / timeline
    bestand_pad: str
    bestandsnaam: str
    gedetecteerde_persoon: str
    gedetecteerde_zaak: str
    geimporteerd_op: str
    inhoud_hash: str
    geextraheerde_tekst: str
    juridische_relevantie: str       # Hoog / Middel / Laag
    bewijsgewicht: BewijsGewicht
    bewijs_keten: list[str] = field(default_factory=list)
    analyse: DocumentAnalyse = field(default_factory=DocumentAnalyse)
    metadata: BestandsMetadata | None = None


@dataclass
class TijdlijnGebeurtenis:
    """Eén gebeurtenis op de tijdlijn."""
    gebeurtenis_id: str
    tijdstip: str                    # ISO 8601
    titel: str
    beschrijving: str
    gerelateerde_bewijs_ids: list[str] = field(default_factory=list)
    vertrouwen: VertrouwensNiveau = VertrouwensNiveau.MIDDEL
    bron_bestand: str = ""


@dataclass
class InconsistentieBevinding:
    """Gedetecteerde inconsistentie tussen bewijsstukken."""
    bevinding_id: str
    type: str                        # datum_conflict / persoon_conflict / feit_tegenspraak
    beschrijving: str
    bewijs_id_a: str
    bewijs_id_b: str
    ernst: RisicoNiveau
    aanbeveling: str


@dataclass
class RisicoItem:
    """Geïdentificeerd risico in het dossier."""
    risico_id: str
    categorie: str                   # juridisch / procedureel / bewijstechnisch / temporeel
    omschrijving: str
    niveau: RisicoNiveau
    betrokken_bewijs_ids: list[str] = field(default_factory=list)
    mitigatie_advies: str = ""


@dataclass
class MapBewijsStructuur:
    """Bewijsstructuur per map."""
    map_naam: str
    map_pad: str
    aantal_bestanden: int
    bewijs_items: list[BewijsItem] = field(default_factory=list)
    samenvatting: str = ""
    dominante_persoon: str = ""
    dominante_zaak: str = ""
    tijdspanne_van: str = ""
    tijdspanne_tot: str = ""


@dataclass
class DossierRapport:
    """Volledig forensisch dossierrapport."""
    rapport_id: str
    gegenereerd_op: str
    dossier_pad: str
    totaal_bestanden: int
    totaal_bewijs_items: int
    totaal_tijdlijn_gebeurtenissen: int
    totaal_inconsistenties: int
    totaal_risicos: int
    bewijs_items: list[BewijsItem] = field(default_factory=list)
    tijdlijn: list[TijdlijnGebeurtenis] = field(default_factory=list)
    inconsistenties: list[InconsistentieBevinding] = field(default_factory=list)
    risicos: list[RisicoItem] = field(default_factory=list)
    map_structuren: list[MapBewijsStructuur] = field(default_factory=list)
    samenvatting: str = ""
    conclusies: list[str] = field(default_factory=list)
    aanbevelingen: list[str] = field(default_factory=list)

"""
FORENSIC_DOSSIER_ENGINE — CLI Entry Point
Commandoregelinterface voor de forensische dossieranalyse-engine.

Gebruik:
    python -m dossier.engine.cli [opties]
    python dossier/engine/cli.py [opties]

Opties:
    --dossier PATH    Pad naar de dossiermap (standaard: ./dossier)
    --uitvoer PATH    Pad naar de uitvoermap (standaard: ./dossier/output)
    --alleen-tijdlijn Exporteer alleen de tijdlijn
    --alleen-risicos  Exporteer alleen de risico-analyse
    --verbose         Uitgebreide logging
    --help            Toon deze hulptekst
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _maak_argument_parser() -> argparse.ArgumentParser:
    """Maakt de argumentparser aan."""
    parser = argparse.ArgumentParser(
        prog="forensic_dossier_engine",
        description=(
            "FORENSIC_DOSSIER_ENGINE — Forensische dossieranalyse\n"
            "Analyseert en structureert uitsluitend lokaal aangeleverde dossierdata.\n"
            "Reconstrueert tijdlijnen, detecteert inconsistenties en genereert\n"
            "juridisch bruikbare rapportstructuren."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Voorbeelden:\n"
            "  python -m dossier.engine.cli\n"
            "  python -m dossier.engine.cli --dossier /pad/naar/dossier\n"
            "  python -m dossier.engine.cli --verbose\n"
            "  python -m dossier.engine.cli --alleen-tijdlijn\n"
        ),
    )

    parser.add_argument(
        "--dossier",
        type=Path,
        default=Path("dossier"),
        metavar="PAD",
        help="Pad naar de dossiermap (standaard: ./dossier)",
    )

    parser.add_argument(
        "--uitvoer",
        type=Path,
        default=None,
        metavar="PAD",
        help="Pad naar de uitvoermap (standaard: <dossier>/output)",
    )

    parser.add_argument(
        "--alleen-tijdlijn",
        action="store_true",
        help="Exporteer alleen de tijdlijn (geen volledig rapport)",
    )

    parser.add_argument(
        "--alleen-risicos",
        action="store_true",
        help="Exporteer alleen de risico-analyse (geen volledig rapport)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Uitgebreide logging",
    )

    parser.add_argument(
        "--versie",
        action="version",
        version="FORENSIC_DOSSIER_ENGINE v1.0.0",
    )

    return parser


def _valideer_dossier_pad(dossier_pad: Path) -> bool:
    """Valideert of de dossiermap bestaat en de juiste structuur heeft."""
    if not dossier_pad.exists():
        print(f"❌ Fout: Dossiermap niet gevonden: {dossier_pad}", file=sys.stderr)
        print(
            "   Maak de map aan met de volgende structuur:\n"
            "   dossier/\n"
            "   ├── data/\n"
            "   ├── evidence/\n"
            "   ├── timeline/\n"
            "   └── output/",
            file=sys.stderr,
        )
        return False

    if not dossier_pad.is_dir():
        print(f"❌ Fout: {dossier_pad} is geen map.", file=sys.stderr)
        return False

    return True


def _initialiseer_dossier_structuur(dossier_pad: Path) -> None:
    """Maakt de dossierstructuur aan als deze niet bestaat."""
    mappen = ["data", "evidence", "timeline", "output"]
    for map_naam in mappen:
        (dossier_pad / map_naam).mkdir(parents=True, exist_ok=True)
    print(f"✅ Dossierstructuur aangemaakt in: {dossier_pad}")


def hoofd() -> int:
    """Hoofdfunctie van de CLI. Retourneert exitcode."""
    parser = _maak_argument_parser()
    args = parser.parse_args()

    # Verbose logging instellen
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    dossier_pad = args.dossier.resolve()
    uitvoer_pad = args.uitvoer.resolve() if args.uitvoer else dossier_pad / "output"

    print("╔══════════════════════════════════════════════════════════╗")
    print("║         FORENSIC_DOSSIER_ENGINE v1.0.0                  ║")
    print("║  Forensische dossieranalyse — Uitsluitend lokale data    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\nDossiermap:  {dossier_pad}")
    print(f"Uitvoermap:  {uitvoer_pad}\n")

    # Maak dossierstructuur aan als niet aanwezig
    if not dossier_pad.exists():
        print(f"ℹ️  Dossiermap niet gevonden. Aanmaken...")
        _initialiseer_dossier_structuur(dossier_pad)
        print(
            "\n⚠️  Voeg bewijsstukken toe aan de dossiermappen:\n"
            f"   {dossier_pad}/data/      — Ruwe data en bronbestanden\n"
            f"   {dossier_pad}/evidence/  — Bewijsstukken\n"
            f"   {dossier_pad}/timeline/  — Tijdlijn-gerelateerde documenten\n"
        )

    if not _valideer_dossier_pad(dossier_pad):
        return 1

    # Importeer engine modules
    try:
        from .orchestrator import voer_volledige_analyse_uit
        from .importer import importeer_bestanden
        from .tijdlijn import bouw_tijdlijn, detecteer_temporele_gaten
        from .risico_analyse import voer_risico_analyse_uit
        from .consistency_scan import voer_consistency_scan_uit
        from .rapport_export import (
            exporteer_tijdlijn_markdown,
            exporteer_risicos_markdown,
        )
    except ImportError as exc:
        print(f"❌ Importfout: {exc}", file=sys.stderr)
        return 1

    try:
        if args.alleen_tijdlijn:
            # Alleen tijdlijn exporteren
            print("📅 Tijdlijn reconstrueren...")
            bewijs_items = importeer_bestanden(dossier_pad)
            tijdlijn = bouw_tijdlijn(bewijs_items)
            uitvoer_bestand = uitvoer_pad / "tijdlijn.md"
            exporteer_tijdlijn_markdown(tijdlijn, uitvoer_bestand)
            print(f"✅ Tijdlijn geëxporteerd: {uitvoer_bestand}")
            print(f"   {len(tijdlijn)} tijdlijngebeurtenissen")

        elif args.alleen_risicos:
            # Alleen risico-analyse exporteren
            print("⚠️  Risico-analyse uitvoeren...")
            bewijs_items = importeer_bestanden(dossier_pad)
            tijdlijn = bouw_tijdlijn(bewijs_items)
            temporele_gaten = detecteer_temporele_gaten(tijdlijn)
            inconsistenties = voer_consistency_scan_uit(bewijs_items)
            risicos = voer_risico_analyse_uit(
                bewijs_items, tijdlijn, inconsistenties, temporele_gaten
            )
            uitvoer_bestand = uitvoer_pad / "risico_analyse.md"
            exporteer_risicos_markdown(risicos, uitvoer_bestand)
            print(f"✅ Risico-analyse geëxporteerd: {uitvoer_bestand}")
            print(f"   {len(risicos)} risico('s) geïdentificeerd")

        else:
            # Volledige analyse
            print("🔍 Volledige forensische analyse starten...\n")
            rapport = voer_volledige_analyse_uit(dossier_pad, uitvoer_pad)

            print("\n" + "═" * 60)
            print("ANALYSE VOLTOOID")
            print("═" * 60)
            print(f"\n{rapport.samenvatting}\n")
            print(f"📄 Rapporten opgeslagen in: {uitvoer_pad}")
            print(f"   • hoofdrapport.md")
            print(f"   • tijdlijn.md")
            print(f"   • risico_analyse.md")
            print(f"   • samenvatting.json")

            if rapport.conclusies:
                print("\n📋 Conclusies:")
                for i, conclusie in enumerate(rapport.conclusies[:3], 1):
                    print(f"   {i}. {conclusie[:100]}...")

            if rapport.aanbevelingen:
                print("\n💡 Prioritaire aanbevelingen:")
                for i, aanbeveling in enumerate(rapport.aanbevelingen[:3], 1):
                    print(f"   {i}. {aanbeveling[:100]}...")

    except KeyboardInterrupt:
        print("\n⚠️  Analyse onderbroken door gebruiker.")
        return 130
    except Exception as exc:
        print(f"\n❌ Fout tijdens analyse: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(hoofd())

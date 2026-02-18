#!/usr/bin/env node
/**
 * FORENSIC_DOSSIER_ENGINE — Node.js Runner
 * Voert de forensische dossieranalyse uit en genereert rapporten.
 * Werkt uitsluitend met lokale dossierdata.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// ─── Configuratie ─────────────────────────────────────────────────────────────

const WORKSPACE_ROOT = path.resolve(__dirname, '..');
const DOSSIER_ROOT = path.resolve(__dirname);
const UITVOER_MAP = path.join(DOSSIER_ROOT, 'output');

const ONDERSTEUNDE_EXTENSIES = new Set(['.pdf', '.txt', '.json', '.html', '.eml', '.csv', '.md']);

const JURIDISCHE_TERMEN = [
  'contract', 'bewijs', 'zaak', 'advocaat', 'rechtbank', 'procedure',
  'klacht', 'vonnis', 'uitspraak', 'dagvaarding', 'verweer', 'eis',
  'gedaagde', 'eiser', 'rechter', 'hoger beroep', 'cassatie',
  'bewijslast', 'aanklacht', 'verzoekschrift', 'beschikking',
  'executie', 'beslaglegging', 'faillissement', 'curator',
];

const AANNAME_MARKERS = [
  'ik denk', 'vermoed', 'misschien', 'waarschijnlijk', 'volgens mij',
  'zou kunnen', 'lijkt erop', 'vermoedelijk', 'mogelijk', 'wellicht',
  'naar mijn mening', 'ik geloof', 'het schijnt',
];

const DATUM_REGEX = /\b(20\d{2}[-\/]\d{2}[-\/]\d{2}|\d{2}[-\/]\d{2}[-\/]20\d{2})\b/g;

const BEKENDE_PERSONEN = [
  'Kristof Huibers', 'Anneke Coenen', 'Yolanda Dello', 'Yolanda Anne', 'Kristof',
];

// ─── Hulpfuncties ─────────────────────────────────────────────────────────────

function berekenHash(bestandPad) {
  const inhoud = fs.readFileSync(bestandPad);
  return crypto.createHash('sha256').update(inhoud).digest('hex');
}

function leesTekst(bestandPad) {
  const ext = path.extname(bestandPad).toLowerCase();
  if (ONDERSTEUNDE_EXTENSIES.has(ext)) {
    try {
      return fs.readFileSync(bestandPad, 'utf-8');
    } catch (e) {
      return `[Leesfout: ${e.message}]`;
    }
  }
  return '';
}

function extraheerDatums(tekst) {
  const gevonden = [];
  let match;
  const regex = new RegExp(DATUM_REGEX.source, 'g');
  while ((match = regex.exec(tekst)) !== null) {
    if (!gevonden.includes(match[1])) {
      gevonden.push(match[1]);
    }
  }
  return gevonden.slice(0, 30);
}

function normaliseerDatum(datumStr) {
  // ISO: 2024-01-15
  const isoMatch = datumStr.match(/^(20\d{2})[-\/](\d{2})[-\/](\d{2})$/);
  if (isoMatch) return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`;
  // NL: 15-01-2024
  const nlMatch = datumStr.match(/^(\d{2})[-\/](\d{2})[-\/](20\d{2})$/);
  if (nlMatch) return `${nlMatch[3]}-${nlMatch[2]}-${nlMatch[1]}`;
  return null;
}

function extraheerPersonen(tekst) {
  const gevonden = [];
  for (const naam of BEKENDE_PERSONEN) {
    if (tekst.toLowerCase().includes(naam.toLowerCase())) {
      if (!gevonden.includes(naam)) gevonden.push(naam);
    }
  }
  // Heuristisch: Voornaam Achternaam patroon
  const patroon = /\b([A-Z][a-z]+ [A-Z][a-z]+)\b/g;
  let match;
  while ((match = patroon.exec(tekst)) !== null) {
    if (!gevonden.includes(match[1]) && match[1].length > 5) {
      gevonden.push(match[1]);
    }
  }
  return gevonden.slice(0, 20);
}

function extraheerJuridischeTermen(tekst) {
  const tekstLower = tekst.toLowerCase();
  return JURIDISCHE_TERMEN.filter(term => tekstLower.includes(term));
}

function splitsFeitenAannames(tekst) {
  const feiten = [];
  const aannames = [];
  for (const regel of tekst.split('\n')) {
    const schoon = regel.trim();
    if (schoon.length < 15) continue;
    const laag = schoon.toLowerCase();
    if (AANNAME_MARKERS.some(m => laag.includes(m))) {
      aannames.push(schoon);
    } else {
      feiten.push(schoon);
    }
  }
  return { feiten: feiten.slice(0, 60), aannames: aannames.slice(0, 40) };
}

function detecteerInconsistentiesLokaal(feiten, aannames) {
  const bevindingen = [];
  for (const aanname of aannames) {
    const al = aanname.toLowerCase();
    const heeftNegA = /\b(niet|nooit|geen|nimmer)\b/.test(al);
    for (const feit of feiten.slice(0, 20)) {
      const fl = feit.toLowerCase();
      const heeftNegF = /\b(niet|nooit|geen|nimmer)\b/.test(fl);
      const tokensA = al.split(/\s+/).filter(t => t.length > 4);
      const overlap = tokensA.filter(t => fl.includes(t));
      if (overlap.length >= 2 && heeftNegA !== heeftNegF) {
        bevindingen.push(
          `Mogelijke tegenspraak: Aanname: '${aanname.slice(0, 100)}' ↔ Feit: '${feit.slice(0, 100)}'`
        );
        break;
      }
    }
  }
  return bevindingen.slice(0, 20);
}

function bepaalJuridischeRelevantie(tekst) {
  const score = JURIDISCHE_TERMEN.filter(t => tekst.toLowerCase().includes(t)).length;
  if (score >= 4) return 'Hoog';
  if (score >= 2) return 'Middel';
  return 'Laag';
}

function bepaalBewijsgewicht(tekst, datums) {
  const lengteScore = Math.min(Math.floor(tekst.length / 1000), 3);
  const datumScore = Math.min(datums.length, 2);
  const juridischScore = Math.min(
    JURIDISCHE_TERMEN.filter(t => tekst.toLowerCase().includes(t)).length, 3
  );
  const totaal = lengteScore + datumScore + juridischScore;
  if (totaal >= 6) return 'hoog';
  if (totaal >= 3) return 'middel';
  return 'laag';
}

function detecteerPersoon(tekst, personen) {
  for (const naam of BEKENDE_PERSONEN) {
    if (tekst.toLowerCase().includes(naam.toLowerCase())) return naam;
  }
  return personen.length > 0 ? personen[0] : 'Onbekend';
}

function detecteerZaak(bestandPad, tekst) {
  const zaakMatch = tekst.match(/\b(zaak[-\s]?\w+|dossier[-\s]?\w+|procedure[-\s]?\w+)\b/i);
  if (zaakMatch) return zaakMatch[0].replace(/\s/g, '_').toLowerCase().slice(0, 50);
  if (tekst.toLowerCase().includes('zaak')) return 'algemene_zaak';
  const mapNaam = path.basename(path.dirname(bestandPad));
  const bestandNaam = path.basename(bestandPad, path.extname(bestandPad));
  return `${mapNaam}_${bestandNaam}`.replace(/\s/g, '_').slice(0, 50);
}

function itereerBestanden(mapPad) {
  const bestanden = [];
  if (!fs.existsSync(mapPad)) return bestanden;
  const items = fs.readdirSync(mapPad, { withFileTypes: true });
  for (const item of items) {
    const volledigPad = path.join(mapPad, item.name);
    if (item.isDirectory()) {
      bestanden.push(...itereerBestanden(volledigPad));
    } else if (item.isFile() && ONDERSTEUNDE_EXTENSIES.has(path.extname(item.name).toLowerCase())) {
      bestanden.push(volledigPad);
    }
  }
  return bestanden.sort();
}

// ─── Importeer bestanden ──────────────────────────────────────────────────────

function importeerBestanden(dossierRoot) {
  const mappen = ['data', 'evidence', 'timeline'];
  const bewijsItems = [];
  const verwerktHashes = new Set();

  for (const mapNaam of mappen) {
    const mapPad = path.join(dossierRoot, mapNaam);
    fs.mkdirSync(mapPad, { recursive: true });
    const bestanden = itereerBestanden(mapPad);

    for (const bestandPad of bestanden) {
      const sha256 = berekenHash(bestandPad);
      if (verwerktHashes.has(sha256)) continue;
      verwerktHashes.add(sha256);

      const tekst = leesTekst(bestandPad);
      const datums = extraheerDatums(tekst);
      const personen = extraheerPersonen(tekst);
      const juridischeTermen = extraheerJuridischeTermen(tekst);
      const { feiten, aannames } = splitsFeitenAannames(tekst);
      const inconsistenties = detecteerInconsistentiesLokaal(feiten, aannames);

      const geimporteerdOp = new Date().toISOString();
      const bewijsId = crypto.createHash('md5')
        .update(`${bestandPad}-${sha256}`)
        .digest('hex');

      const gedetecteerdePersoon = detecteerPersoon(tekst, personen);
      const gedetecteerdeZaak = detecteerZaak(bestandPad, tekst);
      const juridischeRelevantie = bepaalJuridischeRelevantie(tekst);
      const bewijsgewicht = bepaalBewijsgewicht(tekst, datums);

      bewijsItems.push({
        bewijs_id: bewijsId,
        bron_map: mapNaam,
        bestand_pad: bestandPad,
        bestandsnaam: path.basename(bestandPad),
        gedetecteerde_persoon: gedetecteerdePersoon,
        gedetecteerde_zaak: gedetecteerdeZaak,
        geimporteerd_op: geimporteerdOp,
        inhoud_hash: sha256,
        geextraheerde_tekst: tekst.slice(0, 12000),
        juridische_relevantie: juridischeRelevantie,
        bewijsgewicht,
        bewijs_keten: [`${geimporteerdOp} — Geïmporteerd: ${path.basename(bestandPad)} (SHA-256: ${sha256.slice(0, 16)}…)`],
        analyse: {
          feiten,
          aannames,
          inconsistenties,
          datums_gevonden: datums,
          personen_gevonden: personen,
          juridische_termen: juridischeTermen,
        },
        metadata: {
          pad: bestandPad,
          bestandsnaam: path.basename(bestandPad),
          extensie: path.extname(bestandPad).toLowerCase(),
          grootte_bytes: fs.statSync(bestandPad).size,
          sha256_hash: sha256,
          geimporteerd_op: geimporteerdOp,
          map_categorie: mapNaam,
        },
      });
    }
  }

  return bewijsItems;
}

// ─── Tijdlijn ─────────────────────────────────────────────────────────────────

function bouwTijdlijn(bewijsItems) {
  const gebeurtenissen = [];

  for (const item of bewijsItems) {
    // Importgebeurtenis
    gebeurtenissen.push({
      gebeurtenis_id: `import-${item.bewijs_id.slice(0, 8)}`,
      tijdstip: item.geimporteerd_op,
      titel: `Bestand geïmporteerd: ${item.bestandsnaam}`,
      beschrijving: `Bestand '${item.bestandsnaam}' geïmporteerd uit map '${item.bron_map}'. Juridische relevantie: ${item.juridische_relevantie}. Bewijsgewicht: ${item.bewijsgewicht}. Gedetecteerde persoon: ${item.gedetecteerde_persoon}.`,
      gerelateerde_bewijs_ids: [item.bewijs_id],
      vertrouwen: 'hoog',
      bron_bestand: item.bestandsnaam,
    });

    // Datums uit tekst
    for (let i = 0; i < item.analyse.datums_gevonden.length; i++) {
      const datumStr = item.analyse.datums_gevonden[i];
      const genormaliseerd = normaliseerDatum(datumStr);
      if (!genormaliseerd) continue;

      gebeurtenissen.push({
        gebeurtenis_id: `datum-${item.bewijs_id.slice(0, 8)}-${genormaliseerd}-${i}`,
        tijdstip: `${genormaliseerd}T00:00:00`,
        titel: `Datum gedetecteerd in ${item.bestandsnaam}`,
        beschrijving: `Datum '${datumStr}' gevonden in '${item.bestandsnaam}'. Persoon: ${item.gedetecteerde_persoon}. Zaak: ${item.gedetecteerde_zaak}.`,
        gerelateerde_bewijs_ids: [item.bewijs_id],
        vertrouwen: 'middel',
        bron_bestand: item.bestandsnaam,
      });
    }
  }

  // Sorteren op tijdstip
  gebeurtenissen.sort((a, b) => {
    const da = new Date(a.tijdstip);
    const db = new Date(b.tijdstip);
    return da - db;
  });

  return gebeurtenissen;
}

function detecteerTemporeleGaten(tijdlijn, drempelDagen = 90) {
  const gaten = [];
  if (tijdlijn.length < 2) return gaten;

  let vorigeDt = new Date(tijdlijn[0].tijdstip);
  for (let i = 1; i < tijdlijn.length; i++) {
    const huidigeDt = new Date(tijdlijn[i].tijdstip);
    if (isNaN(vorigeDt) || isNaN(huidigeDt)) { vorigeDt = huidigeDt; continue; }
    const verschilDagen = Math.floor((huidigeDt - vorigeDt) / (1000 * 60 * 60 * 24));
    if (verschilDagen > drempelDagen) {
      gaten.push({
        van: vorigeDt.toISOString().slice(0, 10),
        tot: huidigeDt.toISOString().slice(0, 10),
        duur_dagen: verschilDagen,
        beschrijving: `Tijdsgat van ${verschilDagen} dagen gedetecteerd (${vorigeDt.toLocaleDateString('nl-NL')} → ${huidigeDt.toLocaleDateString('nl-NL')})`,
      });
    }
    vorigeDt = huidigeDt;
  }
  return gaten;
}

// ─── Consistency Scan ─────────────────────────────────────────────────────────

function voerConsistencyScanUit(bewijsItems) {
  const bevindingen = [];

  // Scan feit-tegenspraken tussen documenten
  for (let i = 0; i < bewijsItems.length; i++) {
    for (let j = i + 1; j < bewijsItems.length; j++) {
      const itemA = bewijsItems[i];
      const itemB = bewijsItems[j];

      // Vergelijk aannames van A met feiten van B
      for (const aanname of itemA.analyse.aannames.slice(0, 10)) {
        const al = aanname.toLowerCase();
        const heeftNegA = /\b(niet|nooit|geen|nimmer|betwist|ontkent)\b/.test(al);
        for (const feit of itemB.analyse.feiten.slice(0, 20)) {
          const fl = feit.toLowerCase();
          const heeftNegF = /\b(niet|nooit|geen|nimmer)\b/.test(fl);
          const tokensA = al.split(/\s+/).filter(t => t.length > 4);
          const overlap = tokensA.filter(t => fl.includes(t));
          if (overlap.length >= 2 && heeftNegA !== heeftNegF) {
            const bevindingId = crypto.createHash('md5')
              .update(`feit_tegenspraak-${itemA.bewijs_id.slice(0, 8)}-${itemB.bewijs_id.slice(0, 8)}`)
              .digest('hex').slice(0, 12);
            bevindingen.push({
              bevinding_id: bevindingId,
              type: 'feit_tegenspraak',
              beschrijving: `Feitelijke tegenspraak tussen '${itemA.bestandsnaam}' en '${itemB.bestandsnaam}'. Aanname: '${aanname.slice(0, 120)}'. Feit: '${feit.slice(0, 120)}'.`,
              bewijs_id_a: itemA.bewijs_id,
              bewijs_id_b: itemB.bewijs_id,
              ernst: 'hoog',
              aanbeveling: 'Verifieer welke stelling correct is door aanvullend bewijs te verzamelen.',
            });
            break;
          }
        }
      }
    }
  }

  // Duplicaatdetectie
  const hashNaarItems = {};
  for (const item of bewijsItems) {
    if (!hashNaarItems[item.inhoud_hash]) hashNaarItems[item.inhoud_hash] = [];
    hashNaarItems[item.inhoud_hash].push(item);
  }
  for (const [hash, items] of Object.entries(hashNaarItems)) {
    if (items.length > 1) {
      for (let i = 0; i < items.length; i++) {
        for (let j = i + 1; j < items.length; j++) {
          if (items[i].bestand_pad !== items[j].bestand_pad) {
            const bevindingId = crypto.createHash('md5')
              .update(`duplicaat-${items[i].bewijs_id.slice(0, 8)}-${items[j].bewijs_id.slice(0, 8)}`)
              .digest('hex').slice(0, 12);
            bevindingen.push({
              bevinding_id: bevindingId,
              type: 'duplicaat_bestand',
              beschrijving: `Identieke bestanden: '${items[i].bestandsnaam}' en '${items[j].bestandsnaam}' (SHA-256: ${hash.slice(0, 16)}…).`,
              bewijs_id_a: items[i].bewijs_id,
              bewijs_id_b: items[j].bewijs_id,
              ernst: 'laag',
              aanbeveling: 'Controleer of het duplicaat intentioneel is.',
            });
          }
        }
      }
    }
  }

  return bevindingen;
}

// ─── Risico-analyse ───────────────────────────────────────────────────────────

function voerRisicoAnalyseUit(bewijsItems, tijdlijn, inconsistenties, temporeleGaten) {
  const risicos = [];
  const huidigJaar = new Date().getFullYear();

  // Juridische risico's
  const laagGewichtItems = bewijsItems.filter(i => i.bewijsgewicht === 'laag');
  if (laagGewichtItems.length > bewijsItems.length * 0.5 && bewijsItems.length > 0) {
    risicos.push({
      risico_id: crypto.createHash('md5').update('juridisch-laag_bewijsgewicht').digest('hex').slice(0, 12),
      categorie: 'juridisch',
      omschrijving: `${laagGewichtItems.length} van ${bewijsItems.length} bewijsstukken hebben een laag bewijsgewicht. Dit verzwakt de juridische positie.`,
      niveau: 'hoog',
      betrokken_bewijs_ids: laagGewichtItems.map(i => i.bewijs_id),
      mitigatie_advies: 'Verzamel aanvullend bewijs met hogere juridische waarde: officiële documenten, notariële akten, rechterlijke uitspraken.',
    });
  }

  // Procedurele risico's — lege mappen
  const mappen = new Set(bewijsItems.map(i => i.bron_map));
  const verwachteMappen = ['data', 'evidence', 'timeline'];
  const legeMappen = verwachteMappen.filter(m => !mappen.has(m));
  if (legeMappen.length > 0) {
    risicos.push({
      risico_id: crypto.createHash('md5').update('procedureel-lege_mappen').digest('hex').slice(0, 12),
      categorie: 'procedureel',
      omschrijving: `Lege dossiermappen gedetecteerd: ${legeMappen.join(', ')}. Mogelijk ontbreken er bewijsstukken.`,
      niveau: 'middel',
      betrokken_bewijs_ids: [],
      mitigatie_advies: `Voeg relevante bestanden toe aan de lege mappen: ${legeMappen.join(', ')}.`,
    });
  }

  // Bewijstechnische risico's — inconsistenties
  const hogeErnstInconsistenties = inconsistenties.filter(b => ['kritiek', 'hoog'].includes(b.ernst));
  if (hogeErnstInconsistenties.length > 0) {
    const betrokkenIds = [...new Set(hogeErnstInconsistenties.flatMap(b => [b.bewijs_id_a, b.bewijs_id_b]))];
    risicos.push({
      risico_id: crypto.createHash('md5').update('bewijstechnisch-hoge_inconsistenties').digest('hex').slice(0, 12),
      categorie: 'bewijstechnisch',
      omschrijving: `${hogeErnstInconsistenties.length} hoge/kritieke inconsistenties gedetecteerd. Dit ondermijnt de bewijskracht.`,
      niveau: 'hoog',
      betrokken_bewijs_ids: betrokkenIds.slice(0, 10),
      mitigatie_advies: 'Los de gedetecteerde inconsistenties op door aanvullend bewijs te verzamelen.',
    });
  }

  // Temporele risico's
  const groteGaten = temporeleGaten.filter(g => g.duur_dagen > 180);
  if (groteGaten.length > 0) {
    risicos.push({
      risico_id: crypto.createHash('md5').update('temporeel-grote_tijdsgaten').digest('hex').slice(0, 12),
      categorie: 'temporeel',
      omschrijving: `${groteGaten.length} grote tijdsgat(en) gedetecteerd (> 180 dagen). Grootste gat: ${Math.max(...groteGaten.map(g => g.duur_dagen))} dagen.`,
      niveau: 'middel',
      betrokken_bewijs_ids: [],
      mitigatie_advies: 'Verklaar de tijdsgaten of verzamel aanvullend bewijs voor de ontbrekende periodes.',
    });
  }

  // Verjaringsrisico
  if (tijdlijn.length > 0) {
    const vroegsteJaar = Math.min(...tijdlijn
      .map(g => new Date(g.tijdstip).getFullYear())
      .filter(y => y > 2000));
    if (vroegsteJaar > 0 && (huidigJaar - vroegsteJaar) >= 5) {
      risicos.push({
        risico_id: crypto.createHash('md5').update('procedureel-verjaring').digest('hex').slice(0, 12),
        categorie: 'procedureel',
        omschrijving: `Verjaringsrisico: vroegste tijdlijngebeurtenis dateert uit ${vroegsteJaar} (${huidigJaar - vroegsteJaar} jaar geleden). Standaard civiele verjaringstermijn is 5 jaar.`,
        niveau: 'kritiek',
        betrokken_bewijs_ids: [],
        mitigatie_advies: 'Raadpleeg onmiddellijk een advocaat over de toepasselijke verjaringstermijnen.',
      });
    }
  }

  // Sorteer op ernst
  const ernstVolgorde = { kritiek: 0, hoog: 1, middel: 2, laag: 3, geen: 4 };
  risicos.sort((a, b) => (ernstVolgorde[a.niveau] || 5) - (ernstVolgorde[b.niveau] || 5));

  return risicos;
}

// ─── Rapport genereren ────────────────────────────────────────────────────────

function ernstBadge(niveau) {
  const badges = { kritiek: '🔴 KRITIEK', hoog: '🟠 HOOG', middel: '🟡 MIDDEL', laag: '🟢 LAAG', geen: '⚪ GEEN' };
  return badges[niveau] || '❓ ONBEKEND';
}

function gewichtBadge(gewicht) {
  const badges = { hoog: '⬆️ Hoog', middel: '➡️ Middel', laag: '⬇️ Laag', onbekend: '❓ Onbekend' };
  return badges[gewicht] || '❓ Onbekend';
}

function vertrouwenBadge(vertrouwen) {
  const badges = { hoog: '✅ Hoog', middel: '⚠️ Middel', laag: '❌ Laag' };
  return badges[vertrouwen] || '❓ Onbekend';
}

function genereerHoofdrapport(rapport) {
  const gegenereerd = new Date(rapport.gegenereerd_op).toLocaleString('nl-NL', { timeZone: 'UTC' });
  const lijnen = [];

  // Voorblad
  lijnen.push(`# FORENSISCH DOSSIERRAPPORT`);
  lijnen.push(`\n${'─'.repeat(80)}\n`);
  lijnen.push(`**Rapport ID:** \`${rapport.rapport_id}\``);
  lijnen.push(`**Gegenereerd op:** ${gegenereerd} UTC`);
  lijnen.push(`**Dossierlocatie:** \`${rapport.dossier_pad}\``);
  lijnen.push(`\n${'─'.repeat(80)}\n`);
  lijnen.push(`## Samenvatting\n`);
  lijnen.push(rapport.samenvatting);
  lijnen.push(`\n### Statistieken\n`);
  lijnen.push(`| Categorie | Aantal |`);
  lijnen.push(`|-----------|--------|`);
  lijnen.push(`| Totaal bestanden geanalyseerd | ${rapport.totaal_bestanden} |`);
  lijnen.push(`| Bewijsstukken verwerkt | ${rapport.totaal_bewijs_items} |`);
  lijnen.push(`| Tijdlijngebeurtenissen | ${rapport.totaal_tijdlijn_gebeurtenissen} |`);
  lijnen.push(`| Inconsistenties gedetecteerd | ${rapport.totaal_inconsistenties} |`);
  lijnen.push(`| Risico's geïdentificeerd | ${rapport.totaal_risicos} |`);
  lijnen.push(`\n> **Disclaimer:** Dit rapport is gegenereerd door de FORENSIC_DOSSIER_ENGINE op basis van`);
  lijnen.push(`> uitsluitend lokaal aangeleverde dossierdata. Elke conclusie is herleidbaar naar brondata.`);
  lijnen.push(`> Dit rapport vervangt geen juridisch advies van een gekwalificeerde advocaat.\n`);
  lijnen.push(`${'─'.repeat(80)}\n`);

  // Conclusies
  lijnen.push(`## Conclusies en Aanbevelingen\n`);
  if (rapport.conclusies.length > 0) {
    lijnen.push(`### Conclusies\n`);
    rapport.conclusies.forEach((c, i) => lijnen.push(`${i + 1}. ${c}`));
    lijnen.push('');
  }
  if (rapport.aanbevelingen.length > 0) {
    lijnen.push(`### Aanbevelingen\n`);
    rapport.aanbevelingen.forEach((a, i) => lijnen.push(`${i + 1}. ${a}`));
    lijnen.push('');
  }

  // Tijdlijn
  lijnen.push(`## Tijdlijnreconstructie\n`);
  lijnen.push(`Totaal **${rapport.tijdlijn.length}** tijdlijngebeurtenissen gereconstrueerd.\n`);
  const perJaar = {};
  for (const g of rapport.tijdlijn) {
    const jaar = g.tijdstip.slice(0, 4) || 'Onbekend';
    if (!perJaar[jaar]) perJaar[jaar] = [];
    perJaar[jaar].push(g);
  }
  for (const jaar of Object.keys(perJaar).sort()) {
    lijnen.push(`### ${jaar}\n`);
    for (const g of perJaar[jaar]) {
      const datum = g.tijdstip.slice(0, 10);
      const vertrouwen = vertrouwenBadge(g.vertrouwen);
      const bewijsRefs = g.gerelateerde_bewijs_ids.slice(0, 3).map(id => `\`${id.slice(0, 8)}…\``).join(', ') || '*geen*';
      lijnen.push(`**${datum}** — ${g.titel}`);
      lijnen.push(`*Vertrouwen: ${vertrouwen} | Bron: ${g.bron_bestand || 'onbekend'} | Bewijs-ID: ${bewijsRefs}*`);
      lijnen.push(`${g.beschrijving}\n`);
    }
  }

  // Inconsistenties
  lijnen.push(`## Consistency Scan — Inconsistenties\n`);
  if (rapport.inconsistenties.length === 0) {
    lijnen.push(`✅ *Geen inconsistenties gedetecteerd.*\n`);
  } else {
    lijnen.push(`Totaal **${rapport.inconsistenties.length}** inconsistentie(s) gedetecteerd.\n`);
    const perType = {};
    for (const b of rapport.inconsistenties) {
      if (!perType[b.type]) perType[b.type] = [];
      perType[b.type].push(b);
    }
    const typeLabels = {
      datum_conflict: 'Datumconflicten',
      persoon_conflict: 'Persoonconflicten',
      feit_tegenspraak: 'Feitelijke tegenspraken',
      duplicaat_bestand: 'Duplicaatbestanden',
    };
    for (const [type, bevindingen] of Object.entries(perType)) {
      const label = typeLabels[type] || type;
      lijnen.push(`### ${label} (${bevindingen.length})\n`);
      for (const b of bevindingen) {
        lijnen.push(`**Bevinding \`${b.bevinding_id}\`** — Ernst: ${ernstBadge(b.ernst)}`);
        lijnen.push(`*Bewijs A: \`${b.bewijs_id_a.slice(0, 8)}…\` | Bewijs B: \`${b.bewijs_id_b.slice(0, 8)}…\`*`);
        lijnen.push(`${b.beschrijving}`);
        lijnen.push(`**Aanbeveling:** ${b.aanbeveling}\n`);
      }
    }
  }

  // Risico-analyse
  lijnen.push(`## Risico-analyse\n`);
  if (rapport.risicos.length === 0) {
    lijnen.push(`✅ *Geen risico's geïdentificeerd.*\n`);
  } else {
    lijnen.push(`Totaal **${rapport.risicos.length}** risico('s) geïdentificeerd.\n`);
    lijnen.push(`### Risico-overzicht\n`);
    lijnen.push(`| # | Categorie | Niveau | Omschrijving |`);
    lijnen.push(`|---|-----------|--------|--------------|`);
    rapport.risicos.forEach((r, i) => {
      const kort = r.omschrijving.length > 80 ? r.omschrijving.slice(0, 80) + '…' : r.omschrijving;
      lijnen.push(`| ${i + 1} | ${r.categorie.charAt(0).toUpperCase() + r.categorie.slice(1)} | ${ernstBadge(r.niveau)} | ${kort} |`);
    });
    lijnen.push('');
    const perCategorie = {};
    for (const r of rapport.risicos) {
      if (!perCategorie[r.categorie]) perCategorie[r.categorie] = [];
      perCategorie[r.categorie].push(r);
    }
    for (const [cat, items] of Object.entries(perCategorie)) {
      lijnen.push(`### ${cat.charAt(0).toUpperCase() + cat.slice(1)} Risico's\n`);
      for (const r of items) {
        const bewijsRefs = r.betrokken_bewijs_ids.slice(0, 3).map(id => `\`${id.slice(0, 8)}…\``).join(', ') || '*geen specifiek bewijs*';
        lijnen.push(`**Risico \`${r.risico_id}\`** — ${ernstBadge(r.niveau)}`);
        lijnen.push(`*Betrokken bewijs: ${bewijsRefs}*`);
        lijnen.push(`${r.omschrijving}`);
        lijnen.push(`**Mitigatie:** ${r.mitigatie_advies}\n`);
      }
    }
  }

  // Bewijsstructuur per map
  lijnen.push(`## Bewijsstructuur per Map\n`);
  for (const structuur of rapport.map_structuren) {
    lijnen.push(`### Map: \`${structuur.map_naam}/\`\n`);
    lijnen.push(`**Pad:** \`${structuur.map_pad}\``);
    lijnen.push(`**Aantal bestanden:** ${structuur.aantal_bestanden}`);
    lijnen.push(`**Dominante persoon:** ${structuur.dominante_persoon}`);
    lijnen.push(`**Dominante zaak:** ${structuur.dominante_zaak}`);
    if (structuur.tijdspanne_van && structuur.tijdspanne_tot) {
      lijnen.push(`**Tijdspanne:** ${structuur.tijdspanne_van} → ${structuur.tijdspanne_tot}`);
    }
    lijnen.push(`\n${structuur.samenvatting}\n`);
    if (structuur.bewijs_items.length > 0) {
      lijnen.push(`#### Bewijsstukken\n`);
      lijnen.push(`| Bestand | Persoon | Relevantie | Gewicht | Bewijs-ID |`);
      lijnen.push(`|---------|---------|------------|---------|-----------|`);
      for (const item of structuur.bewijs_items) {
        lijnen.push(`| \`${item.bestandsnaam}\` | ${item.gedetecteerde_persoon} | ${item.juridische_relevantie} | ${gewichtBadge(item.bewijsgewicht)} | \`${item.bewijs_id.slice(0, 8)}…\` |`);
      }
      lijnen.push('');
    }
  }

  // Gedetailleerde bewijsstukken
  lijnen.push(`## Gedetailleerde Bewijsstukken\n`);
  lijnen.push(`Totaal **${rapport.bewijs_items.length}** bewijsstuk(ken) geanalyseerd.\n`);
  for (const item of rapport.bewijs_items) {
    lijnen.push(`### \`${item.bestandsnaam}\`\n`);
    lijnen.push(`**Bewijs-ID:** \`${item.bewijs_id}\``);
    lijnen.push(`**Bronmap:** \`${item.bron_map}/\``);
    lijnen.push(`**Geïmporteerd:** ${item.geimporteerd_op.slice(0, 19)}`);
    lijnen.push(`**Persoon:** ${item.gedetecteerde_persoon}`);
    lijnen.push(`**Zaak:** ${item.gedetecteerde_zaak}`);
    lijnen.push(`**Juridische relevantie:** ${item.juridische_relevantie}`);
    lijnen.push(`**Bewijsgewicht:** ${gewichtBadge(item.bewijsgewicht)}`);
    lijnen.push(`**SHA-256:** \`${item.inhoud_hash.slice(0, 32)}…\``);
    lijnen.push('');
    if (item.bewijs_keten.length > 0) {
      lijnen.push(`**Bewijs-keten (Chain of Custody):**`);
      item.bewijs_keten.forEach(stap => lijnen.push(`- ${stap}`));
      lijnen.push('');
    }
    if (item.analyse.datums_gevonden.length > 0) {
      lijnen.push(`**Gevonden datums:** ${item.analyse.datums_gevonden.slice(0, 10).join(', ')}`);
      lijnen.push('');
    }
    if (item.analyse.juridische_termen.length > 0) {
      lijnen.push(`**Juridische termen:** ${item.analyse.juridische_termen.join(', ')}`);
      lijnen.push('');
    }
    if (item.analyse.feiten.length > 0) {
      lijnen.push(`**Geëxtraheerde feiten (eerste 5):**`);
      item.analyse.feiten.slice(0, 5).forEach(f => lijnen.push(`- ${f.slice(0, 150)}`));
      lijnen.push('');
    }
    if (item.analyse.aannames.length > 0) {
      lijnen.push(`**Gedetecteerde aannames (eerste 3):**`);
      item.analyse.aannames.slice(0, 3).forEach(a => lijnen.push(`- ⚠️ ${a.slice(0, 150)}`));
      lijnen.push('');
    }
    if (item.analyse.inconsistenties.length > 0) {
      lijnen.push(`**Interne inconsistenties:**`);
      item.analyse.inconsistenties.slice(0, 3).forEach(inc => lijnen.push(`- ❗ ${inc.slice(0, 150)}`));
      lijnen.push('');
    }
    lijnen.push('─'.repeat(40));
    lijnen.push('');
  }

  // Voettekst
  lijnen.push(`\n${'─'.repeat(80)}`);
  lijnen.push(`*Rapport gegenereerd door FORENSIC_DOSSIER_ENGINE v1.0.0 — ${rapport.gegenereerd_op.slice(0, 19)} UTC*`);
  lijnen.push(`*Alle conclusies zijn herleidbaar naar lokale brondata. Geen externe bronnen geraadpleegd.*`);

  return lijnen.join('\n');
}

// ─── Hoofdprogramma ───────────────────────────────────────────────────────────

function hoofd() {
  console.log('╔══════════════════════════════════════════════════════════╗');
  console.log('║         FORENSIC_DOSSIER_ENGINE v1.0.0                  ║');
  console.log('║  Forensische dossieranalyse — Uitsluitend lokale data    ║');
  console.log('╚══════════════════════════════════════════════════════════╝');
  console.log(`\nDossiermap:  ${DOSSIER_ROOT}`);
  console.log(`Uitvoermap:  ${UITVOER_MAP}\n`);

  fs.mkdirSync(UITVOER_MAP, { recursive: true });

  // Stap 1: Importeer bestanden
  console.log('Stap 1/6: Bestanden importeren...');
  const bewijsItems = importeerBestanden(DOSSIER_ROOT);
  console.log(`  → ${bewijsItems.length} bewijsstuk(ken) geïmporteerd`);

  // Stap 2: Tijdlijn
  console.log('Stap 2/6: Tijdlijn reconstrueren...');
  const tijdlijn = bouwTijdlijn(bewijsItems);
  const temporeleGaten = detecteerTemporeleGaten(tijdlijn, 90);
  console.log(`  → ${tijdlijn.length} tijdlijngebeurtenissen, ${temporeleGaten.length} temporele gaten`);

  // Stap 3: Consistency scan
  console.log('Stap 3/6: Consistency scan uitvoeren...');
  const inconsistenties = voerConsistencyScanUit(bewijsItems);
  console.log(`  → ${inconsistenties.length} inconsistentie(s) gedetecteerd`);

  // Stap 4: Risico-analyse
  console.log('Stap 4/6: Risico-analyse uitvoeren...');
  const risicos = voerRisicoAnalyseUit(bewijsItems, tijdlijn, inconsistenties, temporeleGaten);
  const kritiekeRisicos = risicos.filter(r => r.niveau === 'kritiek').length;
  const hogeRisicos = risicos.filter(r => r.niveau === 'hoog').length;
  console.log(`  → ${risicos.length} risico('s) (${kritiekeRisicos} kritiek, ${hogeRisicos} hoog)`);

  // Stap 5: Bewijsstructuur per map
  console.log('Stap 5/6: Bewijsstructuur per map bouwen...');
  const verwachteMappen = ['data', 'evidence', 'timeline'];
  const mapStructuren = verwachteMappen.map(mapNaam => {
    const items = bewijsItems.filter(i => i.bron_map === mapNaam);
    const alleDatums = items.flatMap(i => i.analyse.datums_gevonden).concat(items.map(i => i.geimporteerd_op));
    const personen = items.map(i => i.gedetecteerde_persoon).filter(p => p !== 'Onbekend');
    const zaken = items.map(i => i.gedetecteerde_zaak);
    const telPersoon = {};
    personen.forEach(p => { telPersoon[p] = (telPersoon[p] || 0) + 1; });
    const dominantePersoon = Object.keys(telPersoon).sort((a, b) => telPersoon[b] - telPersoon[a])[0] || 'Onbekend';
    const telZaak = {};
    zaken.forEach(z => { telZaak[z] = (telZaak[z] || 0) + 1; });
    const dominanteZaak = Object.keys(telZaak).sort((a, b) => telZaak[b] - telZaak[a])[0] || 'Onbekend';

    const geldigeDatums = alleDatums.map(d => new Date(d)).filter(d => !isNaN(d));
    const vroegste = geldigeDatums.length > 0 ? new Date(Math.min(...geldigeDatums)).toISOString().slice(0, 10) : '';
    const laatste = geldigeDatums.length > 0 ? new Date(Math.max(...geldigeDatums)).toISOString().slice(0, 10) : '';

    const hoogGewicht = items.filter(i => i.bewijsgewicht === 'hoog').length;
    const middelGewicht = items.filter(i => i.bewijsgewicht === 'middel').length;
    const laagGewicht = items.filter(i => i.bewijsgewicht === 'laag').length;
    const hoogRel = items.filter(i => i.juridische_relevantie === 'Hoog').length;
    const middelRel = items.filter(i => i.juridische_relevantie === 'Middel').length;

    const samenvatting = items.length === 0
      ? `Map '${mapNaam}' bevat geen bewijsstukken.`
      : `Map '${mapNaam}' bevat ${items.length} bewijsstuk(ken). Bewijsgewicht: ${hoogGewicht} hoog, ${middelGewicht} middel, ${laagGewicht} laag. Juridische relevantie: ${hoogRel} hoog, ${middelRel} middel. Dominante persoon: ${dominantePersoon}. Dominante zaak: ${dominanteZaak}.${vroegste && laatste ? ` Tijdspanne: ${vroegste} tot ${laatste}.` : ''}`;

    return {
      map_naam: mapNaam,
      map_pad: path.join(DOSSIER_ROOT, mapNaam),
      aantal_bestanden: items.length,
      bewijs_items: items,
      samenvatting,
      dominante_persoon: dominantePersoon,
      dominante_zaak: dominanteZaak,
      tijdspanne_van: vroegste,
      tijdspanne_tot: laatste,
    };
  });
  console.log(`  → ${mapStructuren.length} mapstructuren gebouwd`);

  // Stap 6: Rapport genereren
  console.log('Stap 6/6: Rapport genereren...');
  const gegenereerdeOp = new Date().toISOString();
  const rapportId = crypto.createHash('md5').update(`${DOSSIER_ROOT}-${gegenereerdeOp}`).digest('hex').slice(0, 16);

  const status = kritiekeRisicos > 0 ? 'KRITIEK' : (hogeRisicos > 0 ? 'AANDACHT VEREIST' : 'NORMAAL');
  const samenvatting = `Het forensisch dossier bevat ${bewijsItems.length} bewijsstuk(ken) met ${tijdlijn.length} tijdlijngebeurtenissen. Er zijn ${inconsistenties.length} inconsistentie(s) en ${risicos.length} risico('s) geïdentificeerd (waarvan ${kritiekeRisicos} kritiek en ${hogeRisicos} hoog). Algehele dossierstatus: **${status}**.`;

  // Conclusies
  const conclusies = [];
  if (bewijsItems.length === 0) {
    conclusies.push('Het dossier bevat geen bewijsstukken. Voeg bestanden toe aan dossier/data, dossier/evidence of dossier/timeline.');
  } else {
    const hoogGewicht = bewijsItems.filter(i => i.bewijsgewicht === 'hoog').length;
    const hoogRel = bewijsItems.filter(i => i.juridische_relevantie === 'Hoog').length;
    conclusies.push(`Van de ${bewijsItems.length} bewijsstukken hebben ${hoogGewicht} een hoog bewijsgewicht en ${hoogRel} een hoge juridische relevantie.`);
  }
  if (tijdlijn.length > 0) {
    const vroegste = tijdlijn[0].tijdstip.slice(0, 10);
    const laatste = tijdlijn[tijdlijn.length - 1].tijdstip.slice(0, 10);
    conclusies.push(`De tijdlijn beslaat de periode van ${vroegste} tot ${laatste} met ${tijdlijn.length} geregistreerde gebeurtenissen.`);
  }
  if (temporeleGaten.length > 0) {
    const grootsteGat = temporeleGaten.reduce((a, b) => a.duur_dagen > b.duur_dagen ? a : b);
    conclusies.push(`Er zijn ${temporeleGaten.length} tijdsgat(en) gedetecteerd. Het grootste gat bedraagt ${grootsteGat.duur_dagen} dagen (${grootsteGat.van} → ${grootsteGat.tot}).`);
  }
  if (inconsistenties.length > 0) {
    const hogeErnst = inconsistenties.filter(b => ['kritiek', 'hoog'].includes(b.ernst)).length;
    conclusies.push(`Er zijn ${inconsistenties.length} inconsistentie(s) gedetecteerd, waarvan ${hogeErnst} van hoge of kritieke ernst. Deze vereisen nader onderzoek.`);
  } else {
    conclusies.push('Geen significante inconsistenties gedetecteerd tussen de bewijsstukken.');
  }
  const kritiekeRisicoItems = risicos.filter(r => r.niveau === 'kritiek');
  if (kritiekeRisicoItems.length > 0) {
    conclusies.push(`KRITIEK: ${kritiekeRisicoItems.length} kritiek risico('s) geïdentificeerd. Onmiddellijke actie vereist: ${kritiekeRisicoItems.slice(0, 2).map(r => r.omschrijving.slice(0, 80)).join('; ')}.`);
  }

  // Aanbevelingen
  const aanbevelingen = [];
  risicos.filter(r => r.niveau === 'kritiek').forEach(r => aanbevelingen.push(`[KRITIEK] ${r.mitigatie_advies}`));
  risicos.filter(r => r.niveau === 'hoog').forEach(r => aanbevelingen.push(`[HOOG] ${r.mitigatie_advies}`));
  inconsistenties.filter(b => ['kritiek', 'hoog'].includes(b.ernst)).slice(0, 3).forEach(b => aanbevelingen.push(`[INCONSISTENTIE] ${b.aanbeveling}`));
  if (bewijsItems.length === 0) aanbevelingen.push('Voeg bewijsstukken toe aan de dossiermappen (dossier/data, dossier/evidence, dossier/timeline).');
  if (aanbevelingen.length === 0) aanbevelingen.push('Het dossier is in goede staat. Blijf bewijsstukken actueel houden en documenteer nieuwe ontwikkelingen.');

  const rapport = {
    rapport_id: rapportId,
    gegenereerd_op: gegenereerdeOp,
    dossier_pad: DOSSIER_ROOT,
    totaal_bestanden: bewijsItems.length,
    totaal_bewijs_items: bewijsItems.length,
    totaal_tijdlijn_gebeurtenissen: tijdlijn.length,
    totaal_inconsistenties: inconsistenties.length,
    totaal_risicos: risicos.length,
    bewijs_items: bewijsItems,
    tijdlijn,
    inconsistenties,
    risicos,
    map_structuren: mapStructuren,
    samenvatting,
    conclusies,
    aanbevelingen: aanbevelingen.slice(0, 15),
  };

  // Exporteer rapporten
  const hoofdrapportPad = path.join(UITVOER_MAP, 'hoofdrapport.md');
  fs.writeFileSync(hoofdrapportPad, genereerHoofdrapport(rapport), 'utf-8');
  console.log(`  → Hoofdrapport: ${hoofdrapportPad}`);

  // Tijdlijn apart
  const tijdlijnPad = path.join(UITVOER_MAP, 'tijdlijn.md');
  const tijdlijnInhoud = `# Tijdlijn Export\n\n${rapport.tijdlijn.map(g => `**${g.tijdstip.slice(0, 10)}** — ${g.titel}\n${g.beschrijving}\n`).join('\n')}`;
  fs.writeFileSync(tijdlijnPad, tijdlijnInhoud, 'utf-8');
  console.log(`  → Tijdlijn: ${tijdlijnPad}`);

  // Risico-analyse apart
  const risicoPad = path.join(UITVOER_MAP, 'risico_analyse.md');
  const risicoInhoud = `# Risico-analyse Export\n\n${rapport.risicos.map(r => `## ${ernstBadge(r.niveau)} — ${r.categorie}\n${r.omschrijving}\n\n**Mitigatie:** ${r.mitigatie_advies}\n`).join('\n')}`;
  fs.writeFileSync(risicoPad, risicoInhoud, 'utf-8');
  console.log(`  → Risico-analyse: ${risicoPad}`);

  // JSON samenvatting
  const jsonPad = path.join(UITVOER_MAP, 'samenvatting.json');
  const jsonSamenvatting = {
    rapport_id: rapport.rapport_id,
    gegenereerd_op: rapport.gegenereerd_op,
    dossier_pad: rapport.dossier_pad,
    statistieken: {
      totaal_bestanden: rapport.totaal_bestanden,
      totaal_bewijs_items: rapport.totaal_bewijs_items,
      totaal_tijdlijn_gebeurtenissen: rapport.totaal_tijdlijn_gebeurtenissen,
      totaal_inconsistenties: rapport.totaal_inconsistenties,
      totaal_risicos: rapport.totaal_risicos,
    },
    samenvatting: rapport.samenvatting,
    conclusies: rapport.conclusies,
    aanbevelingen: rapport.aanbevelingen,
    risico_niveaus: {
      kritiek: risicos.filter(r => r.niveau === 'kritiek').length,
      hoog: risicos.filter(r => r.niveau === 'hoog').length,
      middel: risicos.filter(r => r.niveau === 'middel').length,
      laag: risicos.filter(r => r.niveau === 'laag').length,
    },
    bewijs_ids: bewijsItems.map(i => i.bewijs_id),
    inconsistentie_types: [...new Set(inconsistenties.map(b => b.type))],
  };
  fs.writeFileSync(jsonPad, JSON.stringify(jsonSamenvatting, null, 2), 'utf-8');
  console.log(`  → JSON-samenvatting: ${jsonPad}`);

  console.log('\n' + '═'.repeat(60));
  console.log('ANALYSE VOLTOOID');
  console.log('═'.repeat(60));
  console.log(`\n${rapport.samenvatting}\n`);
  console.log(`📄 Rapporten opgeslagen in: ${UITVOER_MAP}`);
  console.log(`   • hoofdrapport.md`);
  console.log(`   • tijdlijn.md`);
  console.log(`   • risico_analyse.md`);
  console.log(`   • samenvatting.json`);

  if (rapport.conclusies.length > 0) {
    console.log('\n📋 Conclusies:');
    rapport.conclusies.slice(0, 3).forEach((c, i) => console.log(`   ${i + 1}. ${c.slice(0, 100)}...`));
  }

  if (rapport.aanbevelingen.length > 0) {
    console.log('\n💡 Prioritaire aanbevelingen:');
    rapport.aanbevelingen.slice(0, 3).forEach((a, i) => console.log(`   ${i + 1}. ${a.slice(0, 100)}...`));
  }

  return 0;
}

process.exit(hoofd());

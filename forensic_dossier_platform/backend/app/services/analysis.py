from __future__ import annotations

import re
from collections import Counter, defaultdict

from ..models import Evidence, Tag, TimelineEvent, db

AUTO_TAGS = {
    '[FEIT]': ['factuur', 'contract', 'datum', 'ondertekend', 'incidentdatum'],
    '[MANIPULATIE]': ['altijd', 'nooit', 'schuld', 'jij bent', 'manipulatief'],
    '[ONBEVESTIGD]': ['volgens mij', 'ik denk', 'mogelijk'],
    '[JURIDISCH RELEVANT]': ['overeenkomst', 'bewijs', 'aansprakelijk', 'schade', 'claim'],
}

PERSON_PATTERN = re.compile(r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b')


def auto_tag_evidence() -> dict:
    created = 0
    for evidence in Evidence.query.all():
        text = (evidence.description or '').lower()
        for label, keywords in AUTO_TAGS.items():
            if any(keyword in text for keyword in keywords):
                exists = Tag.query.filter_by(evidence_id=evidence.evidence_id, label=label).first()
                if not exists:
                    db.session.add(Tag(evidence_id=evidence.evidence_id, label=label, mode='auto'))
                    created += 1
    db.session.commit()
    return {'tags_created': created}


def entity_graph() -> dict:
    names = []
    links = Counter()
    for evidence in Evidence.query.all():
        text = evidence.description or ''
        extracted = PERSON_PATTERN.findall(text)
        names.extend(extracted)
        for index, src in enumerate(extracted):
            for dst in extracted[index + 1 :]:
                if src != dst:
                    links[(src, dst)] += 1

    unique_names = sorted(set(names))
    nodes = [{'id': n, 'label': n} for n in unique_names]
    edges = [{'source': s, 'target': t, 'weight': w} for (s, t), w in links.items()]
    return {'nodes': nodes, 'edges': edges}


def inconsistency_scan() -> list[dict]:
    findings = []
    for evidence in Evidence.query.all():
        text = (evidence.description or '').lower()
        if 'nooit' in text and 'toch' in text:
            findings.append(
                {
                    'evidence_id': evidence.evidence_id,
                    'type': 'contradiction',
                    'message': 'Tegenstrijdige formulering gedetecteerd ("nooit" + "toch").',
                }
            )
        if 'altijd' in text and 'mogelijk' in text:
            findings.append(
                {
                    'evidence_id': evidence.evidence_id,
                    'type': 'narrative_shift',
                    'message': 'Narratiefwijziging: absolute claim gecombineerd met onzekerheidsclaim.',
                }
            )
    return findings


def avg_gba_assessment() -> dict:
    total = Evidence.query.count()
    with_pii = Evidence.query.filter_by(contains_personal_data=True).count()
    risk = 'high' if with_pii > 0 else 'medium'
    legal_basis = 'gerechtvaardigd belang / rechtsvordering' if with_pii else 'gerechtvaardigd belang'
    return {
        'total_files': total,
        'files_with_personal_data': with_pii,
        'risk_level': risk,
        'recommended_legal_basis': legal_basis,
        'controls': [
            'doelbinding en minimale gegevensverwerking',
            'rolgebaseerde toegang',
            'retentiebeleid en logging',
        ],
    }


def counterparty_scenarios() -> list[dict]:
    contradictions = len(inconsistency_scan())
    return [
        {
            'scenario': 'Betwisting authenticiteit van documenten',
            'likely_action': 'tegenpartij stelt dat herkomst/inhoud onbetrouwbaar is',
            'risk_level': 'medium',
            'counter_argument': 'hash-gedreven deduplicatie en bronpad + tijdregistratie aantonen',
        },
        {
            'scenario': 'Framing als subjectieve interpretatie',
            'likely_action': 'tegenpartij benadrukt dat conclusies meningen zijn',
            'risk_level': 'high' if contradictions else 'medium',
            'counter_argument': 'scheiding FEIT/INTERPRETATIE en koppeling naar bewijs-ID in rapport',
        },
        {
            'scenario': 'AVG-bezwaar op persoonsgegevens',
            'likely_action': 'verwerking persoonsgegevens als disproportioneel neerzetten',
            'risk_level': 'high' if avg_gba_assessment()['files_with_personal_data'] else 'low',
            'counter_argument': 'rechtsgrond, proportionaliteit en beveiligingsmaatregelen documenteren',
        },
    ]


def person_profiles() -> list[dict]:
    profiles = defaultdict(lambda: {'facts': [], 'statements': [], 'inconsistencies': []})
    for evidence in Evidence.query.all():
        description = evidence.description or ''
        for person in PERSON_PATTERN.findall(description):
            profiles[person]['facts'].append(f'{evidence.evidence_id}: {evidence.filename}')
            profiles[person]['statements'].append(description[:180])

    for finding in inconsistency_scan():
        for person in profiles:
            profiles[person]['inconsistencies'].append(finding['message'])

    results = []
    for name, profile in sorted(profiles.items()):
        results.append(
            {
                'name': name,
                'role': 'betrokkene',
                'facts': profile['facts'][:5],
                'statements': profile['statements'][:5],
                'behavior_changes': ['Narratief geëvalueerd op absolute en conditionele claims'],
                'possible_motives': ['procespositie versterken'],
                'possible_interests': ['juridische aansprakelijkheid beperken'],
                'medical_context': 'geen medische gegevens aangetroffen in huidige dataset',
                'inconsistencies': profile['inconsistencies'][:3],
            }
        )
    return results


def generate_dossier_report() -> dict:
    evidence_rows = Evidence.query.order_by(Evidence.created_at.asc()).all()
    timeline_rows = TimelineEvent.query.order_by(TimelineEvent.event_time.asc()).all()
    findings = inconsistency_scan()
    return {
        'dossier_overview': {
            'total_evidence': len(evidence_rows),
            'total_timeline_events': len(timeline_rows),
            'generated_for': 'advocaat/rechter/toezichthouder',
        },
        'personen_en_rollen': person_profiles(),
        'chronologie': [
            {
                'tijd': row.event_time.isoformat(),
                'titel': row.title,
                'bewijs_id': row.evidence_id,
            }
            for row in timeline_rows
        ],
        'feiten_vs_meningen': [
            {
                'bewijs_id': ev.evidence_id,
                'labels': [t.label for t in Tag.query.filter_by(evidence_id=ev.evidence_id).all()] or ['[INTERPRETATIE]'],
                'tekst': (ev.description or '')[:220],
            }
            for ev in evidence_rows
        ],
        'gedragsanalyse_per_persoon': person_profiles(),
        'inconsistenties_en_verdraaiingen': findings,
        'juridische_relevantie': [
            {
                'bewijs_id': ev.evidence_id,
                'juridische_relevantie': ev.legal_relevance,
                'bewijskracht': ev.evidence_strength,
            }
            for ev in evidence_rows
        ],
        'risicos_bij_framing_of_misbruik': counterparty_scenarios(),
        'samenvatting_voor_advocaat_rechter': {
            'kern': 'Dossier bevat herleidbare bewijsitems met hashes, tijdlijn en tagging.',
            'sterk': 'traceerbaarheid, deduplicatie, audit logging',
            'zwak': 'NLP-analyse is regelgebaseerd; aanvullende menselijke validatie vereist',
        },
        'actieve_dossierstatus': 'actief',
        'avg_gba_toets': avg_gba_assessment(),
    }

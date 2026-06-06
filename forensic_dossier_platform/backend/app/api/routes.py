from __future__ import annotations

from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from ..models import Evidence, Tag, TimelineEvent, db
from ..services.analysis import (
    auto_tag_evidence,
    avg_gba_assessment,
    counterparty_scenarios,
    entity_graph,
    generate_dossier_report,
    inconsistency_scan,
)
from ..services.exporter import export_case_pdf
from ..services.scanner import scan_directory

api = Blueprint('api', __name__)


@api.get('/health')
def health():
    return jsonify({'status': 'ok'})


@api.post('/scan')
def scan():
    payload = request.get_json(force=True)
    root = payload.get('path', '../sample_data')
    source = payload.get('source', 'local')
    result = scan_directory(root=root, source=source)
    return jsonify(result)


@api.post('/tag/auto')
def tag_auto():
    return jsonify(auto_tag_evidence())


@api.post('/tag/manual')
def tag_manual():
    payload = request.get_json(force=True)
    tag = Tag(evidence_id=payload['evidence_id'], label=payload['label'], mode='manual')
    db.session.add(tag)
    db.session.commit()
    return jsonify({'created': True})


@api.get('/evidence')
def evidence_list():
    query = Evidence.query
    person = request.args.get('person', '').strip().lower()
    evidence_type = request.args.get('type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if evidence_type:
        query = query.filter_by(file_type=evidence_type)
    if date_from:
        query = query.filter(Evidence.created_at >= date_from)
    if date_to:
        query = query.filter(Evidence.created_at <= date_to)

    rows = []
    for ev in query.order_by(Evidence.created_at.desc()).all():
        if person and person not in (ev.description or '').lower():
            continue
        rows.append(
            {
                'evidence_id': ev.evidence_id,
                'filename': ev.filename,
                'type': ev.file_type,
                'date': ev.created_at.isoformat() if ev.created_at else None,
                'description': ev.description,
                'legal_relevance': ev.legal_relevance,
                'evidence_strength': ev.evidence_strength,
                'tags': [t.label for t in Tag.query.filter_by(evidence_id=ev.evidence_id).all()],
            }
        )
    return jsonify(rows)


@api.get('/timeline')
def timeline():
    events = TimelineEvent.query.order_by(TimelineEvent.event_time.asc()).all()
    return jsonify(
        [
            {
                'time': e.event_time.isoformat(),
                'title': e.title,
                'type': e.event_type,
                'evidence_id': e.evidence_id,
                'details': e.details,
            }
            for e in events
        ]
    )


@api.get('/graph')
def graph():
    return jsonify(entity_graph())


@api.get('/analysis/inconsistencies')
def inconsistencies():
    return jsonify(inconsistency_scan())


@api.get('/analysis/scenarios')
def scenarios():
    return jsonify(counterparty_scenarios())


@api.get('/analysis/privacy')
def privacy_assessment():
    return jsonify(avg_gba_assessment())


@api.get('/analysis/report')
def dossier_report():
    return jsonify(generate_dossier_report())


@api.get('/search')
def search():
    term = request.args.get('q', '').lower()
    results = []
    for ev in Evidence.query.all():
        haystack = f'{ev.filename} {(ev.description or "")}'.lower()
        if term in haystack:
            results.append(
                {
                    'evidence_id': ev.evidence_id,
                    'filename': ev.filename,
                    'description': ev.description,
                    'legal_relevance': ev.legal_relevance,
                }
            )
    return jsonify(results)


@api.get('/export/pdf')
def export_pdf():
    binary = export_case_pdf()
    return send_file(
        BytesIO(binary),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='forensisch_rapport.pdf',
    )

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Evidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.String(64), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.Text, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(50), default='local')
    created_at = db.Column(db.DateTime, nullable=True)
    indexed_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, default='')
    legal_relevance = db.Column(db.String(20), default='medium')
    confidence = db.Column(db.String(20), default='medium')
    evidence_strength = db.Column(db.String(20), default='medium')
    contains_personal_data = db.Column(db.Boolean, default=False)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.String(64), nullable=False)
    label = db.Column(db.String(64), nullable=False)
    mode = db.Column(db.String(20), default='manual')


class TimelineEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_time = db.Column(db.DateTime, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, default='')
    evidence_id = db.Column(db.String(64), nullable=True)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    actor = db.Column(db.String(100), default='system')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    payload = db.Column(db.Text, default='')

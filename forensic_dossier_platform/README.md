# Forensisch Dossier Platform

Productiegerichte full-stack webapplicatie voor forensisch dossierbeheer, bewijsanalyse en juridisch inzetbare rapportage.

## Kernfunctionaliteit

- **Volledige bestandsscan (recursief):** PDF, DOCX, TXT, HTML, JSON, CSV, PNG, JPG.
- **Deduplicatie:** SHA-256 op alle bestanden.
- **Bewijsindex:** uniek bewijs-ID, hash, type, bronpad, datum, beschrijving, juridische relevantie, bewijskracht.
- **Tagging:** handmatig + auto-tags (`[FEIT]`, `[MANIPULATIE]`, `[ONBEVESTIGD]`, `[JURIDISCH RELEVANT]`).
- **Tijdlijn-engine:** metadata + inhoudsdatum gecombineerd in één chronologie.
- **Personen & relaties:** naamextractie en relationele edges uit dossiertekst.
- **Forensische analyse:** inconsistenties, narratiefwijziging-signalen en tegenpartij-scenario’s.
- **AVG/GBA-toets:** detectie persoonsgegeven-indicatie + risicoclassificatie + controlemaatregelen.
- **Rapportage:** JSON eindrapport endpoint + PDF export.
- **Audit trail:** scanacties in auditlog.

## Architectuur

```text
forensic_dossier_platform/
  backend/
    app/
      api/routes.py
      services/{scanner,analysis,exporter}.py
      models.py
    run.py
  frontend/
    src/components/*
    src/lib/api.js
  sample_data/
```

## Installatie

### Backend (Flask + SQLite)

```bash
cd forensic_dossier_platform/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Backend URL: `http://localhost:5050`.

### Frontend (React + Tailwind + Vite)

```bash
cd forensic_dossier_platform/frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5175`.

## API-overzicht

- `POST /api/scan` – indexeer bestanden
- `POST /api/tag/auto` – auto-tagging
- `GET /api/evidence` – bewijslijst + filters (`person`, `type`, `date_from`, `date_to`)
- `GET /api/timeline` – tijdlijn
- `GET /api/graph` – personen/relaties
- `GET /api/analysis/inconsistencies` – tegenstrijdigheden
- `GET /api/analysis/scenarios` – tegenpartij-simulator
- `GET /api/analysis/privacy` – AVG/GBA risicobeoordeling
- `GET /api/analysis/report` – volledig juridisch dossierrapport
- `GET /api/search?q=...` – full-text zoekactie
- `GET /api/export/pdf` – PDF export

## Productie-hardening

- OAuth2 integratie voor Google Drive en Gmail (bronconnectoren)
- RBAC + SSO (OIDC/SAML)
- Encryptie at-rest + secrets management
- Asynchrone queue workers voor grote scans
- Ondertekende append-only audit logging

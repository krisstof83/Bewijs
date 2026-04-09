# Auto Forensic OSINT Dossier Platform

## Architectuur
```
osint_app/
  backend/
    core/
      config.py
      logging.py
    engines/
      auto_engine.py
      import_engine.py
      timeline_engine.py
      dossier_engine.py
    services/
      osint_service.py
      dashboard_service.py
      storage_service.py
    models/
      models.py
    connectors/
      duckduckgo.py
      wikipedia.py
      reddit.py
      github_search.py
      openalex.py
    main.py
  frontend/
    index.html
    dashboard.js
    styles.css
  imports/
  data/
```

## Starten
```bash
cd osint_app/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## API
- `GET /dashboard/summary`
- `GET /evidence/list`
- `GET /timeline`
- `POST /osint/search`
- `POST /forensic/command`

## Forensische commando's
`POST /forensic/command` ondersteunt:

- `ANALYSE STARTEN` → volledige scan + bewijsindex + tijdlijn + rapportexport
- `SCENARIO'S TONEN` → scenarioanalyse met tegenpartij-inschatting
- `EINDRAPPORT` → volledige juridisch gestructureerde rapportage

Voorbeeld payload:

```json
{
  "command": "EINDRAPPORT",
  "root_path": "/workspace/Bewijs"
}
```

Rapportartefacten worden automatisch weggeschreven naar `dossiers/reports/`:
- `forensic_report.json`
- `forensic_report.md`

## Automatische pipeline
Bij startup en periodiek:
1. `process_imports()`
2. `build_person_reports()`
3. `build_auto_timeline()`
4. `generate_dashboard_summary()`

De import-engine scant automatisch `imports/pdf`, `imports/gmail` en `imports/drive` met SHA256, duplicate-detectie via state-file, chain-of-custody logging en neutrale tekststructurering.

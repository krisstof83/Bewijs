# OSINT Dossieronderzoek

## Projectstructuur
```
osint_dossier_app/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── dossiers/
│   ├── personen/
│   ├── zaken/
│   └── bewijs/
└── imports/
    ├── pdf/
    ├── gmail/
    └── drive/
└── frontend/
    └── index.html
```

## Lokaal starten
1. Backend:
   ```bash
   cd osint_dossier_app/backend
   python --version
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
2. Frontend:
   ```bash
   cd osint_dossier_app/frontend
   python -m http.server 5173
   ```
3. Open: http://localhost:5173

## Optioneel
- Bing Web Search API: zet `BING_API_KEY` als environment variabele voor live resultaten via Bing.
## Imports
- Plaats bestanden in `imports/pdf`, `imports/gmail`, of `imports/drive` om ze automatisch te laten verwerken en vastleggen als bewijs.

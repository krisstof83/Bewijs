# OSINT Dossier Webapp

## Projectstructuur
```
osint_app/
├── backend/
│   ├── connectors/
│   │   ├── duckduckgo.py
│   │   ├── github_search.py
│   │   ├── openalex.py
│   │   ├── reddit.py
│   │   └── wikipedia.py
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── requirements.txt
│   └── storage.py
├── data/
└── frontend/
    └── index.html
```

## Lokaal starten
1. Backend starten:
   ```bash
   cd osint_app/backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
2. Frontend openen:
   ```bash
   cd osint_app/frontend
   python -m http.server 4173
   ```
   Open daarna `http://localhost:4173` in je browser.

## Belangrijke kenmerken
- Alleen publieke bronnen (DuckDuckGo, Wikipedia, Reddit, GitHub, OpenAlex).
- Juridisch neutrale labels (feit / claim / bron).
- Export naar PDF en JSON via de backend.
- Modulair uitbreidbaar via `backend/connectors/`.

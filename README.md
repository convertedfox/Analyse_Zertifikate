# Analyse Zertifikate – Similarity Dashboard

Streamlit-Dashboard zur Analyse von Zertifikatsähnlichkeiten auf Basis gemeinsamer Module.

## Ziel

Schnell erkennen, welche Zertifikate sich inhaltlich stark überschneiden.

- Datenbasis: `data/Analyse der Zertifikate.xlsx`
- Fokusmenge: 85 Zertifikate aus dem Blatt `Einzelne Zertifikate`
- Metrik: **Jaccard-Ähnlichkeit**

## Datenfluss

1. Excel wird validiert und in ein deterministisches JSON exportiert.
2. Das JSON enthält eine Schema-Version und wird beim Laden strukturell validiert.
3. Streamlit lädt JSON gecached via `st.cache_data`; Änderungen invalidieren den Cache.
4. Für den gewählten Typfilter (`CAS`, `DAS`, `CAS+DAS`) wird die Matrix berechnet.
5. Die klickbare Heatmap zeigt Jaccard-Werte; darunter folgt der Modulvergleich.

## Setup

```bash
uv sync
```

## JSON erzeugen / prüfen

```bash
uv run python scripts/export_certificates.py --check
uv run python scripts/export_certificates.py
```

Erzeugt: `data/certificates.json`. `--check` schlägt fehl, wenn das JSON fehlt oder nicht mehr
dem Excel-Inhalt entspricht.

## Bedienung

- Typfilter steuert, ob CAS-, DAS- oder vereinigte Modulsets verglichen werden.
- Mindestähnlichkeit blendet schwächere Paare aus der Top-Liste aus.
- Ein Klick in die Heatmap oder eine Auswahl aus den Top 20 aktualisiert den Modulvergleich.

## App starten

```bash
uv run streamlit run streamlit_app.py
```

## Qualitätschecks

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest
```

## Deployment (Streamlit Community Cloud)

- Repository: `https://github.com/convertedfox/Analyse_Zertifikate.git`
- Entry point: `streamlit_app.py`
- Vor Deployment: JSON aktualisieren und Tests grün laufen lassen.

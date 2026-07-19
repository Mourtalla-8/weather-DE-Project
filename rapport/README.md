# Dossier rapport — Weather Data Platform

Livrables documentaires du **Groupe A — ForceN**.

## Livrables principaux

| Fichier | Description |
|---|---|
| [**groupe_a_projet_final.pdf**](groupe_a_projet_final.pdf) | **Rapport final** du projet |
| [**presentation_groupe_a_final.pptx**](presentation_groupe_a_final.pptx) | **Présentation finale** du projet |

## Documentation technique

| Fichier | Description |
|---|---|
| [docs/nifi-ingestion.md](docs/nifi-ingestion.md) | Guide NiFi pas à pas |
| [exports/database/README.md](exports/database/README.md) | Export / restauration MongoDB |
| [marp/](marp/README.md) | Source Marp (régénération présentation) |
| [../analysis/README.md](../analysis/README.md) | Guide analyse (EDA, ML, Streamlit) |

---

## Structure

```
rapport/
├── README.md
├── groupe_a_projet_final.pdf          # Rapport final
├── presentation_groupe_a_final.pptx     # Présentation finale
├── docs/
│   └── nifi-ingestion.md
├── assets/
│   ├── nifi/                          # Captures NiFi
│   ├── minio/                         # Captures MinIO
│   ├── diagrams/                      # Diagrammes architecture
│   └── Ana-BI-ML/                     # Figures analyse finales
├── exports/
│   ├── export_assets.sh               # Export CSV + mongodump
│   ├── data/                          # CSV exportés (gitignored)
│   └── database/                      # Dump MongoDB (gitignored)
└── marp/
    ├── slides.md
    └── export.sh
```

---

## Générer les exports localement

```bash
python scripts/setup.py --with-analysis
python scripts/run_pipeline.py
bash rapport/exports/export_assets.sh
```

---

## Présentation Marp (source)

```bash
cd rapport/marp
bash export.sh
```

---

*Groupe A — ForceN.*

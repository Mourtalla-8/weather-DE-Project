# Dossier rapport ETL

Livrable documentaire de l'équipe **Data Engineering - ForceN, Groupe A**.

Ce dossier regroupe la documentation, les captures d'écran, les datasets et le dump MongoDB du projet Weather ETL. Il est conçu pour la **passation** vers l'équipe Analyse / EDA / ML / BI.

---

## Documents

| Fichier | Description                                                       |
|---|-------------------------------------------------------------------|
| [**rapport.md**](rapport.md) | Rapport principal - architecture, pipeline, qualité, livrables    |
| [**nifi-ingestion.md**](nifi-ingestion.md) | Guide NiFi pas à pas - Controller Service, processeurs, dépannage |
| [**database/README.md**](database/README.md) | Export et restauration du dump MongoDB                            |
| [**presentation/**](presentation/README.md) | Support de presentation (Marp) exportable en PowerPoint / PDF     |

---

## Structure

```
rapport/
├── README.md                 # Ce fichier
├── rapport.md                # Rapport principal
├── nifi-ingestion.md         # Guide ingestion NiFi
├── data/
│   ├── raw/                  # weatherHistory.csv (gitignored)
│   └── processed/            # weather_processed.csv (gitignored)
├── database/
│   ├── README.md             # Instructions mongorestore
│   └── dump/                 # mongodump weather_dwh (gitignored)
├── presentation/
│   ├── README.md             # Instructions export .pptx / .pdf
│   ├── slides.md             # Source Marp (16 slides)
│   └── export.sh             # marp slides.md --pptx
├── media/
│   ├── nifi/                 # 11 captures NiFi
│   ├── minio/                # 2 captures MinIO
│   └── diagrams/             # Diagrammes exportés (PNG)
└── scripts/
    └── export_assets.sh      # Export CSV + mongodump
```

---

## Générer les assets localement

Les CSV et le dump MongoDB sont **exclus du Git** (fichiers volumineux). Pour les produire :

```bash
# Depuis la racine du projet

# 1. Environnement et pipeline
python scripts/setup.py
python scripts/run_pipeline.py

# 2. Copie CSV + mongodump vers rapport/
bash rapport/scripts/export_assets.sh
```

### Prérequis

| Prérequis | Vérification |
|---|---|
| Docker + stack démarrée | `docker compose ps` |
| Pipeline exécuté au moins une fois | CSV dans `data/raw/` et `data/processed/` |
| `mongodump` installé | `mongodump --version` (paquet `mongodb-tools`) |
| Fichier `.env` | Credentials MongoDB alignés avec Docker |

---

## Restaurer MongoDB

Voir [database/README.md](database/README.md) pour les commandes `mongorestore` et la vérification du nombre de documents (96 429 attendus).

---

## Présentation

Un support de présentation est fourni sous forme de slides **Marp** versionnées :

```bash
cd rapport/presentation
bash export.sh          # génère presentation.pptx + presentation.pdf
```

Voir [presentation/README.md](presentation/README.md) (prérequis Marp CLI).

---

## Lecture recommandée

1. [rapport.md](rapport.md) - vue d'ensemble du projet
2. [nifi-ingestion.md](nifi-ingestion.md) - si vous devez reconfigurer NiFi
3. [database/README.md](database/README.md) - si vous importez le dump sans relancer le pipeline

---

*Équipe Data Engineering - ForceN, Groupe A.*

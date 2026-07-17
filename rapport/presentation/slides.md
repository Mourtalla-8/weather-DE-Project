---
marp: true
theme: default
paginate: true
size: 16:9
header: 'Weather ETL Platform — ForceN Groupe A'
footer: 'Data Engineering — ForceN, Groupe A · Juillet 2026'
style: |
  section {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 26px;
    color: #1f2933;
    background: #ffffff;
    padding: 60px 70px;
  }
  h1 {
    color: #14532d;
    font-size: 46px;
  }
  h2 {
    color: #166534;
    border-bottom: 3px solid #22c55e;
    padding-bottom: 8px;
  }
  section.lead {
    background: linear-gradient(135deg, #14532d 0%, #166534 60%, #22c55e 100%);
    color: #ffffff;
    justify-content: center;
    text-align: center;
  }
  section.lead h1 { color: #ffffff; font-size: 54px; }
  section.lead h2 { color: #d1fae5; border: none; }
  table { font-size: 22px; }
  th { background: #dcfce7; color: #14532d; }
  code { background: #f1f5f9; color: #b91c1c; }
  header { color: #64748b; font-size: 14px; }
  footer { color: #94a3b8; font-size: 13px; }
  .metric { color: #166534; font-weight: 700; }
  img { background: #ffffff; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# Weather ETL Platform

## Pipeline Extract · Transform · Load

**Data Engineering — ForceN, Groupe A**
Équipe ETL

Juillet 2026

---

## Contexte et objectifs

Transformer un dataset météo brut (Kaggle) en données exploitables pour l'équipe **Analyse / EDA / ML / BI**.

| En scope | Hors scope |
|---|---|
| Extraction et stockage raw (MinIO) | Modèles ML, dashboards BI |
| Nettoyage et normalisation | Déploiement cloud production |
| Chargement MongoDB (`weather_dwh`) | NiFi pour la transformation |
| Automatisation et documentation | |

> Objectif : un pipeline **reproductible, documenté et prêt à la passation**.

---

## Architecture globale

![w:1000 Architecture ETL du pipeline Weather](../media/diagrams/architecture-etl.png)

**Extract** → **Ingestion MinIO** → **Transform** → **Load MongoDB** → Équipe Analyse

---

## Stack Docker

Trois services orchestrés par `docker-compose.yml` :

| Service | Image | Port(s) | Rôle |
|---|---|---|---|
| **MongoDB** | `mongo:latest` | 27017 | Data Warehouse |
| **MinIO** | `minio/minio` | 9000 / 9001 | Data Lake (S3) |
| **NiFi** | `apache/nifi` | 8443 | Orchestration ingestion |

Démarrage en une commande : `python scripts/setup.py`

---

## Extract — récupération du dataset

**Script** : `etl/extract.py` (via `kagglehub`)

```python
src = kagglehub.dataset_download("muthuj7/weather-dataset")
shutil.copytree(src, Path("./data/raw"), dirs_exist_ok=True)
```

| Métrique | Valeur |
|---|---|
| Source | Kaggle — `muthuj7/weather-dataset` |
| Fichier | `weatherHistory.csv` |
| Lignes brutes | <span class="metric">96 453</span> · 12 colonnes |

---

## Ingestion vers MinIO

Deux voies écrivent le CSV brut dans le bucket `weather-lake` :

| Mécanisme | Usage | Destination |
|---|---|---|
| **NiFi** `GetFile` → `PutS3Object` | Démonstration orchestration | `weather-lake/raw/` |
| **Python** `upload_raw_to_minio` | Pipeline automatisé | idem |

![w:850 Flux d'ingestion NiFi vers MinIO](../media/diagrams/flux-nifi-ingestion.png)

---

## NiFi — Process Group Ingestion

Controller Service `AWSCredentialsProviderControllerService` + processeur `PutS3Object`.

![w:560](../media/nifi/config_awsCPS.png) ![w:560](../media/nifi/select_awsCPS_propety_for_PutS3Object.png)

Guide pas à pas complet : `rapport/nifi-ingestion.md`

---

## Transform — nettoyage et qualité

**Script** : `etl/transform.py` (pandas)

- Normalisation snake_case + parsing dates UTC
- Suppression doublons et lignes sans mesures essentielles
- Imputation manquants (interpolation temporelle + médiane)
- Pression ≤ 0 → NaN puis imputation · suppression `loud_cover`

| Métrique | Raw | Clean |
|---|---|---|
| Lignes | 96 453 | <span class="metric">96 429</span> |
| `precip_type` manquant | 517 | 0 |
| Pression invalide | 1 288 | 0 |

---

## Load — Data Warehouse MongoDB

**Script** : `etl/load.py` (pymongo)

| Élément | Valeur |
|---|---|
| Base / Collection | `weather_dwh` / `weather_observations` |
| Documents chargés | <span class="metric">96 429</span> |
| Mode | Remplacement complet (pas de doublons) |
| Index | `date_time` (unique), `precip_type` |

Restauration fournie via `mongodump` / `mongorestore`.

---

## MinIO — Data Lake

Deux buckets séparent zone raw et zone curated :

![w:520 Bucket weather-lake](../media/minio/Bucket_weather-lake.png) ![w:520 Bucket weather-processed](../media/minio/Budcket_weather-processed.png)

`weather-lake` (raw) · `weather-processed` (CSV, Parquet, metadata)

---

## Automatisation

| Script | Rôle |
|---|---|
| `scripts/setup.py` | `.env`, venv, Docker, attente services |
| `scripts/run_pipeline.py` | Pipeline 4 étapes (extract → upload → transform → load) |
| `scripts/reset.py` | Remise à zéro |
| `rapport/scripts/export_assets.sh` | Export CSV + `mongodump` |

Protection par **fichier lock** et **vérification TCP** des ports avant exécution.

---

## Qualité des données

Mapping raw → processed (extrait) et règles appliquées :

| Raw | Processed |
|---|---|
| `Formatted Date` | `date_time` |
| `Temperature (C)` | `temperature_c` |
| `Wind Speed (km/h)` | `wind_speed_km_per_h` |
| `Loud Cover` | *(supprimée — constante)* |

- Lignes sans température / humidité → supprimées
- `precip_type` null → `unknown` + normalisation minuscules

---

## Livrables et passation

| Livrable | Format |
|---|---|
| Dataset nettoyé | CSV (`weather_processed.csv`) |
| Dataset brut | CSV (`weatherHistory.csv`) |
| Dump MongoDB | BSON (`mongodump`) |
| Code + infra | GitHub + Docker |

Deux options pour l'équipe Analyse : **clone GitHub** (reproductible) ou **archive `rapport/`** (résultats finaux).

---

## Difficultés rencontrées

| Problème | Solution |
|---|---|
| Permissions `data/` (root Docker) | Lock déplacé + reset via conteneur Alpine |
| MinIO port 9000 refusé | Vérification TCP explicite avant exécution |
| Mot de passe MongoDB avec `@` | Encodage `quote_plus` dans `load.py` |
| Controller Service absent de l'export NiFi | Procédure manuelle documentée |

---

## Conclusion et perspectives

Un pipeline ETL **complet, documenté et reproductible** :

| Étape | Résultat |
|---|---|
| Extract | 96 453 lignes raw |
| Ingestion | `weather-lake/raw/` |
| Transform | 96 429 lignes clean |
| Load | 96 429 documents indexés |

**Perspectives** : orchestration Airflow/Prefect, monitoring NiFi, partitionnement Parquet, déploiement cloud (S3 + Atlas).

---

<!-- _class: lead -->
<!-- _paginate: false -->

# Merci

## Questions & réponses

Dépôt : `github.com/Mourtalla-8/weather-DE-Project`
Rapport complet : `rapport/rapport.md`

**Équipe Data Engineering — ForceN, Groupe A**

# Analyse — Weather Data Platform

Travail **Analyse / EDA / ML / BI** intégré au dépôt Groupe A.

## Source des données (ETL)

Toute l’analyse lit le **même dataset enrichi** produit par `etl/transform.py` :

| Priorité | Emplacement | Détail |
|---|---|---|
| 1 | `data/processed/weather_processed_enriched.csv` | Copie locale après transform |
| 2 | MinIO `weather-processed/weather_processed_enriched.csv` | Téléchargé automatiquement si le local manque |

La résolution est centralisée dans [`paths.py`](paths.py) via `ensure_enriched_csv()`.  
MongoDB (`weather_dwh.weather_observations`) contient le CSV **clean** (11 colonnes) ; EDA / ML / BI utilisent la version **enrichie** (17 colonnes).

**Prérequis** : exécuter le pipeline ETL au moins une fois :

```bash
python scripts/setup.py --with-analysis
python scripts/run_pipeline.py
```

## Schéma du dataset enrichi (17 colonnes)

| Colonne | Type | Description |
|---|---|---|
| `date_time` | datetime | Horodatage de l'observation |
| `date` | date | Date seule |
| `summary` | string | Résumé météo court |
| `daily_summary` | string | Résumé journalier |
| `precip_type` | string | `rain`, `snow` ou `unknown` |
| `temperature_c` | float | Température (°C) |
| `apparent_temperature_c` | float | Température ressentie (°C) |
| `humidity` | float | Humidité (0–1) |
| `wind_speed_km_per_h` | float | Vitesse du vent (km/h) |
| `wind_bearing_degrees` | float | Direction du vent (°) |
| `visibility_km` | float | Visibilité (km) |
| `pressure_millibars` | float | Pression (mb) |
| `year`, `month`, `day`, `hour`, `day_of_week` | int | Features temporelles (ETL) |

Variable dérivée en analyse : `season` (Hiver / Printemps / Été / Automne).

## Commandes

### Orchestrateur

```bash
python scripts/run_analysis.py   # vérifie les données ETL + ML
```

### EDA statistique

```bash
jupyter notebook analysis/eda/EDA_Analyse_Statistique.ipynb
```

Figures dans `outputs/eda/` : `fig_univariee.png`, `fig_boxplots.png`, etc.

### Machine Learning

```bash
python analysis/ml/train_predict.py
```

Métriques attendues : MAE ≈ 0.56 °C, R² ≈ 0.993 → `outputs/ml/fig1_historique_complet.png`

### Dashboard BI (Streamlit)

```bash
streamlit run analysis/bi/app.py
```

## Configuration

| Variable | Défaut |
|---|---|
| `WEATHER_ENRICHED_CSV` | `data/processed/weather_processed_enriched.csv` |

## Figures de présentation

Assets finaux : [`rapport/assets/Ana-BI-ML/`](../rapport/assets/Ana-BI-ML/).  
`outputs/` est régénérable et non versionné.

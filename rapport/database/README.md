# Dump MongoDB — `weather_dwh`

Instructions pour exporter et restaurer la base MongoDB produite par le pipeline ETL.

---

## Contenu attendu

| Élément | Valeur |
|---|---|
| Base | `weather_dwh` |
| Collection | `weather_observations` |
| Documents | **96 429** |
| Index | `idx_date_time_unique` (unique), `idx_precip_type` (standard) |

Le dossier `dump/` est généré **localement** et exclu du Git (voir `.gitignore` à la racine du projet).

---

## Générer le dump

Depuis la **racine du projet**, avec MongoDB démarré et le pipeline exécuté :

```bash
python scripts/run_pipeline.py          # si pas déjà fait
bash rapport/scripts/export_assets.sh   # copie CSV + mongodump
```

Le script lit `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_HOST`, `MONGO_PORT` et `MONGO_DB` depuis `.env`.

### Prérequis

- Conteneur MongoDB actif (`docker compose ps`)
- Paquet `mongodb-tools` (`mongodump`, `mongorestore`)
- Collection peuplée (étape Load du pipeline)

Structure produite :

```
rapport/database/dump/
└── weather_dwh/
    ├── weather_observations.bson
    ├── weather_observations.metadata.json
    └── prelude.json
```

---

## Restaurer le dump

### Sans authentification

```bash
mongorestore --drop rapport/database/dump/
```

### Avec authentification (configuration par défaut du projet)

```bash
mongorestore \
  --uri="mongodb://groupea_de:ForceN-GroupeA-Mongo@localhost:27017/?authSource=admin" \
  --drop \
  rapport/database/dump/
```

Remplacez user/mot de passe par vos valeurs `.env` si différentes.

> **Mot de passe avec caractères spéciaux** (`@`, `#`, etc.) : encodez-les dans l'URI ou utilisez `--username` / `--password` séparément.

---

## Vérification après restore

```bash
mongosh --eval 'db.getSiblingDB("weather_dwh").weather_observations.countDocuments()'
```

Résultat attendu : **96429**

Contrôle des index :

```bash
mongosh --eval 'db.getSiblingDB("weather_dwh").weather_observations.getIndexes()'
```

---

## Dépannage

| Erreur | Action |
|---|---|
| `Authentication failed` | Vérifier `MONGO_USER` / `MONGO_PASSWORD` dans `.env` |
| Dossier `dump/` vide | Relancer `export_assets.sh` après un pipeline réussi |
| `mongodump: command not found` | Installer `mongodb-tools` (Arch : `pacman -S mongodb-tools`) |
| Count ≠ 96429 | Relancer `python etl/load.py` puis ré-exporter |

---

*Équipe Data Engineering — ForceN, Groupe A.*

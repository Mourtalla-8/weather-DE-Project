# Présentation — Weather ETL Platform

Support de présentation du projet au format **Marp**.
La source `slides.md` est versionnée dans Git ; les exports `.pptx` / `.pdf` sont régénérables et **gitignored**.

---

## Contenu

| Fichier | Description |
|---|---|
| `slides.md` | Source Marp — 16 slides, thème pro (vert/gris), français |
| `export.sh` | Script d'export vers `.pptx` / `.pdf` |
| `presentation.pptx` | Export PowerPoint (généré, non versionné) |
| `presentation.pdf` | Export PDF (généré, non versionné) |

Les images proviennent de `rapport/media/` (captures NiFi/MinIO et diagrammes) via des chemins relatifs (`../media/...`).

---

## Prérequis — Marp CLI

Installation globale (recommandée) :

```bash
npm install -g @marp-team/marp-cli
marp --version
```

Sans installation globale, `export.sh` bascule automatiquement sur `npx @marp-team/marp-cli`.

> L'export `.pptx` / `.pdf` télécharge une instance Chromium via Marp au premier lancement.
> Prévoir une connexion internet la première fois.

---

## Générer la présentation

```bash
cd rapport/presentation

bash export.sh          # presentation.pptx + presentation.pdf
bash export.sh pptx     # uniquement PowerPoint
bash export.sh pdf      # uniquement PDF
```

L'option `--allow-local-files` est nécessaire pour intégrer les images locales dans l'export.

---

## Prévisualiser / éditer

- **VS Code** : extension *Marp for VS Code* → aperçu en direct de `slides.md`.
- **CLI (serveur live)** :

  ```bash
  marp -s slides.md     # http://localhost:8080 avec rechargement auto
  ```

Chaque slide est séparée par `---`. Le thème et les styles sont définis dans le front-matter YAML en tête de `slides.md`.

---

*Équipe Data Engineering — ForceN, Groupe A.*

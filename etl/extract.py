import kagglehub
import shutil
from pathlib import Path

# Télécharge le dataset public via kagglehub (aucune variable .env requise).
src = kagglehub.dataset_download("muthuj7/weather-dataset")

dst = Path("./data/raw")
dst.mkdir(parents=True, exist_ok=True)

shutil.copytree(src, dst, dirs_exist_ok=True)

print(f"Dataset disponible dans {dst}")




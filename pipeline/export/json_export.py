import json
import pandas as pd
from pathlib import Path


def to_chart_json(df, date_format="%Y-%m-%d"):
    """Transforme un DataFrame en dictionnaire pret pour Chart.js.

    date_format : format des etiquettes de l'axe X.
      - "%Y-%m-%d" (defaut) pour des donnees journalieres (gaz, petrole)
      - "%Y-%m-%d %H:%M" pour des donnees intra-journalieres (electricite 15 min)
    Convertit les NaN en None (null en JSON) pour rester valide.
    """
    return {
        "dates": [d.strftime(date_format) for d in df.index],
        "series": {
            col: [None if pd.isna(v) else v for v in df[col].round(3)]
            for col in df.columns
        },
    }


def save_json(data, filename):
    """Ecrit le dictionnaire dans data/<filename> a la racine du projet."""
    project_root = Path(__file__).resolve().parents[2]
    output_path = project_root / "data" / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Ecrit : {output_path}")
import os
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
import pandas as pd

# 1. Charge la cle depuis .env
load_dotenv()
api_key = os.getenv("ENTSOE_API_KEY")

if not api_key:
    print("Cle ENTSO-E introuvable — verifie la ligne ENTSOE_API_KEY dans .env")
    exit()

# 2. Cree le client ENTSO-E
client = EntsoePandasClient(api_key=api_key)

# 3. Fenetre de dates (timestamps AVEC fuseau horaire, obligatoire)
start = pd.Timestamp("2026-09-14", tz="Europe/Brussels")
end = pd.Timestamp("2026-09-17", tz="Europe/Brussels")

# 4. Prix day-ahead pour la France et l'Allemagne-Luxembourg
zones = {
    "France (FR)": "FR",
    "Allemagne-Luxembourg (DE_LU)": "DE_LU",
}

for nom, code in zones.items():
    print(f"\n=== {nom} ===")
    prix = client.query_day_ahead_prices(code, start=start, end=end)
    print(f"Nombre de points : {len(prix)}")
    print(prix.head())
import os
from dotenv import load_dotenv
from fredapi import Fred

# 1. Charge le contenu du fichier .env dans l'environnement
load_dotenv()

# 2. Recupere la cle par son nom (jamais ecrite en dur ici)
api_key = os.getenv("FRED_API_KEY")

# 3. Verifie qu'on a bien trouve une cle avant d'aller plus loin
if not api_key:
    print("Cle FRED introuvable — verifie la ligne FRED_API_KEY dans .env")
    exit()

# 4. Cree le client FRED avec la cle
fred = Fred(api_key=api_key)

# Deux series petrole : Brent (Europe) et WTI (US)
series = {
    "Brent (DCOILBRENTEU)": "DCOILBRENTEU",
    "WTI (DCOILWTICO)": "DCOILWTICO",
}

for nom, code in series.items():
    print(f"\n=== {nom} ===")
    data = fred.get_series(code)   # renvoie une Series pandas (index = dates)
    print(data.tail())             # les 5 dernieres valeurs
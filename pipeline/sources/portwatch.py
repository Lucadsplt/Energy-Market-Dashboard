import pandas as pd
import requests

# Donnees publiques du FMI (IMF PortWatch) : passages quotidiens de navires par detroit
URL = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/"
       "Daily_Chokepoints_Data/FeatureServer/0/query")

# nom dans la base du FMI -> nom affiche sur le site
DETROITS = {
    "Strait of Hormuz": "Détroit d'Ormuz",
    "Bab el-Mandeb Strait": "Bab el-Mandeb",
    "Suez Canal": "Canal de Suez",
    "Malacca Strait": "Malacca",
    "Cape of Good Hope": "Cap de Bonne-Espérance",
    "Bosporus Strait": "Bosphore",
}

PAGE = 1000    # le serveur renvoie au maximum 1000 lignes par requete


def fetch_tankers(nom_anglais, depuis="2025-01-01"):
    """Nombre de petroliers par jour dans un detroit, depuis une date (pagination incluse)."""
    lignes, decalage = [], 0
    while True:
        params = {
            "where": f"portname = '{nom_anglais}' AND date >= timestamp '{depuis} 00:00:00'",
            "outFields": "date,n_tanker",
            "orderByFields": "date ASC",
            "resultRecordCount": PAGE,
            "resultOffset": decalage,
            "f": "json",
        }
        reponse = requests.get(URL, params=params, timeout=60)
        reponse.raise_for_status()
        morceau = [f["attributes"] for f in reponse.json()["features"]]
        lignes += morceau
        if len(morceau) < PAGE:
            break
        decalage += PAGE

    dates = [pd.to_datetime(l["date"], unit="ms") if isinstance(l["date"], (int, float)) else pd.to_datetime(l["date"])
             for l in lignes]
    return pd.Series([l["n_tanker"] for l in lignes], index=pd.DatetimeIndex(dates).normalize(),
                     name=nom_anglais, dtype=float)


def fetch_all_detroits(depuis="2025-01-01"):
    """Un DataFrame : une colonne par detroit, indexe par jour."""
    return pd.DataFrame({nom: fetch_tankers(nom, depuis) for nom in DETROITS})


if __name__ == "__main__":
    df = fetch_all_detroits()
    print(df.shape, df.index[0].date(), "->", df.index[-1].date())
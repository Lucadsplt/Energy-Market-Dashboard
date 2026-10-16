"""Construit les donnees de reference GNL a partir du jeu de donnees LNG-T3.

Source : Zhou et al., "Global Marine LNG Terminals, Tankers & Trade (LNG-T3)",
Scientific Data (2026), Zenodo, DOI 10.5281/zenodo.19571058, licence CC BY 4.0.

Usage (une fois, ou pour mettre a jour) :
  1. telecharger LNG_tanker.csv et LNG_terminal.csv depuis https://zenodo.org/records/19571058
  2. python pipeline/reference/construire_lng.py <dossier des deux fichiers CSV>

Produit :
  - pipeline/reference/lng_flotte.json : flotte de methaniers (lue par le releve AIS, pas servie au site)
  - data/lng_terminaux.json            : terminaux GNL (lus par la carte)
"""
import json
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[2]
SOURCE = ("Zhou et al., LNG-T3 : Global Marine LNG Terminals, Tankers & Trade, "
          "Scientific Data (2026), DOI 10.5281/zenodo.19571058, CC BY 4.0")

CLASSES = {                                  # noms courts pour la carte
    "Large Conventional LNG Carriers": "Grand méthanier",
    "Standard  Conventional LNG Carriers": "Méthanier standard",
    "Q-Flex": "Q-Flex",
    "Q-Max": "Q-Max",
    "Small LNG Carriers": "Petit méthanier",
}
STATUTS_GARDES = ["operating", "construction", "idle"]    # on laisse de cote les projets et les sites fermes


def construire(dossier):
    navires = pd.read_csv(dossier / "LNG_tanker.csv")
    terminaux = pd.read_csv(dossier / "LNG_terminal.csv")

    # --- flotte : tous les navires deja livres (les commandes de 2027 n'ont pas d'AIS)
    navires = navires[navires["built_year"] <= 2026]
    par_imo, mmsi_vers_imo = {}, {}
    for _, n in navires.iterrows():
        imo = str(int(n["IMO"]))
        par_imo[imo] = [
            str(n["ship_name"]).strip(),
            int(n["capacity_final"]) if pd.notna(n["capacity_final"]) else None,
            int(n["built_year"]),
            CLASSES.get(n["tanker_class"], str(n["tanker_class"]).strip()),
        ]
        if pd.notna(n["MMSI"]):
            mmsi_vers_imo[str(int(n["MMSI"]))] = imo
    flotte = {"source": SOURCE, "champs": ["nom", "capacite_m3", "annee", "classe"],
              "par_imo": par_imo, "mmsi_vers_imo": mmsi_vers_imo}
    (RACINE / "pipeline" / "reference" / "lng_flotte.json").write_text(
        json.dumps(flotte, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # --- terminaux : operationnels, en construction ou a l'arret
    terminaux = terminaux[terminaux["status"].isin(STATUTS_GARDES)]
    liste = [{
        "nom": t["name"], "type": t["terminal_type"], "statut": t["status"],
        "capacite_mtpa": round(float(t["capacity"]), 2) if pd.notna(t["capacity"]) else None,
        "pays": t["areas"], "region": t["region"],
        "annee": int(t["start_year"]) if pd.notna(t["start_year"]) else None,
        "lat": round(float(t["lat"]), 4), "lon": round(float(t["lon"]), 4),
    } for _, t in terminaux.iterrows()]
    (RACINE / "data" / "lng_terminaux.json").write_text(
        json.dumps({"source": SOURCE, "terminaux": liste}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"Flotte : {len(par_imo)} methaniers ({len(mmsi_vers_imo)} avec MMSI) | Terminaux : {len(liste)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage : python pipeline/reference/construire_lng.py <dossier des CSV>")
    construire(Path(sys.argv[1]))

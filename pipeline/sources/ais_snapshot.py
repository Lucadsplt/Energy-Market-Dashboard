import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets
from dotenv import load_dotenv

load_dotenv()

URL = "wss://stream.aisstream.io/v0/stream"
DUREE = int(os.getenv("AIS_DUREE_S", "120"))   # secondes d'ecoute du flux (120 par defaut)
RACINE = Path(__file__).resolve().parents[2]
CACHE = RACINE / ".cache" / "ais_static.json"      # memoire des navires deja identifies (hors git)
SORTIE = RACINE / "live" / "tankers.json"          # releve publie sur la branche live-data (hors main)
REF_FLOTTE = RACINE / "pipeline" / "reference" / "lng_flotte.json"   # flotte de methaniers (LNG-T3, CC BY 4.0)

# Zones suivies : [[lat_min, lon_min], [lat_max, lon_max]], d'apres le test de couverture
ZONES = {
    "mer_du_nord": {"nom": "Mer du Nord · Manche", "bbox": [[48.8, -5.5], [60.5, 9.0]], "couverture": "excellente"},
    "golfe_mexique": {"nom": "Golfe du Mexique · Houston", "bbox": [[26.0, -97.5], [30.5, -88.0]], "couverture": "moyenne"},
    "gibraltar": {"nom": "Gibraltar", "bbox": [[35.6, -6.5], [36.4, -4.8]], "couverture": "faible"},
    "detroits_danois": {"nom": "Détroits danois · sortie Baltique", "bbox": [[54.8, 9.5], [58.2, 13.2]], "couverture": "bonne"},
    "egee": {"nom": "Pirée · Égée", "bbox": [[37.4, 23.3], [38.2, 24.2]], "couverture": "moyenne"},
    "norvege_ouest": {"nom": "Norvège ouest · Mongstad", "bbox": [[59.5, 4.0], [61.2, 6.0]], "couverture": "faible"},
    "sicile": {"nom": "Sicile · Augusta", "bbox": [[36.8, 14.5], [38.5, 16.0]], "couverture": "faible"},
}
VIEUX = 30 * 24 * 3600          # on oublie les navires non vus depuis 30 jours
A_L_ANCRE = 0.5                 # noeuds : en dessous, le navire est considere a l'arret


def zone_de(lat, lon):
    for cle, z in ZONES.items():
        (a, b), (c, d) = z["bbox"]
        if a <= lat <= c and b <= lon <= d:
            return cle
    return None


def propre(texte):
    """Les champs texte AIS sont completes par des '@' et des espaces."""
    return (texte or "").replace("@", " ").strip()


def charger_flotte():
    """Flotte de methaniers connue : permet de reconnaitre un methanier par son MMSI ou son IMO."""
    try:
        f = json.loads(REF_FLOTTE.read_text(encoding="utf-8"))
        return f["par_imo"], f["mmsi_vers_imo"]
    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}


def charger_cache():
    try:
        memoire = json.loads(CACHE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    limite = time.time() - VIEUX
    return {k: v for k, v in memoire.items() if v.get("vu", 0) > limite}


async def ecouter(cle_api):
    positions, statiques = {}, {}
    debut = time.time()

    async with websockets.connect(URL, max_size=None, ping_interval=None) as ws:
        await ws.send(json.dumps({
            "APIKey": cle_api,
            "BoundingBoxes": [z["bbox"] for z in ZONES.values()],
            "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
        }))
        while time.time() - debut < DUREE:
            try:
                brut = await asyncio.wait_for(ws.recv(), timeout=DUREE - (time.time() - debut) + 1)
            except asyncio.TimeoutError:
                break
            except (websockets.ConnectionClosed, OSError) as erreur:
                # connexion coupee : on garde ce qui a ete recu jusque-la
                print(f"Connexion interrompue apres {time.time() - debut:.0f} s ({type(erreur).__name__}) : donnees partielles conservees.")
                break
            m = json.loads(brut)
            if "error" in m or "Error" in m:
                raise RuntimeError("Erreur du serveur AISStream : " + str(m)[:200])

            meta = m.get("MetaData", {})
            mmsi = str(meta.get("MMSI"))
            if m.get("MessageType") == "PositionReport":
                p = m["Message"]["PositionReport"]
                positions[mmsi] = {
                    "lat": meta["latitude"], "lon": meta["longitude"],
                    "sog": p.get("Sog"), "cog": p.get("Cog"),
                    "nom": propre(meta.get("ShipName")),
                }
            elif m.get("MessageType") == "ShipStaticData":
                s = m["Message"]["ShipStaticData"]
                d = s.get("Dimension") or {}
                statiques[mmsi] = {
                    "type": s.get("Type"), "imo": s.get("ImoNumber"),
                    "nom": propre(s.get("Name")) or propre(meta.get("ShipName")),
                    "destination": propre(s.get("Destination")),
                    "tirant_eau": s.get("MaximumStaticDraught"),
                    "longueur": (d.get("A") or 0) + (d.get("B") or 0),
                    "vu": time.time(),
                }
    if not positions:
        raise RuntimeError("Aucune position recue : rien a publier.")
    return positions, statiques


def construire(positions, memoire, flotte):
    """Croise les positions recues avec ce que l'on sait de chaque navire (flotte GNL, type, destination...)."""
    par_imo, mmsi_vers_imo = flotte
    zones = {cle: {"navires": 0, "petroliers": 0, "methaniers": 0, "a_l_ancre": 0, "methaniers_arret": 0,
                   "identifies": 0} for cle in ZONES}
    petroliers, methaniers, inconnus = [], [], []

    for mmsi, p in positions.items():
        cle = zone_de(p["lat"], p["lon"])
        if cle is None:
            continue
        z = zones[cle]
        z["navires"] += 1
        info = memoire.get(mmsi) or {}
        arret = (p["sog"] or 0) < A_L_ANCRE

        # 1. methanier : son MMSI (ou son IMO, s'il est connu) figure dans la flotte GNL
        imo = mmsi_vers_imo.get(mmsi) or (str(info["imo"]) if info.get("imo") else None)
        fiche = par_imo.get(imo) if imo else None
        if fiche:
            z["identifies"] += 1
            z["methaniers"] += 1
            z["methaniers_arret"] += arret
            methaniers.append({
                "mmsi": mmsi, "nom": fiche[0], "capacite_m3": fiche[1], "annee": fiche[2], "classe": fiche[3],
                "lat": round(p["lat"], 4), "lon": round(p["lon"], 4), "sog": p["sog"], "cog": p["cog"],
                "arret": arret, "destination": info.get("destination", ""), "tirant_eau": info.get("tirant_eau"),
                "zone": cle,
            })
            continue

        # 2. type inconnu : on garde seulement la position (couche grise)
        if info.get("type") is None:
            inconnus.append([round(p["lat"], 3), round(p["lon"], 3), int(arret)])
            continue

        # 3. navire identifie : les codes 80 a 89 sont des navires-citernes
        z["identifies"] += 1
        if not 80 <= info["type"] <= 89:
            continue
        z["petroliers"] += 1
        z["a_l_ancre"] += arret
        petroliers.append({
            "mmsi": mmsi, "nom": info.get("nom") or p["nom"] or "Inconnu",
            "lat": round(p["lat"], 4), "lon": round(p["lon"], 4),
            "sog": p["sog"], "cog": p["cog"], "arret": arret,
            "destination": info.get("destination", ""), "tirant_eau": info.get("tirant_eau"),
            "longueur": info.get("longueur"), "zone": cle,
        })
    return zones, petroliers, methaniers, inconnus


def main():
    cle_api = os.getenv("AISSTREAM_API_KEY")
    if not cle_api:
        sys.exit("AISSTREAM_API_KEY introuvable (fichier .env ou secret GitHub).")

    positions, statiques = asyncio.run(ecouter(cle_api))

    memoire = charger_cache()
    memoire.update(statiques)                              # on enrichit la memoire avec les nouveaux navires
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(memoire), encoding="utf-8")

    zones, petroliers, methaniers, inconnus = construire(positions, memoire, charger_flotte())
    resultat = {
        "releve_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duree_ecoute_s": DUREE,
        "zones": [{"cle": cle, "nom": ZONES[cle]["nom"], "bbox": ZONES[cle]["bbox"],
                   "couverture": ZONES[cle]["couverture"], **zones[cle]} for cle in ZONES],
        "petroliers": petroliers,
        "methaniers": methaniers,       # navires de la flotte GNL (LNG-T3) reconnus par MMSI ou IMO
        "inconnus": inconnus,           # [lat, lon, a_l_arret] : navires entendus dont le type est inconnu
    }
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(json.dumps(resultat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"Releve de {DUREE} s : {len(positions)} navires, {len(statiques)} fiches statiques recues, "
          f"{len(memoire)} navires en memoire")
    for z in resultat["zones"]:
        print(f'  {z["nom"]:30s} navires {z["navires"]:5d} | identifies {z["identifies"]:4d} | '
              f'petroliers {z["petroliers"]:4d} (a l\'arret : {z["a_l_ancre"]}) | methaniers {z["methaniers"]:3d}')
    print(f"Ecrit : {SORTIE} ({SORTIE.stat().st_size / 1024:.0f} Ko)")


if __name__ == "__main__":
    main()
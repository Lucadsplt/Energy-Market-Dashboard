JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def profil_horaire(prix):
    """Prix moyen par jour de la semaine (0 = lundi) et par heure, en EUR/MWh.

    Les prix sont a 15 minutes : on les moyenne d'abord par heure,
    puis on regroupe par (jour de la semaine, heure).
    """
    horaire = prix.resample("1h").mean()
    table = horaire.groupby([horaire.index.dayofweek, horaire.index.hour]).mean().unstack()
    par_heure = horaire.groupby(horaire.index.hour).mean()

    return {
        "jours": JOURS,
        "matrice": [[round(float(v), 1) for v in ligne] for ligne in table.values],
        "stats": {
            "moyenne": round(float(prix.mean()), 1),
            "heure_la_moins_chere": int(par_heure.idxmin()),
            "heure_la_plus_chere": int(par_heure.idxmax()),
            "negatifs_pct": round(float((prix < 0).mean() * 100), 1),
            "prix_min": round(float(prix.min()), 0),
            "prix_max": round(float(prix.max()), 0),
            "nb_jours": int(horaire.index.normalize().nunique()),
        },
    }
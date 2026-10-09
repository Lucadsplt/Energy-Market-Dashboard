JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def prix_negatifs(prix):
    """Part des quarts d'heure a prix negatif, par mois, par heure et par jour de la semaine."""
    neg = prix < 0                         # Series de True/False ; la moyenne d'un booleen = une proportion
    par_mois = neg.groupby(prix.index.strftime("%Y-%m")).mean() * 100
    par_heure = neg.groupby(prix.index.hour).mean() * 100
    par_jour = neg.groupby(prix.index.dayofweek).mean() * 100

    duree_heures = (prix.index[-1] - prix.index[0]).total_seconds() / 3600
    weekend = neg[prix.index.dayofweek >= 5].sum()

    return {
        "mois": {"labels": list(par_mois.index), "pct": [round(float(v), 1) for v in par_mois]},
        "heures": [round(float(v), 1) for v in par_heure.reindex(range(24), fill_value=0)],
        "jours": {"labels": JOURS, "pct": [round(float(v), 1) for v in par_jour.reindex(range(7), fill_value=0)]},
        "stats": {
            "pct_total": round(float(neg.mean() * 100), 1),
            "heures_negatives": round(float(neg.mean() * duree_heures), 0),
            "pct_weekend": round(float(weekend / neg.sum() * 100), 0),
            "prix_moyen_si_negatif": round(float(prix[neg].mean()), 1),
            "prix_min": round(float(prix.min()), 0),
        },
    }
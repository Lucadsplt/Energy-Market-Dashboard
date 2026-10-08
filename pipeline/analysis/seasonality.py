def indice_saisonnier(prix, jours_min=240):
    """Indice saisonnier mensuel : prix moyen du mois / prix moyen de l'annee x 100.

    - 100 = prix moyen de l'annee
    - on garde les annees completes (>= jours_min seances) pour ne pas biaiser les mois
    - la mediane des annees resiste aux annees exceptionnelles (ex. 2022)
    """
    df = prix.to_frame("prix")
    df["annee"] = df.index.year
    df["mois"] = df.index.month

    nb_seances = df.groupby("annee")["prix"].transform("count")
    df = df[nb_seances >= jours_min]

    moyenne_annee = df.groupby("annee")["prix"].transform("mean")
    df["indice"] = df["prix"] / moyenne_annee * 100

    table = df.pivot_table(index="annee", columns="mois", values="indice", aggfunc="mean")
    return {
        "annees": {
            str(annee): [None if v != v else round(float(v), 1) for v in ligne]
            for annee, ligne in table.iterrows()
        },
        "mediane": [round(float(v), 1) for v in table.median()],
    }
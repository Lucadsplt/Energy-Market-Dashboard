def zscore_glissant(serie, fenetre=252):
    """Z-score glissant : (valeur - moyenne des `fenetre` derniers jours) / ecart-type de la meme fenetre.

    Renvoie (z, moyenne). Les premieres valeurs sont vides (NaN) : il faut assez
    d'historique pour calculer la moyenne. 252 = nombre de jours de bourse par an.
    """
    moyenne = serie.rolling(fenetre).mean()
    ecart_type = serie.rolling(fenetre).std()
    return (serie - moyenne) / ecart_type, moyenne
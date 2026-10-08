import numpy as np


def calibrer(prix):
    """Estime (kappa, mu, sigma) du modele Ornstein-Uhlenbeck sur le LOG du prix.

    Modele discret : x_{t+1} - x_t = a + b * x_t + bruit      (x = ln(prix))
    Une regression lineaire donne a et b, d'ou :
      kappa = -b        vitesse de retour vers la moyenne
      mu    = -a / b    niveau moyen long terme (en log)
      sigma = ecart-type des residus (volatilite quotidienne)
    """
    x = np.log(prix.values)
    x_veille = x[:-1]
    variation = np.diff(x)

    b, a = np.polyfit(x_veille, variation, 1)    # pente, ordonnee a l'origine
    if b >= 0:
        raise ValueError("Pas de retour a la moyenne detecte (b >= 0) : modele inadapte.")

    residus = variation - (a + b * x_veille)
    return {"kappa": -b, "mu": -a / b, "sigma": residus.std()}


def simuler(params, x0, jours, n=10000, seed=42):
    """Simule `n` trajectoires de prix sur `jours` jours. Renvoie un tableau (jours, n).

    On avance jour par jour, mais les n trajectoires en meme temps (vectorise).
    seed fixe : meme resultat a chaque execution, donc reproductible.
    """
    rng = np.random.default_rng(seed)
    x = np.full(n, x0)
    chemins = np.empty((jours, n))
    for t in range(jours):
        x = x + params["kappa"] * (params["mu"] - x) + params["sigma"] * rng.standard_normal(n)
        chemins[t] = x
    return np.exp(chemins)    # retour du log vers les prix


def resumer(chemins, prix0):
    """Bandes du fan chart + VaR et Expected Shortfall a 95 % (en % de perte)."""
    niveaux = [5, 25, 50, 75, 95]
    bandes = np.percentile(chemins, niveaux, axis=1)    # une ligne par niveau

    rendements = chemins[-1] / prix0 - 1                # resultat a l'echeance
    seuil = np.percentile(rendements, 5)
    return {
        "bandes": {f"p{n}": b.round(2).tolist() for n, b in zip(niveaux, bandes)},
        "var95": float(-seuil * 100),                           # perte qu'on ne depasse pas 95 % du temps
        "es95": float(-rendements[rendements <= seuil].mean() * 100),   # perte moyenne dans les 5 % pires cas
    }
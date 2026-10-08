import numpy as np


def distribution(rendements, bins=40):
    """Histogramme des rendements (en %) + courbe normale + statistiques de forme."""
    r = rendements.values * 100                 # en pourcentage
    densite, bords = np.histogram(r, bins=bins, density=True)
    centres = (bords[:-1] + bords[1:]) / 2      # milieu de chaque barre

    m, s = r.mean(), r.std()
    normale = np.exp(-0.5 * ((centres - m) / s) ** 2) / (s * np.sqrt(2 * np.pi))

    z = (r - m) / s                             # ecarts reduits (en nombre d'ecarts-types)
    return {
        "centres": centres.round(2).tolist(),
        "densite": densite.round(4).tolist(),
        "normale": normale.round(4).tolist(),
        "stats": {
            "ecart_type": round(float(s), 2),
            "asymetrie": round(float((z ** 3).mean()), 2),
            "kurtosis_exces": round(float((z ** 4).mean() - 3), 2),
            "jours_extremes_pct": round(float((np.abs(z) > 3).mean() * 100), 2),
            "pire_jour": round(float(r.min()), 1),
            "meilleur_jour": round(float(r.max()), 1),
            "nb_jours": int(len(r)),
        },
    }
"""Moteur de backtest : mesure honnetement la valeur d'une regle de trading.

Principes (chacun repond a un piege rencontre en testant l'ecart Brent - WTI) :
  1. AUCUN REGARD DANS LE FUTUR : la position decidee a la cloture du jour t ne s'applique qu'a partir de t+1.
  2. RETARD D'EXECUTION : on ne peut pas trader exactement au prix de cloture qui a produit le signal.
     On mesure la strategie avec 0, 1, 2, 3 et 5 jours de retard. Un gain qui disparait des le premier jour
     n'etait pas exploitable (typiquement : bruit de mesure entre deux prix releves a des heures differentes).
  3. COUTS : chaque changement de position coute des frais et du glissement.
  4. STABILITE : la regle doit marcher sur deux sous-periodes, pas seulement sur l'ensemble.
  5. HASARD : un test par bootstrap donne la probabilite d'obtenir un resultat aussi bon sans aucun talent,
     avec un seuil corrige du nombre de regles essayees (plus on essaie de regles, plus il faut etre exigeant).
"""
import numpy as np
import pandas as pd

JOURS_AN = 252
COUT_PAR_JAMBE = 0.0005          # 5 points de base (0,05 %) par changement de position et par jambe
RETARDS = [0, 1, 2, 3, 5]
RETARD_REFERENCE = 1             # la valeur « realiste » d'une regle est mesuree avec 1 jour de retard


def rendements_nets(rend_actif, position, retard=RETARD_REFERENCE, cout=COUT_PAR_JAMBE):
    """Rendements quotidiens de la strategie, apres couts.

    `position` est decidee a la cloture du jour t (+1 acheteur, -1 vendeur, 0 hors marche) ;
    elle s'applique au rendement du jour t + 1 + retard.
    """
    pos = position.shift(1 + retard).fillna(0)
    brut = pos * rend_actif
    couts = pos.diff().abs().fillna(0) * cout
    return brut - couts, pos


def sharpe(rend, jours_an=JOURS_AN):
    """Rendement moyen rapporte a la volatilite, annualise (le ratio de Sharpe, sans taux sans risque)."""
    r = rend.dropna()
    if len(r) < 30 or r.std() == 0:
        return float("nan")
    return float(r.mean() / r.std() * np.sqrt(jours_an))


def metriques(rend, pos):
    r = rend.dropna()
    cumul = (1 + r).cumprod()
    annees = len(r) / JOURS_AN
    return {
        "annualise_pct": round(float(cumul.iloc[-1] ** (1 / annees) - 1) * 100, 1),
        "volatilite_pct": round(float(r.std() * np.sqrt(JOURS_AN)) * 100, 1),
        "sharpe": round(sharpe(r), 2),
        "max_drawdown_pct": round(float((cumul / cumul.cummax() - 1).min()) * 100, 1),
        "trades": int((pos.diff().abs() > 0).sum()),
        "jours_en_position_pct": round(float((pos != 0).mean()) * 100),
    }


def p_valeur_bootstrap(rend, bloc=20, tirages=2000, graine=0):
    """Probabilite de faire aussi bien PAR PUR HASARD (bootstrap par blocs, vectorise).

    On centre les rendements (moyenne nulle = aucun talent), on les retire au hasard par blocs de `bloc` jours
    (pour conserver l'autocorrelation) et on regarde dans quelle proportion de tirages la moyenne depasse celle observee.
    """
    r = rend.dropna().values
    n = len(r)
    if n < 100:
        return float("nan")
    rng = np.random.default_rng(graine)
    centre = r - r.mean()
    nb_blocs = int(np.ceil(n / bloc))
    debuts = rng.integers(0, n, size=(tirages, nb_blocs))
    indices = (debuts[:, :, None] + np.arange(bloc)[None, None, :]) % n
    moyennes = centre[indices.reshape(tirages, -1)[:, :n]].mean(axis=1)
    return float((moyennes >= r.mean()).mean())


def evaluer(rend_actif, position, cout=COUT_PAR_JAMBE, coupure="2013-01-01"):
    """Toutes les mesures d'une regle : metriques, sensibilite au retard, stabilite, hasard."""
    net_ref, pos_ref = rendements_nets(rend_actif, position, RETARD_REFERENCE, cout)
    retard = []
    for r in RETARDS:
        net, _ = rendements_nets(rend_actif, position, r, cout)
        retard.append({"jours": r, "sharpe": round(sharpe(net), 2)})

    avant, apres = net_ref[net_ref.index < coupure], net_ref[net_ref.index >= coupure]
    debut = net_ref.index[0].year
    sous_periodes = [
        {"nom": f"{debut}–{int(coupure[:4]) - 1}", "sharpe": round(sharpe(avant), 2)},
        {"nom": f"{coupure[:4]}–{net_ref.index[-1].year}", "sharpe": round(sharpe(apres), 2)},
    ]
    return {
        "metriques": metriques(net_ref, pos_ref),
        "metriques_sans_retard": metriques(*rendements_nets(rend_actif, position, 0, cout)),
        "retard": retard,
        "sous_periodes": sous_periodes,
        "p_valeur": round(p_valeur_bootstrap(net_ref), 3),
        "net": net_ref,
    }


def verdict(evaluation, seuil):
    """Verdict en trois etats, selon des regles posees AVANT de regarder les resultats.

    - « probable artefact » : bon resultat sans retard, qui s'effondre des 1 jour de retard ;
    - « demontre »          : hasard improbable (sous le seuil corrige), positif sur les deux sous-periodes,
                              et qui ne s'effondre pas avec 3 jours de retard ;
    - « non demontre »      : tout le reste.
    """
    s = {r["jours"]: r["sharpe"] for r in evaluation["retard"]}
    s0, s1, s3 = s[0], s[1], s[3]
    if s0 >= 0.4 and s1 <= 0.6 * s0:
        return "artefact", (f"Le ratio de Sharpe passe de {s0:+.2f} sans retard à {s1:+.2f} avec 1 jour de retard, puis {s3:+.2f} avec 3 jours : ".replace(".", ",") +
                            "une grande partie du gain disparaît dès qu'on n'exécute plus exactement à la clôture. "
                            "C'est le signe d'un artefact de mesure (par exemple deux prix relevés à des heures différentes), pas d'un gain exploitable. "
                            "Un éventuel petit effet résiduel resterait à vérifier sur des prix à terme relevés à la même heure, avec les vrais coûts.")
    stable = all(p["sharpe"] > 0 for p in evaluation["sous_periodes"])
    tient = s1 > 0 and s3 >= 0.5 * s1
    if evaluation["p_valeur"] <= seuil and stable and tient:
        return "demontre", ("Probabilité de hasard sous le seuil corrigé, résultat positif sur les deux sous-périodes "
                            "et qui tient avec 3 jours de retard.")
    raisons = []
    if evaluation["p_valeur"] > seuil:
        raisons.append(f"probabilité de hasard de {evaluation['p_valeur']:.3f} (seuil corrigé {seuil:.4f})".replace(".", ","))
    if not stable:
        raisons.append("résultat négatif sur au moins une sous-période")
    if not tient:
        raisons.append("le résultat ne résiste pas au retard d'exécution")
    return "non_demontre", "Non démontré : " + " ; ".join(raisons) + "."

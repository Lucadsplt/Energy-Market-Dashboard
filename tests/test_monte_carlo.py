"""Tests du modele de simulation (Ornstein-Uhlenbeck), de la VaR et du test de Kupiec."""
import math

import numpy as np
import pandas as pd
import pytest

from pipeline.analysis.backtest import backtest_var, kupiec
from pipeline.analysis.monte_carlo import calibrer, resumer, simuler
from pipeline.analysis.returns import log_returns

KAPPA, MU_PRIX, SIGMA = 0.05, 80.0, 0.02


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def formule_exacte(params, p0, n):
    """Loi exacte du log du prix apres n jours : normale de moyenne m et d'ecart-type s."""
    a, mu, x0 = 1 - params["kappa"], params["mu"], math.log(p0)
    m = mu + a ** n * (x0 - mu)
    s = math.sqrt(params["sigma"] ** 2 * (1 - a ** (2 * n)) / (1 - a * a))
    return m, s


def serie_ou(n=20000, graine=0, kappa=KAPPA, mu_prix=MU_PRIX, sigma=SIGMA, debut="2000-01-03"):
    rng = np.random.default_rng(graine)
    mu, x = math.log(mu_prix), math.log(mu_prix)
    xs = []
    for _ in range(n):
        x = x + kappa * (mu - x) + sigma * rng.standard_normal()
        xs.append(x)
    return pd.Series(np.exp(xs), index=pd.bdate_range(debut, periods=n))


PARAMS = {"kappa": KAPPA, "mu": math.log(MU_PRIX), "sigma": SIGMA}


# ---------------------------------------------------------------- rendements
def test_rendements_logarithmiques_exemple():
    r = log_returns(pd.Series([100.0, 110.0, 99.0]))
    assert r.iloc[0] == pytest.approx(0.0953, abs=1e-4)
    assert r.iloc[1] == pytest.approx(-0.1054, abs=1e-4)


def test_les_rendements_logarithmiques_s_additionnent():
    prix = pd.Series([100.0, 103.0, 99.0, 120.0, 118.0])
    assert log_returns(prix).sum() == pytest.approx(math.log(prix.iloc[-1] / prix.iloc[0]))


# ---------------------------------------------------------------- calibrage
def test_calibrage_retrouve_les_parametres_d_un_processus_connu():
    p = calibrer(serie_ou())
    assert p["kappa"] == pytest.approx(KAPPA, rel=0.25)       # le retour a la moyenne est le plus difficile a estimer
    assert math.exp(p["mu"]) == pytest.approx(MU_PRIX, rel=0.03)
    assert p["sigma"] == pytest.approx(SIGMA, rel=0.03)


def test_calibrage_refuse_une_serie_sans_retour_a_la_moyenne():
    explosive = pd.Series(np.exp(1.01 ** np.arange(300) * 0.1))   # le log du prix s'eloigne de plus en plus
    with pytest.raises(ValueError):
        calibrer(explosive)


# ---------------------------------------------------------------- simulation
def test_simulation_forme_et_reproductibilite():
    c1 = simuler(PARAMS, math.log(100), 30, n=500, seed=1)
    c2 = simuler(PARAMS, math.log(100), 30, n=500, seed=1)
    assert c1.shape == (30, 500)
    assert np.array_equal(c1, c2)
    assert (c1 > 0).all()


def test_sans_bruit_la_simulation_suit_la_formule_deterministe():
    p = {"kappa": 0.1, "mu": math.log(80), "sigma": 0.0}
    c = simuler(p, math.log(120), 10, n=3)
    m, _ = formule_exacte(p, 120, 10)
    assert c[-1] == pytest.approx(math.exp(m))


def test_la_simulation_gaussienne_a_la_bonne_loi_a_30_jours():
    c = simuler(PARAMS, math.log(120), 30, n=100000)
    m, s = formule_exacte(PARAMS, 120, 30)
    x = np.log(c[-1])
    assert x.mean() == pytest.approx(m, abs=4 * s / math.sqrt(100000))
    assert x.std() == pytest.approx(s, rel=0.02)


def test_les_chocs_de_student_gardent_la_meme_volatilite():
    gauss = simuler(PARAMS, math.log(100), 30, n=100000)
    student = simuler(PARAMS, math.log(100), 30, n=100000, df=5)
    assert np.log(student[-1]).std() == pytest.approx(np.log(gauss[-1]).std(), rel=0.03)


def test_les_queues_epaisses_donnent_plus_de_valeurs_extremes():
    gauss = simuler({"kappa": 0.0, "mu": 0.0, "sigma": 0.03}, 0.0, 1, n=200000)[-1]
    student = simuler({"kappa": 0.0, "mu": 0.0, "sigma": 0.03}, 0.0, 1, n=200000, df=4)[-1]
    seuil = math.exp(4 * 0.03)
    assert (student > seuil).mean() > 3 * (gauss > seuil).mean()


# ---------------------------------------------------------------- VaR et Expected Shortfall
def test_var_et_es_correspondent_a_la_formule_exacte():
    p0 = 120.0
    c = simuler(PARAMS, math.log(p0), 30, n=200000)
    r = resumer(c, p0)
    m, s = formule_exacte(PARAMS, p0, 30)
    z = -1.6448536
    var = -(math.exp(m + z * s) / p0 - 1) * 100
    es = -(math.exp(m + s * s / 2) * phi(z - s) / 0.05 / p0 - 1) * 100
    assert r["var95"] == pytest.approx(var, abs=0.5)
    assert r["es95"] == pytest.approx(es, abs=0.5)


def test_var_inferieure_a_es_et_bandes_ordonnees():
    c = simuler(PARAMS, math.log(100), 30, n=5000)
    r = resumer(c, 100.0)
    assert r["es95"] >= r["var95"]
    b = r["bandes"]
    assert all(b["p5"][i] <= b["p25"][i] <= b["p50"][i] <= b["p75"][i] <= b["p95"][i] for i in range(30))


def test_un_prix_qui_ne_bouge_pas_n_a_aucun_risque():
    c = simuler({"kappa": 0.0, "mu": 0.0, "sigma": 0.0}, math.log(100), 30, n=100)
    r = resumer(c, 100.0)
    assert r["var95"] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------- test de Kupiec
def test_kupiec_vaut_un_quand_le_taux_observe_est_exactement_celui_attendu():
    assert kupiec(200, 10) == pytest.approx(1.0)


def test_kupiec_rejette_un_taux_tres_eloigne():
    assert kupiec(200, 40) < 0.001
    assert kupiec(200, 0) < 0.01


def test_kupiec_diminue_quand_on_s_eloigne_du_taux_attendu():
    valeurs = [kupiec(200, x) for x in (10, 13, 16, 20, 25)]
    assert valeurs == sorted(valeurs, reverse=True)


def test_kupiec_est_coherent_avec_les_valeurs_critiques_du_khi_deux():
    """n = 250, x = 5 (au lieu de 12,5 attendus). Valeurs critiques connues du khi-deux a 1 degre de liberte :
    3,841 correspond a une probabilite de 0,05 et 6,635 a 0,01. Une statistique LR entre les deux donne une probabilite entre 0,01 et 0,05."""
    n, x, p = 250, 5, 0.05
    t = x / n
    lr = -2 * ((n - x) * math.log(1 - p) + x * math.log(p)) + 2 * ((n - x) * math.log(1 - t) + x * math.log(t))
    assert 3.841 < lr < 6.635
    assert 0.01 < kupiec(n, x) < 0.05
    assert kupiec(n, x) == pytest.approx(math.erfc(math.sqrt(lr / 2)))      # khi2(1) : P(X > lr) = erfc(racine(lr / 2))


# ---------------------------------------------------------------- backtest de la VaR
def test_backtest_var_sur_un_processus_connu_donne_un_taux_proche_de_5_pour_cent():
    prix = serie_ou(n=4500, graine=3, kappa=0.02, sigma=0.015)
    b = backtest_var(prix, fenetre_ans=5, horizon=30, pas=30, debut="2008-01-01", n=1000)
    assert b["tests"] > 50
    assert 0 <= b["depassement_bas_pct"] <= 15
    assert 0 <= b["depassement_haut_pct"] <= 15
    assert b["p_kupiec"] > 0.01                             # le modele est le bon : il ne doit pas etre rejete
    assert b["var_moyenne"] > 0


def test_backtest_var_ne_calibre_que_sur_le_passe(monkeypatch):
    """A chaque date de test, les donnees de calibrage doivent s'arreter a cette date et couvrir la fenetre demandee."""
    import pipeline.analysis.backtest as backtest

    prix = serie_ou(n=3500, graine=5, kappa=0.02, sigma=0.015)
    vus = []
    vrai_calibrer = backtest.calibrer

    def espion(passe):
        vus.append((passe.index[0], passe.index[-1]))
        return vrai_calibrer(passe)

    monkeypatch.setattr(backtest, "calibrer", espion)
    backtest.backtest_var(prix, 3, horizon=30, pas=30, debut="2008-01-01", n=200)

    assert vus
    derniere_date_possible = prix.index[-1 - 30]            # il faut 30 jours de futur pour juger la prevision
    for premier, dernier in vus:
        assert dernier <= derniere_date_possible
        assert dernier - premier <= pd.Timedelta(days=3 * 366)       # fenetre de 3 ans, pas plus
        assert dernier - premier >= pd.Timedelta(days=3 * 365 - 10)  # et vraiment 3 ans

"""Tests des fonctions d'analyse : statistiques, ecarts de prix, saisonnalite, electricite, maritime, export JSON."""
import json
import math

import numpy as np
import pandas as pd
import pytest

from pipeline.analysis.distribution import distribution
from pipeline.analysis.gas_spread import MWH_PAR_MMBTU, ecart_jkm_ttf, ecart_ttf_hh
from pipeline.analysis.maritime import analyse_detroits, zscore_vs_reference
from pipeline.analysis.negative_prices import prix_negatifs
from pipeline.analysis.oil_spread import analyse_ecart
from pipeline.analysis.price_profile import profil_horaire
from pipeline.analysis.seasonality import indice_saisonnier
from pipeline.analysis.volatility import rolling_volatility
from pipeline.analysis.zscore import zscore_glissant
from pipeline.export.json_export import sans_nan


# ---------------------------------------------------------------- z-score et volatilite
def test_zscore_d_une_valeur_isolee():
    s = pd.Series([10.0, 12.0, 8.0, 10.0, 10.0, 30.0])
    z, moyenne = zscore_glissant(s, fenetre=5)
    fenetre = s.iloc[1:6]
    assert moyenne.iloc[-1] == pytest.approx(fenetre.mean())
    assert z.iloc[-1] == pytest.approx((30 - fenetre.mean()) / fenetre.std(ddof=1))
    assert z.iloc[:4].isna().all()                          # fenetre incomplete : pas de z


def test_zscore_d_une_serie_aleatoire_est_centre_reduit():
    s = pd.Series(np.random.default_rng(0).normal(0, 1, 5000))
    z, _ = zscore_glissant(s, 252)
    z = z.dropna()
    assert abs(z.mean()) < 0.05 and z.std() == pytest.approx(1.0, abs=0.05)


def test_volatilite_d_un_prix_constant_est_nulle_et_annualisee_par_racine_de_252():
    assert rolling_volatility(pd.Series([100.0] * 20)).dropna().eq(0).all()
    prix = pd.Series(100 * np.cumprod(1 + np.random.default_rng(1).normal(0, 0.01, 60)))
    v = rolling_volatility(prix, window=7)
    attendu = prix.pct_change().iloc[-7:].std(ddof=1) * math.sqrt(252) * 100
    assert v.iloc[-1] == pytest.approx(attendu)


# ---------------------------------------------------------------- distribution
def test_distribution_d_un_echantillon_normal():
    r = pd.Series(np.random.default_rng(0).normal(0, 0.02, 20000))
    d = distribution(r)
    s = d["stats"]
    assert s["ecart_type"] == pytest.approx(2.0, abs=0.05)
    assert abs(s["asymetrie"]) < 0.1 and abs(s["kurtosis_exces"]) < 0.2
    assert s["jours_extremes_pct"] == pytest.approx(0.27, abs=0.15)      # 0,27 % au-dela de 3 ecarts-types
    assert s["nb_jours"] == 20000
    largeur = d["centres"][1] - d["centres"][0]
    assert sum(d["densite"]) * largeur == pytest.approx(1.0, abs=0.02)  # l'histogramme est une densite


def test_distribution_detecte_les_queues_epaisses():
    r = pd.Series(np.random.default_rng(0).standard_t(3, 20000) * 0.01)
    assert distribution(r)["stats"]["kurtosis_exces"] > 2


def test_distribution_pire_et_meilleur_jour():
    d = distribution(pd.Series([-0.1, 0.0, 0.02, 0.15, 0.01] * 20))
    assert d["stats"]["pire_jour"] == pytest.approx(-10.0)
    assert d["stats"]["meilleur_jour"] == pytest.approx(15.0)


# ---------------------------------------------------------------- ecart Brent - WTI
def test_ecart_brent_wti_z_et_statistiques():
    idx = pd.bdate_range("2020-01-01", periods=400)
    rng = np.random.default_rng(0)
    wti = pd.Series(60 + rng.normal(0, 1, 400).cumsum() * 0.1, index=idx)
    brent = wti + 4 + rng.normal(0, 0.3, 400)
    brent.iloc[-1] = wti.iloc[-1] + 12                       # ecart soudain tres grand
    res = analyse_ecart(pd.DataFrame({"brent": brent, "wti": wti}))
    assert len(res["z"]) == 400 - 251                         # les 251 premiers jours n'ont pas de z
    assert res["stats"]["z_actuel"] > 5
    assert res["stats"]["ecart_actuel"] == pytest.approx(12.0, abs=0.1)
    assert 0 <= res["stats"]["jours_extremes_pct"] <= 100


# ---------------------------------------------------------------- conversions du gaz
def test_la_constante_mwh_par_mmbtu():
    assert MWH_PAR_MMBTU == pytest.approx(0.293071)


def donnees_gaz(ttf=100.0, hh=3.0, jkm=30.0, fx=1.1, n=5):
    idx = pd.bdate_range("2024-01-01", periods=n)
    return (pd.Series(ttf, index=idx), pd.Series(hh, index=idx), pd.Series(jkm, index=idx), pd.Series(fx, index=idx))


def test_ecart_ttf_henry_hub_en_euros_par_mwh():
    ttf, hh, _, fx = donnees_gaz()
    res = ecart_ttf_hh(ttf, hh, fx)
    hh_eur = 3.0 / 0.293071 / 1.1
    assert res["hh_eur"][-1] == pytest.approx(hh_eur, abs=0.01)
    assert res["ecart"][-1] == pytest.approx(100 - hh_eur, abs=0.01)
    assert res["stats"]["actuel"] == pytest.approx(100 - hh_eur, abs=0.1)


def test_ecart_jkm_ttf_en_dollars_par_mmbtu():
    ttf, _, jkm, fx = donnees_gaz()
    res = ecart_jkm_ttf(jkm, ttf, fx)
    ttf_usd = 100 * 0.293071 * 1.1
    assert res["ttf_usd"][-1] == pytest.approx(ttf_usd, abs=0.01)
    assert res["ecart"][-1] == pytest.approx(30 - ttf_usd, abs=0.01)
    assert res["stats"]["asie_plus_chere_pct"] == 0           # le JKM est ici moins cher que le TTF converti


def test_les_conversions_de_gaz_sont_coherentes_entre_elles():
    """Un TTF et un Henry Hub qui valent la meme chose en energie doivent donner un ecart nul."""
    fx = 1.2
    hh = 3.0
    ttf_equivalent = hh / MWH_PAR_MMBTU / fx
    idx = pd.bdate_range("2024-01-01", periods=3)
    res = ecart_ttf_hh(pd.Series(ttf_equivalent, index=idx), pd.Series(hh, index=idx), pd.Series(fx, index=idx))
    assert abs(res["ecart"][-1]) < 0.01


def test_le_taux_de_change_manquant_reprend_la_veille():
    idx = pd.bdate_range("2024-01-01", periods=4)
    ttf, hh = pd.Series(100.0, index=idx), pd.Series(3.0, index=idx)
    fx = pd.Series([1.1, np.nan, 1.1, 1.1], index=idx)
    assert len(ecart_ttf_hh(ttf, hh, fx)["dates"]) == 4


def test_les_jours_ou_une_serie_manque_sont_ignores():
    idx = pd.bdate_range("2024-01-01", periods=5)
    ttf = pd.Series(100.0, index=idx)
    hh = pd.Series([3.0, 3.0, np.nan, 3.0, 3.0], index=idx)
    assert len(ecart_ttf_hh(ttf, hh, pd.Series(1.1, index=idx))["dates"]) == 4


# ---------------------------------------------------------------- saisonnalite
def prix_saisonniers(annees=range(2018, 2024), seances=250):
    morceaux = []
    for a in annees:
        idx = pd.bdate_range(f"{a}-01-01", periods=seances)
        morceaux.append(pd.Series(np.where(idx.month == 7, 150.0, 100.0), index=idx))   # juillet 50 % plus cher
    return pd.concat(morceaux)


def test_indice_saisonnier_un_mois_plus_cher_depasse_100():
    res = indice_saisonnier(prix_saisonniers())
    mediane = res["mediane"]
    assert mediane[6] > 110                                  # juillet
    assert mediane[0] < 100                                  # janvier
    assert len(mediane) == 12


def test_indice_saisonnier_exclut_les_annees_incompletes():
    prix = prix_saisonniers(seances=250)
    incomplete = prix[prix.index.year == 2020].iloc[:100]
    prix = pd.concat([prix[prix.index.year != 2020], incomplete]).sort_index()
    assert "2020" not in indice_saisonnier(prix)["annees"]


def test_indice_saisonnier_moyenne_annuelle_egale_cent():
    res = indice_saisonnier(prix_saisonniers())
    for ligne in res["annees"].values():
        valeurs = [v for v in ligne if v is not None]
        assert sum(valeurs) / len(valeurs) == pytest.approx(100, abs=3)


# ---------------------------------------------------------------- electricite
def prix_quart_d_heure(jours=14, debut="2025-01-06"):
    idx = pd.date_range(debut, periods=jours * 96, freq="15min", tz="Europe/Brussels")
    return pd.Series(50.0, index=idx)


def test_prix_negatifs_proportions_et_week_end():
    p = prix_quart_d_heure()
    samedi = p.index.dayofweek == 5
    p[samedi & (p.index.hour == 13)] = -10.0                  # 4 quarts d'heure negatifs par samedi, 2 samedis
    res = prix_negatifs(p)
    assert res["stats"]["pct_total"] == pytest.approx(8 / len(p) * 100, abs=0.1)
    assert res["stats"]["pct_weekend"] == 100                 # tous les prix negatifs tombent un samedi
    assert res["stats"]["prix_moyen_si_negatif"] == -10.0
    assert res["heures"][13] > 0 and res["heures"][12] == 0
    assert res["jours"]["pct"][5] > 0 and res["jours"]["pct"][1] == 0


def test_profil_horaire_cases_et_statistiques():
    p = prix_quart_d_heure()
    p[p.index.hour == 19] = 90.0
    p[p.index.hour == 13] = 5.0
    res = profil_horaire(p)
    assert res["stats"]["heure_la_plus_chere"] == 19
    assert res["stats"]["heure_la_moins_chere"] == 13
    assert res["stats"]["nb_jours"] == 14
    assert len(res["matrice"]) == 7 and len(res["matrice"][0]) == 24
    assert res["matrice"][2][19] == 90.0                      # mercredi 19 h
    assert res["stats"]["prix_min"] == 5 and res["stats"]["prix_max"] == 90


def test_profil_horaire_moyenne_les_quarts_d_heure_d_une_meme_heure():
    p = prix_quart_d_heure(jours=7)
    h = p.index.hour == 10
    p[h & (p.index.minute == 0)] = 10.0
    p[h & (p.index.minute == 15)] = 20.0
    p[h & (p.index.minute == 30)] = 30.0
    p[h & (p.index.minute == 45)] = 40.0
    assert profil_horaire(p)["matrice"][0][10] == 25.0


# ---------------------------------------------------------------- trafic maritime
def test_zscore_de_reference_maritime():
    idx = pd.date_range("2025-01-01", "2026-02-28", freq="D")
    moy7 = pd.Series(10.0, index=idx)
    moy7[moy7.index.year == 2025] += np.sin(np.arange((moy7.index.year == 2025).sum()))   # un peu de variation en 2025
    moy7.iloc[-1] = 0.0
    z, ref = zscore_vs_reference(moy7)
    en_2025 = moy7[moy7.index.year == 2025]
    assert ref == pytest.approx(en_2025.mean())
    assert z == pytest.approx((0 - en_2025.mean()) / en_2025.std(ddof=1))
    assert z < -5


def test_analyse_detroits_variation_et_serie():
    idx = pd.date_range("2025-01-01", "2026-03-31", freq="D")
    rng = np.random.default_rng(0)
    base = pd.Series(50 + rng.normal(0, 3, len(idx)), index=idx)
    base.iloc[-7:] = 25.0                                    # le trafic est divise par deux la derniere semaine
    df = pd.DataFrame({"Strait of Hormuz": base})
    res = analyse_detroits(df, {"Strait of Hormuz": "Détroit d'Ormuz"})[0]
    assert res["nom"] == "Détroit d'Ormuz"
    assert res["actuel_7j"] == pytest.approx(25.0, abs=0.1)
    assert res["variation_pct"] == pytest.approx(-50, abs=3)
    assert res["zscore"] < -2                                # classe « rupture »
    assert len(res["serie"]) == 90


# ---------------------------------------------------------------- export JSON
def test_sans_nan_remplace_nan_et_infini_par_none_recursivement():
    data = {"a": float("nan"), "b": [1.0, float("inf"), {"c": float("-inf"), "d": 2.5}], "e": "texte", "f": None}
    propre = sans_nan(data)
    assert propre == {"a": None, "b": [1.0, None, {"c": None, "d": 2.5}], "e": "texte", "f": None}
    json.dumps(propre, allow_nan=False)                      # ne leve pas d'erreur : JSON valide


def test_sans_nan_gere_les_flottants_numpy():
    propre = sans_nan({"x": np.float64("nan"), "y": np.float64(1.5)})
    assert propre["x"] is None and propre["y"] == 1.5

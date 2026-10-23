"""Tests du moteur de backtest : chaque test repond a une question « le moteur peut-il se tromper de cette facon ? »."""
import math

import numpy as np
import pandas as pd
import pytest

from pipeline.analysis.strategies_engine import (COUT_PAR_JAMBE, RETARDS, evaluer, metriques, p_valeur_bootstrap,
                                                 rendements_nets, sharpe, verdict)


def serie_aleatoire(n=3000, graine=0, moyenne=0.0, ecart=0.01, debut="2005-01-03"):
    rng = np.random.default_rng(graine)
    return pd.Series(rng.normal(moyenne, ecart, n), index=pd.bdate_range(debut, periods=n))


# ---------------------------------------------------------------- aucun regard dans le futur
def test_une_position_ne_gagne_jamais_le_rendement_du_jour_ou_elle_est_decidee():
    """Position decidee a la cloture de t = signe du rendement de t : sans regard dans le futur, elle ne doit rien rapporter."""
    r = serie_aleatoire()
    position = np.sign(r)                                   # triche : on connait le rendement du jour t
    net, _ = rendements_nets(r, position, retard=0, cout=0.0)
    assert abs(sharpe(net)) < 1.0                           # aucun gain systematique


def test_la_clairvoyance_du_lendemain_n_est_exploitable_qu_avec_un_retard_nul():
    """Position decidee en t = signe du rendement de t + 1. Retard 0 : on le gagne (Sharpe enorme). Retard 1 : disparu."""
    r = serie_aleatoire()
    position = np.sign(r.shift(-1)).fillna(0)
    sans_retard, _ = rendements_nets(r, position, retard=0, cout=0.0)
    avec_retard, _ = rendements_nets(r, position, retard=1, cout=0.0)
    assert sharpe(sans_retard) > 10
    assert abs(sharpe(avec_retard)) < 1.0


def test_la_position_est_decalee_de_un_plus_retard_jours():
    r = pd.Series(1.0, index=pd.bdate_range("2020-01-01", periods=10))
    position = pd.Series(0.0, index=r.index)
    position.iloc[3] = 1.0                                  # une position decidee le 4e jour seulement
    for retard in (0, 1, 2):
        _, pos = rendements_nets(r, position, retard=retard, cout=0.0)
        assert pos.iloc[3 + 1 + retard] == 1.0
        assert pos.sum() == 1.0


# ---------------------------------------------------------------- couts
def test_les_couts_valent_cout_fois_le_changement_de_position():
    r = pd.Series(0.0, index=pd.bdate_range("2020-01-01", periods=20))
    position = pd.Series([1.0, -1.0] * 10, index=r.index)   # change de sens chaque jour : |variation| = 2
    net, pos = rendements_nets(r, position, retard=0, cout=0.001)
    attendu = -(pos.diff().abs().fillna(0) * 0.001).sum()
    assert net.sum() == pytest.approx(attendu)
    assert net.sum() < 0


def test_sans_changement_de_position_un_seul_cout_d_entree():
    r = pd.Series(0.0, index=pd.bdate_range("2020-01-01", periods=50))
    position = pd.Series(1.0, index=r.index)
    net, _ = rendements_nets(r, position, retard=1, cout=COUT_PAR_JAMBE)
    assert net.sum() == pytest.approx(-COUT_PAR_JAMBE)


def test_rendement_brut_egal_position_fois_rendement_de_l_actif():
    r = serie_aleatoire(200)
    position = pd.Series(1.0, index=r.index)
    net, _ = rendements_nets(r, position, retard=0, cout=0.0)
    assert net.iloc[5:].equals(r.iloc[5:]) or np.allclose(net.iloc[5:], r.iloc[5:])


# ---------------------------------------------------------------- Sharpe
def test_sharpe_sur_un_exemple_calcule_a_la_main():
    r = pd.Series([0.01, -0.01, 0.02, 0.0] * 20)             # moyenne 0,005 ; ecart-type d'echantillon connu
    attendu = r.mean() / r.std(ddof=1) * math.sqrt(252)
    assert sharpe(r) == pytest.approx(attendu)


def test_sharpe_ne_depend_pas_de_l_echelle():
    r = serie_aleatoire(500, moyenne=0.0005)
    assert sharpe(r) == pytest.approx(sharpe(r * 10))


def test_sharpe_est_indefini_si_peu_de_donnees_ou_volatilite_nulle():
    assert math.isnan(sharpe(pd.Series([0.01] * 10)))
    assert math.isnan(sharpe(pd.Series([0.001] * 100)))


def test_sharpe_change_de_signe_avec_la_position():
    r = serie_aleatoire(1000, moyenne=0.0004)
    long, _ = rendements_nets(r, pd.Series(1.0, index=r.index), retard=0, cout=0.0)
    court, _ = rendements_nets(r, pd.Series(-1.0, index=r.index), retard=0, cout=0.0)
    assert sharpe(long) == pytest.approx(-sharpe(court))


# ---------------------------------------------------------------- metriques
def test_metriques_d_un_rendement_constant():
    r = pd.Series(0.001, index=pd.bdate_range("2015-01-01", periods=252))
    pos = pd.Series(1.0, index=r.index)
    m = metriques(r, pos)
    assert m["annualise_pct"] == pytest.approx((1.001 ** 252 - 1) * 100, abs=0.1)
    assert m["max_drawdown_pct"] == 0
    assert m["jours_en_position_pct"] == 100


def test_perte_maximale_d_une_chute_connue():
    r = pd.Series([0.1, -0.5, 0.1, 0.0] + [0.0] * 40)        # 1,1 puis 0,55 : perte de 50 % depuis le sommet
    m = metriques(r, pd.Series(1.0, index=r.index))
    assert m["max_drawdown_pct"] == pytest.approx(-50.0, abs=0.1)


def test_nombre_de_trades_compte_les_changements_de_position():
    r = pd.Series(0.0, index=pd.bdate_range("2020-01-01", periods=10))
    pos = pd.Series([0, 1, 1, 0, 0, -1, -1, -1, 0, 0], index=r.index, dtype=float)
    assert metriques(r, pos)["trades"] == 4


# ---------------------------------------------------------------- bootstrap
@pytest.mark.parametrize("graine", [1, 2, 3, 4, 5])
def test_bootstrap_sans_talent_donne_une_probabilite_moyenne(graine):
    p = p_valeur_bootstrap(serie_aleatoire(2500, graine=graine))
    assert 0.02 < p < 0.98                                  # ni tres petite, ni quasi certaine


def test_bootstrap_d_un_vrai_gain_donne_une_petite_probabilite():
    assert p_valeur_bootstrap(serie_aleatoire(2500, moyenne=0.002)) < 0.01


def test_bootstrap_d_une_perte_donne_une_probabilite_proche_de_un():
    assert p_valeur_bootstrap(serie_aleatoire(2500, moyenne=-0.002)) > 0.99


def test_bootstrap_est_reproductible_et_refuse_les_series_courtes():
    r = serie_aleatoire(1000)
    assert p_valeur_bootstrap(r) == p_valeur_bootstrap(r)
    assert math.isnan(p_valeur_bootstrap(r.iloc[:50]))


def test_bootstrap_ne_modifie_pas_ses_donnees():
    r = serie_aleatoire(500)
    copie = r.copy()
    p_valeur_bootstrap(r)
    assert r.equals(copie)


# ---------------------------------------------------------------- evaluer
def test_evaluer_renvoie_toutes_les_mesures_et_les_sous_periodes():
    r = serie_aleatoire(4000, debut="2004-01-01")
    position = pd.Series(1.0, index=r.index)
    e = evaluer(r, position)
    assert {"metriques", "metriques_sans_retard", "retard", "sous_periodes", "p_valeur", "net"} <= set(e)
    assert [x["jours"] for x in e["retard"]] == RETARDS
    assert e["sous_periodes"][0]["nom"].startswith("2004")
    assert e["sous_periodes"][1]["nom"].startswith("2013")
    assert len(e["net"]) == len(r)


def test_evaluer_respecte_la_date_de_coupure_demandee():
    r = serie_aleatoire(2500, debut="2017-10-23")
    e = evaluer(r, pd.Series(1.0, index=r.index), coupure="2022-01-01")
    assert e["sous_periodes"][0]["nom"].startswith("2017") and "2021" in e["sous_periodes"][0]["nom"]
    assert not math.isnan(e["sous_periodes"][0]["sharpe"])


def test_evaluer_un_gain_qui_disparait_des_un_jour_de_retard():
    """Le cas Brent - WTI : une regle qui exploite le bruit de mesure s'effondre des le premier jour de retard."""
    r = serie_aleatoire(4000, graine=7)
    position = np.sign(r.shift(-1)).fillna(0)              # clairvoyante : gain parfait a retard 0
    e = evaluer(r, position, cout=0.0)
    s = {x["jours"]: x["sharpe"] for x in e["retard"]}
    assert s[0] > 5
    assert abs(s[1]) < 1.5


# ---------------------------------------------------------------- verdict
def evaluation(s0, s1, s2, s3, s5, avant, apres, p):
    return {"retard": [{"jours": j, "sharpe": s} for j, s in zip(RETARDS, (s0, s1, s2, s3, s5))],
            "sous_periodes": [{"nom": "a", "sharpe": avant}, {"nom": "b", "sharpe": apres}], "p_valeur": p}


def test_verdict_artefact_quand_le_gain_s_effondre_au_premier_jour():
    cle, texte = verdict(evaluation(0.82, 0.43, 0.39, 0.17, 0.16, 0.3, 0.4, 0.002), seuil=0.0125)
    assert cle == "artefact"
    assert "artefact" in texte


def test_verdict_demontre_quand_tout_est_reuni():
    cle, _ = verdict(evaluation(0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.5, 0.005), seuil=0.0125)
    assert cle == "demontre"


def test_verdict_non_demontre_si_la_probabilite_de_hasard_depasse_le_seuil():
    cle, texte = verdict(evaluation(0.62, 0.58, 0.42, 0.33, 0.44, 0.42, 0.74, 0.016), seuil=0.0125)
    assert cle == "non_demontre"
    assert "0,016" in texte                                 # nombre ecrit a la francaise


def test_verdict_non_demontre_si_une_sous_periode_est_negative():
    cle, _ = verdict(evaluation(0.9, 0.8, 0.7, 0.6, 0.5, -0.1, 0.5, 0.001), seuil=0.0125)
    assert cle == "non_demontre"


def test_verdict_non_demontre_si_le_gain_ne_tient_pas_a_trois_jours():
    cle, _ = verdict(evaluation(0.9, 0.8, 0.5, 0.2, 0.1, 0.4, 0.5, 0.001), seuil=0.0125)
    assert cle == "non_demontre"


def test_verdict_le_seuil_est_respecte_a_la_limite():
    assert verdict(evaluation(0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.5, 0.0125), seuil=0.0125)[0] == "demontre"
    assert verdict(evaluation(0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.5, 0.0126), seuil=0.0125)[0] == "non_demontre"

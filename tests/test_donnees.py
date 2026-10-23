"""Tests des fichiers de donnees publies : JSON valide (pas de NaN), structure attendue, coherence des verdicts."""
import json
import math
from pathlib import Path

import pytest

from pipeline.analysis.strategies_engine import verdict

DATA = Path(__file__).resolve().parents[1] / "data"
FICHIERS = sorted(DATA.glob("*.json"))


def refuser_constante(nom):
    raise ValueError(f"valeur interdite dans un JSON : {nom}")


def lire(fichier):
    return json.loads(fichier.read_text(encoding="utf-8"), parse_constant=refuser_constante)


@pytest.mark.parametrize("fichier", FICHIERS, ids=lambda f: f.name)
def test_chaque_fichier_de_donnees_est_un_json_valide_sans_nan(fichier):
    """Le navigateur refuse un JSON contenant NaN : l'onglet concerne resterait vide (c'est deja arrive au trafic maritime)."""
    lire(fichier)


def test_il_y_a_bien_des_fichiers_a_tester():
    assert len(FICHIERS) >= 10


# ---------------------------------------------------------------- strategies
@pytest.mark.parametrize("nom", ["strategies.json", "strategies_gaz.json"])
def test_strategies_structure_et_valeurs_plausibles(nom):
    d = lire(DATA / nom)
    assert d["meta"]["nb_tests"] == 4
    assert d["meta"]["seuil_corrige"] == pytest.approx(0.05 / 4, abs=1e-4)
    assert len(d["signaux"]) == 4
    assert 0 <= d["reference"]["p_valeur"] <= 1
    for s in d["signaux"]:
        assert 0 <= s["p_valeur"] <= 1
        assert s["verdict"] in ("demontre", "non_demontre", "artefact")
        assert [r["jours"] for r in s["retard"]] == [0, 1, 2, 3, 5]
        assert len(s["courbe"]["dates"]) == len(s["courbe"]["strategie"])
        assert all(v > 0 for v in s["courbe"]["strategie"]), "la courbe de performance doit rester positive (echelle logarithmique)"
        assert math.isfinite(s["metriques"]["annualise_pct"])
        assert -100 <= s["metriques"]["max_drawdown_pct"] <= 0
        assert 0 <= s["metriques"]["jours_en_position_pct"] <= 100
        assert s["etat"]["libelle"]


@pytest.mark.parametrize("nom", ["strategies.json", "strategies_gaz.json"])
def test_le_verdict_publie_est_celui_de_la_regle_appliquee_aux_chiffres_affiches(nom):
    d = lire(DATA / nom)
    for s in d["signaux"]:
        evaluation = {"retard": s["retard"], "sous_periodes": s["sous_periodes"], "p_valeur": s["p_valeur"]}
        cle, _ = verdict(evaluation, d["meta"]["seuil_corrige"])
        assert cle == s["verdict"], f"{s['nom']} : verdict publie {s['verdict']}, regle appliquee {cle}"


# ---------------------------------------------------------------- autres fichiers
def test_trafic_maritime_six_detroits_avec_des_valeurs():
    d = lire(DATA / "maritime.json")
    assert len(d["detroits"]) == 6
    for x in d["detroits"]:
        assert x["actuel_7j"] is not None and x["reference"] > 0 and x["zscore"] is not None
        assert len(x["serie"]) == 90


def test_risque_du_brent_coherent():
    r = lire(DATA / "risk.json")["brent"]
    assert r["risque"]["es95"] >= r["risque"]["var95"] > 0
    assert r["parametres"]["kappa"] > 0 and r["parametres"]["sigma_quotidien"] > 0
    futur = r["futur"]
    assert all(futur["p5"][i] <= futur["p50"][i] <= futur["p95"][i] for i in range(len(futur["dates"])))


def test_series_de_prix_ont_des_dates_et_des_valeurs_de_meme_longueur():
    for nom in ("oil", "gas", "electricity"):
        d = lire(DATA / f"{nom}.json")
        for cle, valeurs in d["series"].items():
            assert len(valeurs) == len(d["dates"]), f"{nom}.{cle}"


def test_ecart_brent_wti_est_la_difference_des_prix():
    d = lire(DATA / "oil.json")["series"]
    for b, w, s in zip(d["brent"], d["wti"], d["spread"]):
        if None not in (b, w, s):
            assert s == pytest.approx(b - w, abs=0.011)


def test_ecart_france_allemagne_est_la_difference_des_prix():
    d = lire(DATA / "electricity.json")["series"]
    for f, a, s in zip(d["fr"], d["de_lu"], d["spread_fr_de"]):
        if None not in (f, a, s):
            assert s == pytest.approx(f - a, abs=0.011)


def test_ecarts_de_gaz_sont_coherents_avec_leurs_composantes():
    g = lire(DATA / "gas_analysis.json")
    e, n = g["ecart"], g["gnl"]
    for t, h, x in zip(e["ttf"], e["hh_eur"], e["ecart"]):
        assert x == pytest.approx(t - h, abs=0.011)
    for j, t, x in zip(n["jkm"], n["ttf_usd"], n["ecart"]):
        assert x == pytest.approx(j - t, abs=0.011)

"""Tests des regles de trading (petrole et gaz) : signaux, hysteresis, saisonnalite sans regard dans le futur."""
import numpy as np
import pandas as pd
import pytest

try:                                    # ces modules importent fredapi / yfinance : on saute les tests si l'environnement ne les a pas
    from pipeline.analysis import strategies_gas as gaz
    from pipeline.analysis import strategies_oil as petrole
except Exception as erreur:             # pragma: no cover
    pytest.skip(f"modules de strategies indisponibles : {erreur}", allow_module_level=True)


def jours(n, debut="2010-01-04"):
    return pd.bdate_range(debut, periods=n)


# ---------------------------------------------------------------- petrole : tendance et moyennes mobiles
def test_tendance_acheteuse_sur_un_prix_qui_monte_et_hors_marche_au_debut():
    brent = pd.Series(np.linspace(50, 100, 300), index=jours(300))
    rend, position, _, etat, _ = petrole.regle_momentum(brent)
    assert (position.iloc[:63] == 0).all()                    # pas assez d'historique
    assert (position.iloc[63:] == 1).all()
    assert etat.startswith("Acheteur")


def test_tendance_vendeuse_sur_un_prix_qui_baisse():
    brent = pd.Series(np.linspace(100, 50, 300), index=jours(300))
    _, position, _, etat, _ = petrole.regle_momentum(brent)
    assert (position.iloc[63:] == -1).all()
    assert etat.startswith("Vendeur")


def test_moyennes_mobiles_hors_marche_avant_200_jours():
    brent = pd.Series(np.linspace(50, 100, 400), index=jours(400))
    _, position, _, _, _ = petrole.regle_moyennes(brent)
    assert (position.iloc[:199] == 0).all()
    assert (position.iloc[200:] == 1).all()


def test_moyennes_mobiles_vendeuses_en_baisse():
    brent = pd.Series(np.linspace(100, 50, 400), index=jours(400))
    _, position, _, _, _ = petrole.regle_moyennes(brent)
    assert (position.iloc[200:] == -1).all()


# ---------------------------------------------------------------- ecarts : entree, maintien, sortie
def serie_ecart_avec_pic(n=330, debut_pic=300, fin_pic=305, hauteur=12.0):
    """Ecart qui alterne entre -0,5 et +0,5 (jamais a plus de 1 ecart-type de sa moyenne : aucune entree parasite), avec un pic."""
    e = np.where(np.arange(n) % 2 == 0, 0.5, -0.5)
    e[debut_pic:fin_pic] += hauteur
    return pd.Series(e, index=jours(n))


def test_ecart_gaz_entre_vendeur_pendant_le_pic_puis_sort():
    ecart = serie_ecart_avec_pic()
    base = pd.Series(100.0, index=ecart.index)
    _, position, cout, _, _, coupure = gaz.regle_ecart(ecart, base)
    assert (position.iloc[:300] == 0).all()                   # avant le pic : aucun signal
    assert position.iloc[300] == -1                           # ecart anormalement haut : on parie sur sa baisse
    assert (position.iloc[300:305] == -1).all()               # maintien pendant le pic
    assert position.iloc[-1] == 0                             # retour a la normale : sortie
    assert (position != 1).all()
    assert cout == pytest.approx(gaz.COUT_PAR_JAMBE)          # normalise par l'exposition totale : 1 x cout
    assert coupure == "2022-01-01"


def test_ecart_gaz_entre_acheteur_quand_l_ecart_s_effondre():
    ecart = serie_ecart_avec_pic(hauteur=-12.0)
    base = pd.Series(100.0, index=ecart.index)
    _, position, _, _, _, _ = gaz.regle_ecart(ecart, base)
    assert position.iloc[300] == 1


def test_ecart_gaz_rendement_rapporte_a_l_exposition_de_la_veille():
    ecart = pd.Series([1.0, 2.0, 4.0] + [4.0] * 300, index=jours(303))
    base = pd.Series([10.0, 10.0, 20.0] + [20.0] * 300, index=ecart.index)
    rend, _, _, _, _, _ = gaz.regle_ecart(ecart, base)
    assert rend.iloc[1] == pytest.approx(1.0 / 10.0)
    assert rend.iloc[2] == pytest.approx(2.0 / 10.0)          # variation de 2 rapportee a la base de la VEILLE
    assert rend.iloc[3] == pytest.approx(0.0)


def test_ecart_petrole_meme_logique_d_entree_et_de_sortie():
    idx = jours(330)
    rng = np.random.default_rng(1)
    wti = pd.Series(60.0, index=idx)
    brent = wti + 4 + rng.normal(0, 0.3, 330)
    brent.iloc[300:305] += 8
    _, position, cout, _, prix_ref = petrole.regle_ecart(brent, wti)
    assert position.iloc[301] == -1
    assert position.iloc[-1] == 0
    assert cout == pytest.approx(2 * petrole.COUT_PAR_JAMBE)  # deux jambes
    assert prix_ref is None


# ---------------------------------------------------------------- gaz : saisonnalite sans regard dans le futur
def prix_gaz_saisonniers(annees=17, graine=0):
    idx = pd.bdate_range("2000-01-03", periods=annees * 261)
    rng = np.random.default_rng(graine)
    r = rng.normal(0, 0.01, len(idx)) + np.where(idx.month == 10, 0.01, 0.0)   # octobre monte toujours
    return pd.Series(10 * np.exp(np.cumsum(r)), index=idx)


def test_saisonnalite_hors_marche_avant_cinq_ans_d_historique():
    hh = prix_gaz_saisonniers()
    _, position, _, _, _, _ = gaz.regle_saison(hh)
    assert (position[position.index.year <= 2004] == 0).all()


def test_saisonnalite_apprend_que_octobre_monte():
    hh = prix_gaz_saisonniers()
    _, position, _, _, _, _ = gaz.regle_saison(hh)
    octobre = position[(position.index.year >= 2006) & (position.index.month == 10)]
    assert (octobre == 1).all()


def test_saisonnalite_ne_regarde_jamais_l_annee_en_cours_ni_le_futur():
    hh = prix_gaz_saisonniers()
    _, position, _, _, _, _ = gaz.regle_saison(hh)
    modifie = hh.copy()
    modifie[modifie.index.year == 2010] *= np.where(np.arange((modifie.index.year == 2010).sum()) % 2 == 0, 3.0, 0.2)   # annee 2010 bouleversee
    _, position2, _, _, _, _ = gaz.regle_saison(modifie)
    assert position[position.index.year <= 2010].equals(position2[position2.index.year <= 2010])   # rien n'a bouge jusqu'en 2010 incluse


# ---------------------------------------------------------------- outils communs
def test_courbe_mensuelle_commence_a_100_et_suit_la_strategie():
    net = pd.Series(0.01, index=jours(60))
    c = petrole.courbe_mensuelle(net, None)
    assert c["strategie"][0] > 100
    assert len(c["dates"]) == len(c["strategie"])
    assert "reference" not in c


def test_depuis_quand_renvoie_la_date_du_dernier_changement():
    position = pd.Series([0, 0, 1, 1, -1, -1, -1], index=jours(7), dtype=float)
    assert petrole.depuis_quand(position) == position.index[4].strftime("%Y-%m-%d")


def test_libelle_position():
    assert petrole.libelle_position(1.0, "a", "v", "n") == "a"
    assert petrole.libelle_position(-1.0, "a", "v", "n") == "v"
    assert petrole.libelle_position(0.0, "a", "v", "n") == "n"

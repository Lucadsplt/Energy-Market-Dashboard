"""Tests de la fiche d'idees : lectures, comptage, actualites, fichier produit."""
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from pipeline.analysis import idees

RACINE = Path(__file__).resolve().parents[1]
MAINTENANT = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


def ind(lecture, fiabilite="non_demontre", compte=True):
    return {"cle": "x", "nom": "x", "valeur": "", "lecture": lecture, "detail": "", "fiabilite": fiabilite, "compte": compte}


# ---------------------------------------------------------------- lectures
def test_lecture_d_une_position():
    assert idees.lecture_position(1.0) == "haussier"
    assert idees.lecture_position(-1.0) == "baissier"
    assert idees.lecture_position(0.0) == "neutre"


def test_seuls_les_indicateurs_issus_d_une_regle_sont_comptes():
    liste = [ind("haussier"), ind("haussier"), ind("baissier"), ind("neutre"), ind("contexte", compte=False), ind("haussier", compte=False)]
    s = idees.synthese(liste)
    assert (s["haussiers"], s["baissiers"], s["neutres"], s["regles_comptees"]) == (2, 1, 1, 4)


def test_les_regles_demontrees_sont_comptees_a_part():
    s = idees.synthese([ind("haussier", "demontre"), ind("haussier", "non_demontre"), ind("baissier", "artefact")])
    assert s["regles_demontrees"] == 1 and s["regles_comptees"] == 3


def test_la_phrase_ne_promet_rien_quand_aucune_regle_n_est_demontree():
    phrase = idees.phrase_synthese(idees.synthese([ind("haussier"), ind("haussier")]))
    assert "acheteur" in phrase
    assert "Aucune n'a démontré" in phrase


def test_la_phrase_reconnait_une_regle_demontree():
    phrase = idees.phrase_synthese(idees.synthese([ind("haussier", "demontre"), ind("baissier")]))
    assert "1 règle(s) sur 2" in phrase


def test_la_phrase_gere_l_egalite_et_l_absence_de_regle():
    assert "pas de sens clair" in idees.phrase_synthese(idees.synthese([ind("haussier"), ind("baissier")]))
    assert "Aucune règle testée" in idees.phrase_synthese(idees.synthese([ind("contexte", compte=False)]))


def test_la_phrase_suit_le_verdict_reellement_publie():
    assert "artefact" in idees.texte_verdict("artefact")
    assert "pas démontrée" in idees.texte_verdict("non_demontre")
    assert "a démontré" in idees.texte_verdict("demontre")


# ---------------------------------------------------------------- centile COT et z-score
def test_centile_cot_compte_les_semaines_strictement_inferieures():
    net = np.arange(156, dtype=float)                       # croissant : la derniere depasse les 155 precedentes
    assert idees.centile_cot(net) == pytest.approx(1.0)
    assert idees.centile_cot(net[::-1]) == pytest.approx(0.0)
    net2 = np.concatenate([np.zeros(155), [0.0]])           # toutes egales : aucune strictement inferieure
    assert idees.centile_cot(net2) == pytest.approx(0.0)


def test_centile_cot_refuse_un_historique_trop_court():
    assert idees.centile_cot(np.arange(100, dtype=float)) is None


def test_centile_cot_utilise_les_156_dernieres_semaines():
    net = np.concatenate([np.full(500, 99.0), np.arange(156, dtype=float)])    # le passe lointain ne compte pas
    assert idees.centile_cot(net) == pytest.approx(1.0)


def test_zscore_courant():
    serie = list(np.random.default_rng(0).normal(0, 1, 251)) + [10.0]
    z = idees.zscore_courant(serie)
    fenetre = np.array(serie[-252:])
    assert z == pytest.approx((10.0 - fenetre.mean()) / fenetre.std(ddof=1))
    assert idees.zscore_courant(serie[:100]) is None


def test_volatilite_quotidienne():
    prix = [100 * math.exp(0.02 * ((-1) ** i)) for i in range(30)]       # +-2 % en alternance
    v = idees.volatilite_quotidienne(prix)
    assert v == pytest.approx(np.std([0.04, -0.04] * 10, ddof=1) * 100, rel=0.06)
    assert idees.volatilite_quotidienne([1.0, 2.0]) is None


# ---------------------------------------------------------------- actualites
def article(titre, jours_avant, source="Test"):
    return {"titre": titre, "source": source, "lien": "https://exemple.org/a", "date": (MAINTENANT - timedelta(days=jours_avant)).isoformat()}


def test_classement_par_marche():
    assert idees.classer_marches("Brent crude jumps") == ["petrole"]
    assert "gaz" in idees.classer_marches("European gas prices")
    assert idees.classer_marches("Football results") == []
    assert idees.classer_marches(None) == []


def test_actualites_comptent_par_fenetre_et_par_marche():
    arts = [article("Oil rises", 0.2), article("Oil falls", 3), article("Crude slump", 20), article("Gas surges", 1), article("Sports", 1)]
    a = idees.actualites(arts, "petrole", MAINTENANT)
    assert (a["nb_24h"], a["nb_7j"], a["nb_30j"]) == (1, 2, 3)
    assert a["rythme_hebdo_30j"] == pytest.approx(3 / 30 * 7, abs=0.05)
    assert [x["titre"] for x in a["derniers"]][0] == "Oil rises"          # les plus recents d'abord


def test_actualites_ignorent_les_articles_sans_date():
    a = idees.actualites([{"titre": "Oil news", "date": None, "lien": "https://x"}, article("Oil ok", 1)], "petrole", MAINTENANT)
    assert a["nb_30j"] == 1


def test_actualites_limitent_le_nombre_de_titres():
    a = idees.actualites([article(f"Oil {i}", i * 0.1) for i in range(30)], "petrole", MAINTENANT, nb_titres=4)
    assert len(a["derniers"]) == 4


def test_les_mots_cles_sont_identiques_a_ceux_de_la_page_news():
    """Si on modifie les mots-cles de js/news.js sans modifier idees.py, les deux pages classeraient les articles differemment."""
    js = (RACINE / "js" / "news.js").read_text(encoding="utf-8")
    bloc = js[js.index("const MOTS"):js.index("};", js.index("const MOTS"))]
    for marche, mots in idees.MOTS.items():
        extrait = re.search(marche + r":\s*\[(.*?)\]", bloc, re.S).group(1)
        assert re.findall(r'"([^"]+)"', extrait) == mots, marche


# ---------------------------------------------------------------- fichier produit
@pytest.fixture(scope="module")
def fiche():
    return json.loads((RACINE / "data" / "idees.json").read_text(encoding="utf-8"))


def test_la_fiche_couvre_les_trois_marches(fiche):
    assert set(fiche["marches"]) == {"petrole", "gaz", "electricite"}


def test_chaque_indicateur_a_une_lecture_et_une_fiabilite_valides(fiche):
    for cle, m in fiche["marches"].items():
        assert m["indicateurs"], cle
        for i in m["indicateurs"]:
            assert i["lecture"] in ("haussier", "baissier", "neutre", "contexte")
            assert i["fiabilite"] in ("demontre", "non_demontre", "artefact", "non_teste")
            if i["lecture"] != "contexte":
                assert i["compte"], "un indicateur directionnel doit provenir d'une regle testee"
            if i["compte"]:
                assert i["fiabilite"] != "non_teste", "un indicateur compte doit avoir un verdict"


def test_la_synthese_correspond_aux_indicateurs(fiche):
    for m in fiche["marches"].values():
        assert m["synthese"] == idees.synthese(m["indicateurs"])


def test_aucun_indicateur_non_teste_n_est_directionnel(fiche):
    for m in fiche["marches"].values():
        for i in m["indicateurs"]:
            if i["fiabilite"] == "non_teste":
                assert i["lecture"] == "contexte"


def test_les_verdicts_affiches_sont_ceux_de_l_onglet_strategies(fiche):
    for fichier, marche in (("strategies.json", "petrole"), ("strategies_gaz.json", "gaz")):
        strat = json.loads((RACINE / "data" / fichier).read_text(encoding="utf-8"))
        verdicts = {s["cle"]: s["verdict"] for s in strat["signaux"]}
        for i in fiche["marches"][marche]["indicateurs"]:
            if i["cle"] in verdicts:
                assert i["fiabilite"] == verdicts[i["cle"]], i["nom"]


def test_les_instruments_ont_un_prix_et_une_volatilite_positifs(fiche):
    for m in fiche["marches"].values():
        for x in m["instruments"]:
            assert x["prix"] > 0 and x["sigma_quotidien_pct"] > 0 and x["multiplicateur"] > 0


def test_aucun_conseil_dans_les_textes(fiche):
    interdits = re.compile(r"\b(achetez|vendez|nous recommandons|il faut acheter|il faut vendre)\b", re.I)
    for m in fiche["marches"].values():
        textes = [m["phrase"]] + [i["detail"] + i["valeur"] for i in m["indicateurs"]]
        assert not any(interdits.search(t) for t in textes)

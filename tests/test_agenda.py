"""Tests de l'agenda : fuseaux horaires, publications hebdomadaires, filtrage des evenements, fichier de reference."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pipeline.analysis import agenda

RACINE = Path(__file__).resolve().parents[1]


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


REGLE_MERCREDI = {"jour_semaine": 2, "heure": "10:30"}


# ---------------------------------------------------------------- publications hebdomadaires
def test_une_publication_du_mercredi_tombe_bien_un_mercredi():
    for iso in agenda.occurrences(REGLE_MERCREDI, utc(2026, 10, 26, 8), nombre=4):
        assert agenda.horodatage(iso).astimezone(agenda.NEW_YORK).weekday() == 2


def test_l_heure_americaine_suit_le_passage_a_l_heure_d_hiver():
    """10 h 30 a New York = 14 h 30 UTC en heure d'ete (jusqu'au 1er novembre 2026), 15 h 30 UTC ensuite."""
    avant, apres = agenda.occurrences(REGLE_MERCREDI, utc(2026, 10, 26, 8), nombre=2)
    assert avant == "2026-10-28T14:30:00Z"
    assert apres == "2026-11-04T15:30:00Z"


def test_la_publication_du_jour_est_comptee_tant_qu_elle_n_a_pas_eu_lieu():
    assert agenda.occurrences(REGLE_MERCREDI, utc(2026, 10, 28, 12))[0] == "2026-10-28T14:30:00Z"
    assert agenda.occurrences(REGLE_MERCREDI, utc(2026, 10, 28, 15))[0] == "2026-11-04T15:30:00Z"     # deja passee


def test_les_dates_sont_dans_l_ordre_et_dans_le_futur():
    maintenant = utc(2026, 10, 26, 8)
    for regle in agenda.HEBDOMADAIRES:
        dates = [agenda.horodatage(d) for d in agenda.occurrences(regle, maintenant, nombre=3)]
        assert dates == sorted(dates) and len(dates) == 3
        assert all(d >= maintenant for d in dates)


def test_les_regles_hebdomadaires_sont_bien_formees():
    for r in agenda.HEBDOMADAIRES:
        assert 0 <= r["jour_semaine"] <= 4
        assert set(r["marches"]) <= agenda.MARCHES
        assert r["lien"].startswith("https://")


# ---------------------------------------------------------------- evenements a venir
def evt(**kw):
    base = {"titre": "x", "type": "politique", "marches": ["petrole"], "importance": "faible", "statut": "confirme", "source": "s", "lien": None}
    return {**base, **kw}


def test_les_evenements_passes_sont_retires_et_les_autres_tries():
    liste = [evt(jour="2026-12-01"), evt(jour="2026-10-01"), evt(quand="2026-11-04T10:00:00Z"), evt(jour="2026-10-26")]
    reste = agenda.a_venir(liste, utc(2026, 10, 26, 15))
    assert [e.get("jour") or e["quand"][:10] for e in reste] == ["2026-10-26", "2026-11-04", "2026-12-01"]


def test_un_evenement_de_plusieurs_jours_reste_affiche_jusqu_a_sa_fin():
    conf = evt(jour="2026-11-09", fin_jour="2026-11-20")
    assert agenda.a_venir([conf], utc(2026, 11, 15, 12)) == [conf]
    assert agenda.a_venir([conf], utc(2026, 11, 21, 0, 1)) == []


def test_un_evenement_avec_heure_reste_visible_quelques_heures_apres_son_debut():
    e = evt(quand="2026-10-28T18:00:00Z")
    assert agenda.a_venir([e], utc(2026, 10, 28, 19, 30)) == [e]       # la conference de presse peut durer
    assert agenda.a_venir([e], utc(2026, 10, 28, 22, 0)) == []


# ---------------------------------------------------------------- controle de forme
def test_verifier_accepte_un_evenement_correct_et_refuse_les_autres():
    agenda.verifier([evt(jour="2026-11-01")])
    with pytest.raises(AssertionError):
        agenda.verifier([evt(jour="2026-11-01", quand="2026-11-01T10:00:00Z")])        # les deux a la fois
    with pytest.raises(AssertionError):
        agenda.verifier([evt(jour="2026-11-20", fin_jour="2026-11-09")])               # fin avant le debut
    with pytest.raises(AssertionError):
        agenda.verifier([evt(jour="2026-11-01", statut="peut-etre")])
    with pytest.raises(AssertionError):
        agenda.verifier([evt(jour="2026-11-01", lien="http://pas-securise.example")])
    with pytest.raises(AssertionError):
        agenda.verifier([evt(jour="2026-11-01", source="")])


# ---------------------------------------------------------------- fichier de reference et fichier publie
def test_le_fichier_de_reference_est_valide():
    brut = json.loads(agenda.REFERENCE.read_text(encoding="utf-8"))
    agenda.verifier(brut["evenements"])
    assert datetime.fromisoformat(brut["verifie_le"])


def test_toute_date_non_confirmee_est_signalee_comme_telle():
    brut = json.loads(agenda.REFERENCE.read_text(encoding="utf-8"))
    for e in brut["evenements"]:
        if e["statut"] == "a_confirmer":
            assert "confirm" in (e["titre"] + e["note"]).lower()


def test_les_dates_de_reunion_avec_heure_sont_en_utc():
    brut = json.loads(agenda.REFERENCE.read_text(encoding="utf-8"))
    for e in brut["evenements"]:
        if "quand" in e:
            assert e["quand"].endswith("Z")


def test_le_fichier_publie_a_la_structure_attendue():
    d = json.loads((RACINE / "data" / "agenda.json").read_text(encoding="utf-8"))
    assert {"genere", "verifie_le", "evenements", "hebdomadaires"} <= set(d)
    assert len(d["hebdomadaires"]) == len(agenda.HEBDOMADAIRES)
    assert all(len(h["prochaines"]) == 2 for h in d["hebdomadaires"])


def test_construire_ne_garde_que_le_futur():
    d = agenda.construire(utc(2027, 6, 1))
    assert d["evenements"] == []                           # tout est passe : l'agenda doit alors etre mis a jour
    assert d["hebdomadaires"]

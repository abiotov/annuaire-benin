"""Tests de la normalisation des noms d'entreprise."""

from annuaire_benin.dedupe.names import blocking_tokens, normalize, tokens


def test_normalize_accents_case_punctuation():
    assert normalize("Établissement Générale - Bénin") == "ETABLISSEMENT GENERALE BENIN"
    assert normalize("  KOFFI   &  FRERES ") == "KOFFI FRERES"
    assert normalize(None) == ""
    assert normalize("") == ""


def test_tokens():
    assert tokens("ETS KOFFI-BENIN") == ["ETS", "KOFFI", "BENIN"]


def test_blocking_tokens_filters_generic_words():
    # ETS, BENIN, SERVICES sont génériques ; KOFFI est discriminant.
    assert blocking_tokens("ETS KOFFI BENIN SERVICES") == ["KOFFI"]
    # Les mots trop courts et les nombres ne bloquent pas.
    assert blocking_tokens("AB 2000 TRANSPORT") == ["TRANSPORT"]

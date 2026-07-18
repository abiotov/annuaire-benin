"""Tests du lexique mot-clé -> secteur de la recherche."""

from annuaire_benin.atlas.lexicon import build_lexicon, tokens
from annuaire_benin.classify.taxonomy import SECTORS


def test_lexicon_maps_distinctive_words():
    lexicon = build_lexicon()
    assert lexicon["quincaillerie"] == "commerce-construction-quincaillerie"
    assert lexicon["pressing"] == "services-divers"
    assert lexicon["coiffure"] == "services-beaute"
    assert lexicon["transport"] == "transport-logistique"
    assert lexicon["anacarde"] == "commerce-agricole"
    assert lexicon["btp"] == "btp-construction"


def test_lexicon_rejects_cross_sector_words():
    lexicon = build_lexicon()
    # « vente » et « produits » traversent une dizaine de secteurs : la
    # règle de dominance doit les écarter.
    assert "vente" not in lexicon
    assert "produits" not in lexicon


def test_lexicon_values_are_valid_sectors():
    assert set(build_lexicon().values()) <= set(SECTORS)


def test_tokens_folds_accents_and_stopwords():
    assert tokens("Achat et vente de bâches") == ["baches"]

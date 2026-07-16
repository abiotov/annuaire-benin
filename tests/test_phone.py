"""Tests de la normalisation des numéros de téléphone béninois.

Les numéros utilisés ici sont plausibles mais fictifs (jamais tirés
des données réelles), conformément aux règles de confidentialité du
projet (docs/architecture.md).
"""

import pytest

from annuaire_benin.contacts.phone import PhoneStatus, extract_all, normalize


@pytest.mark.parametrize(
    ("raw", "e164", "status"),
    [
        # Ancien plan à 8 chiffres : préfixe 01 ajouté.
        ("97000001", "+2290197000001", PhoneStatus.MIGRATED),
        ("40000001", "+2290140000001", PhoneStatus.MIGRATED),
        ("61000001", "+2290161000001", PhoneStatus.MIGRATED),
        ("21000001", "+2290121000001", PhoneStatus.MIGRATED),  # ligne fixe
        # Nouveau plan à 10 chiffres : conservé tel quel.
        ("0197000001", "+2290197000001", PhoneStatus.ALREADY_MIGRATED),
        # Mise en forme variée.
        ("97 00 00 01", "+2290197000001", PhoneStatus.MIGRATED),
        ("97-00-00-01", "+2290197000001", PhoneStatus.MIGRATED),
        ("+229 01 97 00 00 01", "+2290197000001", PhoneStatus.ALREADY_MIGRATED),
        ("0022997000001", "+2290197000001", PhoneStatus.MIGRATED),
        ("22997000001", "+2290197000001", PhoneStatus.MIGRATED),
        ("2290197000001", "+2290197000001", PhoneStatus.ALREADY_MIGRATED),
        # Zéro de tête perdu par un stockage numérique.
        (197000001, "+2290197000001", PhoneStatus.LEADING_ZERO_RESTORED),
        ("197000001", "+2290197000001", PhoneStatus.LEADING_ZERO_RESTORED),
        # 8 chiffres commençant par 01 : ni ancien plan, ni nouveau complet.
        ("01970001", None, PhoneStatus.SUSPICIOUS_SHORT_01),
        # Invalides.
        ("31000001", None, PhoneStatus.INVALID),  # premier chiffre hors plan
        ("1234", None, PhoneStatus.INVALID),
        ("abc", None, PhoneStatus.INVALID),
        ("0812345678", None, PhoneStatus.INVALID),  # 10 chiffres hors préfixe 01
        # Vides.
        ("", None, PhoneStatus.EMPTY),
        (None, None, PhoneStatus.EMPTY),
        ("   ", None, PhoneStatus.EMPTY),
    ],
)
def test_normalize(raw, e164, status):
    result = normalize(raw)
    assert result.e164 == e164
    assert result.status == status


def test_normalize_rejects_multiple_numbers():
    assert normalize("97000001 / 96000002").status == PhoneStatus.INVALID


def test_national_property():
    assert normalize("97000001").national == "0197000001"
    assert normalize("abc").national is None


def test_extract_all_splits_on_separator():
    results = extract_all("97 00 00 01 / 96 00 00 02")
    assert [r.e164 for r in results] == ["+2290197000001", "+2290196000002"]
    assert all(r.status == PhoneStatus.MIGRATED for r in results)


def test_extract_all_single_and_empty():
    assert extract_all("97000001")[0].e164 == "+2290197000001"
    assert extract_all(None)[0].status == PhoneStatus.EMPTY
    assert extract_all("aucun")[0].status == PhoneStatus.INVALID

"""Tests de la validation des adresses email.

Les adresses utilisées ici sont fictives (domaines example.*), jamais
tirées des données réelles, conformément aux règles de confidentialité
du projet (docs/architecture.md).
"""

import pytest

from annuaire_benin.contacts.emails import EmailStatus, normalize


@pytest.mark.parametrize(
    ("raw", "normalized", "status"),
    [
        ("contact@example.com", "contact@example.com", EmailStatus.VALID),
        ("CONTACT@EXAMPLE.COM", "contact@example.com", EmailStatus.VALID),
        ("  boutique.01@example.org ", "boutique.01@example.org", EmailStatus.VALID),
        ("atelier@example.fr", "atelier@example.fr", EmailStatus.VALID),
        ("jean dupont@example.com", "jeandupont@example.com", EmailStatus.VALID),
        # Invalides.
        ("aucun", None, EmailStatus.INVALID),
        ("97000001", None, EmailStatus.INVALID),
        ("test@", None, EmailStatus.INVALID),
        ("@example.com", None, EmailStatus.INVALID),
        ("test@example", None, EmailStatus.INVALID),
        # Vides.
        ("", None, EmailStatus.EMPTY),
        (None, None, EmailStatus.EMPTY),
        ("   ", None, EmailStatus.EMPTY),
    ],
)
def test_normalize(raw, normalized, status):
    result = normalize(raw)
    assert result.normalized == normalized
    assert result.status == status

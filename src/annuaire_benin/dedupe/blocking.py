"""Étape 2b, temps 1 : génération des paires candidates (blocking).

On ne compare jamais les 27 milliards de paires possibles : une paire
n'est candidate que si les deux entités partagent au moins un canal :

- même téléphone valide (les numéros tronqués ne servent jamais de
  signal d'identité : deux troncatures identiques peuvent venir de
  numéros différents) ;
- même email normalisé ;
- un mot de nom discriminant en commun (blocage par token rare).

Garde-fous de volume : un contact ou un token partagé par trop
d'entités ne génère pas de paires (il n'est pas discriminant), et ce
qui est écarté est compté, jamais ignoré en silence.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

# Au-delà de ces tailles de bloc, la clé n'est plus un signal d'identité.
CONTACT_BLOCK_CAP = 10
TOKEN_BLOCK_CAP = 15

CHANNEL_PHONE = "phone"
CHANNEL_EMAIL = "email"
CHANNEL_NAME = "name"


@dataclass(frozen=True)
class BlockingStats:
    """Bilan chiffré de la génération de candidats."""

    pairs_by_channel: dict[str, int]
    oversized_blocks: dict[str, int]  # blocs écartés car au-dessus du plafond
    total_pairs: int


def candidate_pairs(
    entities: list[tuple[int, list[str], str | None, str | None]],
) -> tuple[dict[tuple[int, int], set[str]], BlockingStats]:
    """Génère les paires candidates.

    ``entities`` : liste de (id, tokens de blocage, phone_e164, email_norm).
    Retourne les paires (id_a < id_b) avec l'ensemble des canaux qui les
    ont proposées, et le bilan chiffré.
    """
    blocks: dict[str, dict[str, list[int]]] = {
        CHANNEL_PHONE: defaultdict(list),
        CHANNEL_EMAIL: defaultdict(list),
        CHANNEL_NAME: defaultdict(list),
    }
    for entity_id, tokens, phone_e164, email_norm in entities:
        if phone_e164:
            blocks[CHANNEL_PHONE][phone_e164].append(entity_id)
        if email_norm:
            blocks[CHANNEL_EMAIL][email_norm].append(entity_id)
        for token in set(tokens):
            blocks[CHANNEL_NAME][token].append(entity_id)

    caps = {
        CHANNEL_PHONE: CONTACT_BLOCK_CAP,
        CHANNEL_EMAIL: CONTACT_BLOCK_CAP,
        CHANNEL_NAME: TOKEN_BLOCK_CAP,
    }
    pairs: dict[tuple[int, int], set[str]] = defaultdict(set)
    pairs_by_channel = dict.fromkeys(blocks, 0)
    oversized = dict.fromkeys(blocks, 0)

    for channel, channel_blocks in blocks.items():
        for members in channel_blocks.values():
            if len(members) < 2:
                continue
            if len(members) > caps[channel]:
                oversized[channel] += 1
                continue
            for a, b in combinations(sorted(members), 2):
                pairs[(a, b)].add(channel)
                pairs_by_channel[channel] += 1

    stats = BlockingStats(
        pairs_by_channel=pairs_by_channel,
        oversized_blocks=oversized,
        total_pairs=len(pairs),
    )
    return dict(pairs), stats

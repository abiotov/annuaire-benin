"""Étape 2b, temps 3 : regroupement des fusions acceptées.

Les paires en zone de fusion forment un graphe ; les composantes
connexes deviennent les entités finales (union-find). Garde-fou anti
méga-cluster : par transitivité, un contact partagé pourrait coller en
chaîne des dizaines de fiches ; au-delà d'une taille limite, seule une
arête à score très élevé peut encore agrandir un groupe, et chaque
refus est compté.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_CLUSTER_SIZE = 12
GUARD_THRESHOLD = 0.92


@dataclass(frozen=True)
class ClusteringStats:
    clusters_merged: int  # unions effectuées
    edges_skipped_by_guard: int


class UnionFind:
    """Union-find avec suivi de la taille des groupes."""

    def __init__(self) -> None:
        self._parent: dict[int, int] = {}
        self._size: dict[int, int] = {}

    def find(self, item: int) -> int:
        parent = self._parent.setdefault(item, item)
        if parent == item:
            self._size.setdefault(item, 1)
            return item
        root = self.find(parent)
        self._parent[item] = root
        return root

    def size(self, item: int) -> int:
        return self._size[self.find(item)]

    def union(self, a: int, b: int) -> bool:
        """Fusionne les groupes de a et b ; False s'ils l'étaient déjà."""
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return False
        if self._size[root_a] < self._size[root_b]:
            root_a, root_b = root_b, root_a
        self._parent[root_b] = root_a
        self._size[root_a] += self._size[root_b]
        return True


def cluster(
    merge_edges: list[tuple[int, int, float]],
    all_ids: list[int],
) -> tuple[dict[int, int], ClusteringStats]:
    """Regroupe les entités reliées par les arêtes de fusion.

    Les arêtes sont traitées par score décroissant : les fusions les
    plus sûres construisent les groupes, les plus faibles ne peuvent
    plus créer de méga-cluster.

    Retourne (entité -> id de cluster, bilan). Chaque entité, fusionnée
    ou non, reçoit un cluster : l'id de son représentant.
    """
    uf = UnionFind()
    merged = 0
    skipped = 0

    for a, b, score in sorted(merge_edges, key=lambda edge: edge[2], reverse=True):
        would_be = uf.size(a) + uf.size(b) if uf.find(a) != uf.find(b) else uf.size(a)
        if would_be > MAX_CLUSTER_SIZE and score < GUARD_THRESHOLD:
            skipped += 1
            continue
        if uf.union(a, b):
            merged += 1

    assignment = {entity_id: uf.find(entity_id) for entity_id in all_ids}
    return assignment, ClusteringStats(clusters_merged=merged, edges_skipped_by_guard=skipped)

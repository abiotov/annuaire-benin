"""Tests du clustering et du garde-fou anti méga-cluster."""

from annuaire_benin.dedupe.clustering import (
    GUARD_THRESHOLD,
    MAX_CLUSTER_SIZE,
    UnionFind,
    cluster,
)


def test_union_find_merges_and_tracks_sizes():
    uf = UnionFind()
    assert uf.union(1, 2)
    assert uf.union(2, 3)
    assert not uf.union(1, 3)  # déjà dans le même groupe
    assert uf.size(1) == 3
    assert uf.find(1) == uf.find(3)


def test_cluster_assigns_every_entity():
    assignment, stats = cluster([(1, 2, 0.9)], all_ids=[1, 2, 3])
    assert assignment[1] == assignment[2]
    assert assignment[3] not in (None, assignment[1])
    assert stats.clusters_merged == 1


def test_guard_blocks_weak_edge_on_large_cluster():
    # Une chaîne d'arêtes moyennes qui dépasserait la taille limite :
    # la dernière arête faible doit être refusée et comptée.
    chain = [(i, i + 1, 0.85) for i in range(1, MAX_CLUSTER_SIZE + 2)]
    assignment, stats = cluster(chain, all_ids=list(range(1, MAX_CLUSTER_SIZE + 3)))
    assert stats.edges_skipped_by_guard >= 1
    sizes = {}
    for root in assignment.values():
        sizes[root] = sizes.get(root, 0) + 1
    assert max(sizes.values()) <= MAX_CLUSTER_SIZE


def test_guard_lets_very_strong_edge_through():
    chain = [(i, i + 1, GUARD_THRESHOLD) for i in range(1, MAX_CLUSTER_SIZE + 2)]
    _, stats = cluster(chain, all_ids=list(range(1, MAX_CLUSTER_SIZE + 3)))
    assert stats.edges_skipped_by_guard == 0

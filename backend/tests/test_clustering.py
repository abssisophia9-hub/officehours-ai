from types import SimpleNamespace

from app.ai.clustering import assign_cluster_id, cosine_similarity


def test_assign_cluster_id_starts_first_cluster(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")

    assert assign_cluster_id("I need help with recursion", []) == 1


def test_assign_cluster_id_reuses_similar_cluster(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
    existing_requests = [
        SimpleNamespace(id=1, text="I need help with recursion", cluster_id=7),
    ]

    cluster_id = assign_cluster_id(
        "Can you explain recursion?",
        existing_requests,
        similarity_threshold=0.5,
    )

    assert cluster_id == 7


def test_assign_cluster_id_starts_new_cluster_for_different_topic(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
    existing_requests = [
        SimpleNamespace(id=1, text="I need help with recursion", cluster_id=7),
    ]

    cluster_id = assign_cluster_id(
        "My project autograder is failing hidden tests.",
        existing_requests,
        similarity_threshold=0.5,
    )

    assert cluster_id == 8


def test_cosine_similarity_handles_empty_vectors():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0]) == 0.0

from app.services.room_reputation import compute_reputation, rank_tier, rooms_score


def test_quality_outweighs_volume():
    noisy = compute_reputation(rooms=8, solutions=8, accepted=0, helpful_votes=0)
    helper = compute_reputation(rooms=1, solutions=1, accepted=1, helpful_votes=1)
    assert helper.hilbert_weight > noisy.hilbert_weight
    assert helper.node_points >= 6
    assert rank_tier(rooms_score(helper.hilbert_weight)) != "Mentor" or helper.rooms_score > 0
    assert 0 <= helper.rooms_score < 1

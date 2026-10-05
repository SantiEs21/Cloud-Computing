import random

from decoder.matching import Sample, match

THRESHOLD = 10


def rand_hash(rng):
    return f"{rng.getrandbits(64):016x}"


def flip(h, bits, rng):
    """Simulates re-encoding noise: flip a few random bits."""
    v = int(h, 16)
    for b in rng.sample(range(64), bits):
        v ^= 1 << b
    return f"{v:016x}"


def trip(n, seed, jitter=0):
    rng = random.Random(seed)
    return [Sample(i * 500 + rng.randint(-jitter, jitter), rand_hash(rng)) for i in range(n)]


def excerpt(stored, start, n, noise=3, seed=1):
    """Query = samples start..start+n of the trip, with video time starting at 0 and a few bit flips."""
    rng = random.Random(seed)
    t0 = stored[start].t_ms
    return [Sample(s.t_ms - t0, flip(s.phash, noise, rng)) for s in stored[start:start + n]]


def test_excerpt_found_at_right_position():
    stored = trip(200, seed=1)
    r = match(excerpt(stored, 40, 20), stored, THRESHOLD)
    assert r["verdict"] == "AUTHENTIC"
    assert r["matched_pct"] == 100
    assert r["position_s"] == 20.0  # sample 40 * 0.5 s


def test_irregular_browser_timing():
    # stored timestamps jitter like a throttled browser tab; video samples are regular
    stored = trip(200, seed=2, jitter=120)
    query = [Sample(i * 500, flip(stored[60 + i].phash, 2, random.Random(i))) for i in range(20)]
    r = match(query, stored, THRESHOLD)
    assert r["verdict"] == "AUTHENTIC"
    assert abs(r["position_s"] - 30.0) <= 0.5


def test_partial_replacement_is_modified():
    stored = trip(200, seed=3)
    other = trip(200, seed=99)
    query = excerpt(stored, 10, 30)
    for i in range(10, 16):  # 3 s replaced by another video
        query[i] = Sample(query[i].t_ms, other[i].phash)
    r = match(query, stored, THRESHOLD)
    assert r["verdict"] == "MODIFIED"
    assert r["position_s"] == 5.0
    assert r["modified_sections"] == [{"from_s": 5.0, "to_s": 8.0}]


def test_extra_frames_at_start_shift():
    stored = trip(200, seed=4)
    rng = random.Random(5)
    black = [Sample(i * 500, rand_hash(rng)) for i in range(6)]  # 3 s of unrelated frames
    query = black + [Sample(3000 + s.t_ms, s.phash) for s in excerpt(stored, 0, 30)]
    r = match(query, stored, THRESHOLD)
    assert r["position_s"] == -3.0  # trip starts 3 s into the video
    assert r["modified_sections"] == [{"from_s": 0.0, "to_s": 3.0}]
    assert r["verdict"] == "MODIFIED"


def test_other_trip_is_no_match():
    r = match(excerpt(trip(200, seed=6), 0, 30), trip(200, seed=7), THRESHOLD)
    assert r["verdict"] == "NO MATCH"
    assert r["matched_pct"] < 30

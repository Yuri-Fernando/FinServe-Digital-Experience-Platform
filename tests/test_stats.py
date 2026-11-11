import pytest

from finserve.modules.analytics import stats


def test_two_proportion_ztest_known_values():
    r = stats.two_proportion_ztest(100, 1000, 130, 1000)
    assert r["z"] == pytest.approx(2.10, abs=0.01)
    assert 0.03 < r["p_value"] < 0.04 and r["significant"]
    assert r["lift_pct"] == pytest.approx(30.0)
    lo, hi = r["ci95"]
    assert lo < r["diff"] < hi and lo > 0


def test_ztest_identical_groups_not_significant():
    r = stats.two_proportion_ztest(50, 500, 50, 500)
    assert r["z"] == 0 and r["p_value"] == pytest.approx(1.0) and not r["significant"]


@pytest.mark.parametrize("args", [(1, 0, 1, 1), (5, 4, 1, 10), (-1, 10, 1, 10)])
def test_ztest_rejects_bad_samples(args):
    with pytest.raises(ValueError):
        stats.two_proportion_ztest(*args)


def test_sample_size_matches_textbook():
    n = stats.sample_size_per_variant(0.10, 0.20)  # 10% -> 12%
    assert 3800 < n < 3900
    assert stats.sample_size_per_variant(0.10, 0.05) > n  # efeito menor exige mais amostra


def test_modified_z_flags_outlier_only():
    vals = [10, 11, 10, 9, 10, 11, 10, 9, 10, 40]
    z = stats.modified_z(vals)
    assert abs(z[-1]) > 3.5 and all(abs(x) < 3.5 for x in z[:-1])


def test_modified_z_handles_zero_mad_and_constants():
    assert stats.modified_z([5, 5, 5, 5]) == [0, 0, 0, 0]
    z = stats.modified_z([1, 1, 1, 1, 1, 1, 1, 10])
    assert abs(z[-1]) > 3.5
    assert stats.modified_z([1, 2]) == [0.0, 0.0]


def test_percentile_interpolation():
    assert stats.percentile([1, 2, 3, 4], 50) == 2.5
    assert stats.percentile([10], 75) == 10
    assert stats.percentile([1, 2, 3, 4, 5], 100) == 5
    with pytest.raises(ValueError):
        stats.percentile([], 50)


@pytest.mark.parametrize("m,v,s", [("lcp", 2500, "good"), ("lcp", 2501, "needs-improvement"), ("lcp", 4001, "poor"),
                                   ("inp", 200, "good"), ("inp", 501, "poor"), ("cls", 0.1, "good"), ("cls", 0.3, "poor")])
def test_cwv_status(m, v, s):
    assert stats.cwv_status(m, v) == s

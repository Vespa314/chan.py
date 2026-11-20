from Research.config import FEATURE_COLUMNS, OPTIONAL_FEATURES
from Research.features import apply_schema, is_strict_type1, vectorize


def test_schema_fills_missing_with_mask():
    row = apply_schema({"is_buy": 1, "type_1": 1, "bsp_bi_amp": 0.2, "bi_is_sure": 1})
    assert list(row) == FEATURE_COLUMNS
    assert row["type_1"] == 1.0
    assert row["type_1p"] == 0.0
    assert row["bsp_bi_amp"] == 0.2
    assert row["divergence_rate"] == 0.0
    assert row["divergence_rate_missing"] == 1.0
    assert "bsp_persisted" not in row
    assert "net_return_10" not in row


def test_optional_columns_have_missing_flags():
    for name in OPTIONAL_FEATURES:
        assert f"{name}_missing" in FEATURE_COLUMNS


def test_vectorize_follows_meta_order():
    assert vectorize({"a": 1.0, "b": 2.0}, ["b", "a", "c"]) == [2.0, 1.0, 0.0]


def test_strict_type1_matches_demo1_thresholds():
    assert is_strict_type1({"1"}, 0.5, 1)
    assert is_strict_type1({"1p"}, 0.8, 2)
    assert not is_strict_type1({"1"}, 0.81, 1)
    assert not is_strict_type1({"1"}, 0.5, 0)
    assert not is_strict_type1({"2"}, 0.2, 3)
    assert not is_strict_type1({"1"}, float("inf"), 2)


def test_relaxed_chan_config_is_valid():
    from Research.config import make_chan_config

    config = make_chan_config()
    assert config.trigger_step is True
    assert config.cal_rsi is True

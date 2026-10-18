from Research.labels import PendingBuy, net_return


def _buy(horizons=(3,)):
    return PendingBuy(entry=10.0, upper_zs=0.08, horizons=horizons)


def test_upper_barrier_sets_positive_label():
    pending = _buy()
    pending.add_bar("2020-01-02", high=10.2, low=9.8, close=10.1)
    pending.add_bar("2020-01-03", high=10.9, low=9.8, close=10.4)
    out = pending.outcome()
    assert out["label_3"] == 1
    assert out["exit_reason_3"] == "upper"
    assert out["complete_3"] == 1
    assert abs(out["exit_price_3"] - 10.8) < 1e-9
    assert abs(out["net_return_3"] - net_return(10.0, 10.8)) < 1e-12


def test_same_bar_both_barriers_count_as_loss():
    pending = _buy()
    pending.add_bar("2020-01-02", high=11.0, low=9.5, close=10.0)
    out = pending.outcome()
    assert out["label_3"] == 0
    assert out["barrier_reason_3"] == "lower"
    assert out["exit_reason_3"] == "lower"
    assert abs(out["exit_price_3"] - 9.6) < 1e-9


def test_time_barrier_exits_at_close():
    pending = _buy()
    for day in ("2020-01-02", "2020-01-03", "2020-01-06"):
        pending.add_bar(day, high=10.2, low=9.8, close=10.5)
    out = pending.outcome()
    assert out["label_3"] == 0
    assert out["exit_reason_3"] == "time"
    assert abs(out["exit_price_3"] - 10.5) < 1e-9
    assert out["horizon_end_3"] == "2020-01-06"
    assert abs(out["forward_return_3"] - 0.05) < 1e-12


def test_sell_exits_trade_while_label_follows_barrier():
    pending = _buy()
    pending.add_bar("2020-01-02", high=10.2, low=9.8, close=10.2, sell_price=10.2)
    pending.add_bar("2020-01-03", high=10.9, low=9.8, close=10.4)
    out = pending.outcome()
    assert out["exit_reason_3"] == "sell"
    assert abs(out["exit_price_3"] - 10.2) < 1e-9
    assert out["label_3"] == 1
    assert out["barrier_reason_3"] == "upper"
    assert out["complete_3"] == 1

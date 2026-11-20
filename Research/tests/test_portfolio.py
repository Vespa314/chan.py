from Research.portfolio import simulate
from Research.train import choose_threshold


def _event(code, day, ret, score=None):
    record = {
        "code": code,
        "decision_time": day,
        "exit_time_10": "2020-01-08",
        "decision_price": 10.0,
        "net_return_10": ret,
        "path_10": "2020-01-03:10.2|2020-01-08:10.5",
    }
    if score is not None:
        record["score"] = score
    return record


def test_portfolio_books_net_return_and_caps_positions():
    one = simulate([_event("000001.XSHE", "2020-01-02", 0.098)])
    assert one["n_trades"] == 1
    assert abs(one["final_equity"] - (1.0 + 0.1 * 0.098)) < 1e-9

    many = [_event(f"{i:06d}.XSHE", "2020-01-02", 0.01) for i in range(11)]
    capped = simulate(many)
    assert capped["n_trades"] == 10


def test_portfolio_does_not_stack_the_same_code():
    records = [
        _event("000001.XSHE", "2020-01-02", 0.01),
        _event("000001.XSHE", "2020-01-03", 0.02),
    ]
    assert simulate(records)["n_trades"] == 1


def test_threshold_maximizes_validation_return():
    records = [
        {"score": 0.9, "net_return_10": 0.05},
        {"score": 0.9, "net_return_10": 0.05},
        {"score": 0.4, "net_return_10": -0.2},
        {"score": 0.4, "net_return_10": -0.2},
    ]
    picked = choose_threshold(records, min_count=2)
    assert picked is not None
    assert picked["threshold"] == 0.8
    assert picked["n"] == 2

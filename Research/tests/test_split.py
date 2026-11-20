from Research.config import FOLDS
from Research.split import select_test, select_train, select_val


def _row(decision, horizon_end, complete=1):
    return {
        "decision_time": decision,
        "complete_10": complete,
        "horizon_end_20": horizon_end,
    }


def test_train_drops_labels_that_cross_validation():
    fold = FOLDS[0]
    assert select_train(_row("2021-11-01", "2021-12-20"), fold)
    assert not select_train(_row("2021-12-20", "2022-01-10"), fold)
    assert not select_train(_row("2021-11-01", ""), fold)
    assert not select_train(_row("2022-01-04", "2022-02-01"), fold)


def test_validation_drops_labels_that_cross_test():
    fold = FOLDS[0]
    assert select_val(_row("2022-06-01", "2022-07-01"), fold)
    assert not select_val(_row("2022-12-20", "2023-01-10"), fold)


def test_test_uses_its_own_window():
    fold = FOLDS[0]
    assert select_test(_row("2023-03-01", "2023-04-01"), fold)
    assert not select_test(_row("2022-12-01", "2023-01-05"), fold)
    assert not select_test(_row("2023-03-01", "2023-04-01", complete=0), fold)

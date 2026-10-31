import numpy as np

from src import params
from src.db import init_db, make_engine
from src.forecast import task_model
from src.forecast.industry import categorise, task_pressure


def _rows(n: int) -> list[dict]:
    """Synthetic Economic Index and O*NET rows: tasks about entering data are mostly automated."""
    rows = []
    for i in range(n):
        auto = i % 2 == 0
        text = f"{'Enter and post' if auto else 'Advise and negotiate with'} records batch {i}."
        rows.append(
            {
                "series": task_model.TARGET,
                "geography": "GLOBAL",
                "period": "2026-05",
                "entity": f"{i} {text}",
                "value": 80.0 if auto else 20.0,
            }
        )
    for i, text in enumerate(["Enter and post invoices.", "Advise and negotiate with suppliers."]):
        rows.append(
            {
                "series": task_model.STATEMENTS,
                "entity": f"{900 + i} 43-3031.00",
                "value": 4.0,
                "cited_span": f"O*NET 31.0 · 43-3031.00 X · task {900 + i} (Core): {text}",
            }
        )
    return rows


def _fake_embedder(texts: list[str]) -> tuple[np.ndarray, str]:
    return np.array(
        [[float("Enter" in t), float("Advise" in t), len(t) / 100] for t in texts]
    ), "fake"


def test_choose_keeps_a_model_only_if_it_beats_the_mean_baseline() -> None:
    assert task_model.choose({"mean": 10.0, "ridge": 7.0, "lightgbm": 8.0}) == "ridge"
    assert task_model.choose({"mean": 10.0, "ridge": 9.9}) is None  # within TASK_MODEL_MIN_GAIN


def test_run_trains_predicts_and_skips_unchanged_data(tmp_path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'f.sqlite'}")
    init_db(engine)
    rows = _rows(params.TASK_MODEL_MIN_TRAIN + 20)
    first = task_model.run(engine, rows, _fake_embedder, None)
    assert first["status"] == "ok" and "fake" in first["note"]
    version, tasks = task_model.latest(engine)
    assert version is not None and version["best"] != "none"
    predicted = {t["text"]: t["predicted"] for t in tasks}
    assert predicted["Enter and post invoices."] > predicted["Advise and negotiate with suppliers."]
    again = task_model.run(engine, rows, _fake_embedder, None)
    assert "unchanged" in again["note"]
    engine.dispose()


def test_too_little_training_data_is_skipped(tmp_path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'f.sqlite'}")
    init_db(engine)
    assert task_model.run(engine, _rows(10), _fake_embedder, None)["status"] == "skipped"
    engine.dispose()


def test_task_pressure_prefers_observed_values_and_weights_by_importance() -> None:
    rows = [
        {"soc": "A", "task": "1", "observed": 60.0, "predicted": 10.0, "importance": 5.0},
        {"soc": "A", "task": "2", "observed": None, "predicted": 20.0, "importance": 1.0},
    ]
    press = task_pressure(rows)["A"]
    assert press["share"] == round((5 * 60 + 1 * 20) / 6, 1)
    assert press["tasks_observed"] == 1 and press["tasks_predicted"] == 1


def test_categories_need_two_kinds_of_ai_evidence_and_a_falling_forecast_to_shrink() -> None:
    high_use = params.INDUSTRY_USE_HIGH + 1
    exposed = params.INDUSTRY_EXPOSURE_HIGH + 0.1
    falling = -params.INDUSTRY_DEMAND_EPS_PP - 0.1
    rising = params.INDUSTRY_DEMAND_EPS_PP + 0.1
    assert categorise(high_use, None, None, falling, None)[0] == "stable"  # usage alone: no verdict
    assert categorise(high_use, exposed, None, 0.0, None)[0] == "transforming"
    assert categorise(high_use, exposed, None, falling, None)[0] == "shrinking"
    assert categorise(None, None, 2.0, rising, None)[0] == "growing"
    assert categorise(None, None, 1.0, None, True)[0] == "growing"  # MyCOL hard to fill
    assert categorise(None, None, 0.0, None, None)[0] == "emerging"

"""Task-level AI-use model: predicts the automation-style share of AI use for O*NET tasks.

Why: the Economic Index observes AI use only for tasks people already bring to Claude. Most tasks of
the followed occupations have no observation, yet their direction matters. The model learns, from
every task the Index observes, how a task's wording relates to the share of its conversations that
are automation-style (AI doing the task rather than helping a person do it), and predicts that share
for the tasks of our occupations. An observed value is always shown before a predicted one.

    target y   = aei_task_collaboration_bucket_automation_pct (global, latest month), 0-100
    features x = the task statement as a BGE-M3 embedding (RunPod); when RunPod is unavailable,
                 TF-IDF word features reduced by SVD, and the version says so (engine "tfidf")
    candidates = mean (baseline), ridge regression, random forest, histogram gradient boosting,
                 LightGBM and XGBoost (the last two only when installed: requirements-ml.txt)
    choice     = 5-fold cross-validated mean absolute error (MAE); the lowest wins only if it beats
                 the baseline by TASK_MODEL_MIN_GAIN, otherwise nothing is predicted

Every prediction is an estimate, stored with the model version, its CV error and the baseline's.
Pure functions except `run`, which reads stored observations and writes the version tables.
"""

import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
from sqlalchemy import Engine, insert, select

from src import params
from src.forecast.store import embedding_table, prediction_table, version_table

log = logging.getLogger(__name__)
Row = dict[str, Any]
Embedder = Callable[[list[str]], tuple[np.ndarray, str]]
TARGET = "aei_task_collaboration_bucket_automation_pct"
STATEMENTS = "onet_task_statement"


@dataclass(frozen=True)
class Task:
    task: str  # O*NET task id
    text: str
    soc: str = ""
    importance: float | None = None


def evidence_period(rows: list[Row]) -> str | None:
    """The newest Economic Index month among these (accepted) observations, if any."""
    periods = [r["period"] for r in rows if r["series"] == TARGET]
    return max(periods) if periods else None


def training_set(rows: list[Row]) -> tuple[list[Task], np.ndarray, str]:
    """Every task with an observed automation share in the latest month, and that month."""
    target = [r for r in rows if r["series"] == TARGET and r["geography"] == "GLOBAL"]
    if not target:
        return [], np.zeros(0), ""
    period = max(r["period"] for r in target)
    tasks, ys = [], []
    for r in sorted(target, key=lambda r: r["entity"]):
        if r["period"] != period or r["value"] is None:
            continue
        task, _, text = r["entity"].partition(" ")
        tasks.append(Task(task, text))
        ys.append(float(r["value"]))
    return tasks, np.array(ys), period


def prediction_set(rows: list[Row]) -> list[Task]:
    """Every task statement of the followed occupations (O*NET), with its importance."""
    out = []
    for r in rows:
        if r["series"] != STATEMENTS:
            continue
        task, _, soc = r["entity"].partition(" ")
        text = str(r["cited_span"]).split("): ", 1)[-1]
        out.append(Task(task, text, soc, r["value"]))
    return sorted(out, key=lambda t: (t.soc, int(t.task)))


def tfidf_features(texts: list[str]) -> np.ndarray:
    """Fallback features: TF-IDF word and bigram weights reduced to TFIDF_COMPONENTS by SVD."""
    from sklearn.decomposition import TruncatedSVD  # type: ignore[import-untyped]
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-untyped]

    matrix = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit_transform(texts)
    components = min(params.TFIDF_COMPONENTS, matrix.shape[1] - 1)
    svd = TruncatedSVD(components, random_state=params.TASK_MODEL_SEED)
    return np.asarray(svd.fit_transform(matrix))


def candidates(n_features: int) -> dict[str, Callable[[], Any]]:
    """The models compared, each a fresh scikit-learn estimator; tree models see SVD-reduced input
    (TREE_COMPONENTS) because 1024 embedding dimensions over a few thousand tasks overfit them."""
    from sklearn.decomposition import PCA
    from sklearn.dummy import DummyRegressor  # type: ignore[import-untyped]
    from sklearn.ensemble import (  # type: ignore[import-untyped]
        HistGradientBoostingRegressor,
        RandomForestRegressor,
    )
    from sklearn.linear_model import RidgeCV  # type: ignore[import-untyped]
    from sklearn.pipeline import make_pipeline  # type: ignore[import-untyped]

    seed = params.TASK_MODEL_SEED

    def reduced(model: Any) -> Any:
        return make_pipeline(PCA(min(params.TREE_COMPONENTS, n_features), random_state=seed), model)

    out: dict[str, Callable[[], Any]] = {
        "mean": lambda: DummyRegressor(strategy="mean"),
        "ridge": lambda: RidgeCV(alphas=params.RIDGE_ALPHAS),
        "random_forest": lambda: reduced(
            RandomForestRegressor(
                n_estimators=300, min_samples_leaf=5, random_state=seed, n_jobs=-1
            )
        ),
        "hist_gradient_boosting": lambda: reduced(
            HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=seed)
        ),
    }
    try:
        from lightgbm import LGBMRegressor

        out["lightgbm"] = lambda: reduced(
            LGBMRegressor(
                n_estimators=400, learning_rate=0.03, num_leaves=15, random_state=seed, verbose=-1
            )
        )
    except ImportError:
        pass
    try:
        from xgboost import XGBRegressor

        out["xgboost"] = lambda: reduced(
            XGBRegressor(
                n_estimators=400, learning_rate=0.03, max_depth=4, subsample=0.8, random_state=seed
            )
        )
    except ImportError:
        pass
    return out


def cross_validate(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Mean absolute error of each candidate over the same TASK_MODEL_FOLDS folds."""
    from sklearn.model_selection import KFold  # type: ignore[import-untyped]

    folds = KFold(params.TASK_MODEL_FOLDS, shuffle=True, random_state=params.TASK_MODEL_SEED)
    scores: dict[str, float] = {}
    for name, make in candidates(x.shape[1]).items():
        errors = []
        for train, test in folds.split(x):
            model = make().fit(x[train], y[train])
            errors.append(float(np.mean(np.abs(np.clip(model.predict(x[test]), 0, 100) - y[test]))))
        scores[name] = round(float(np.mean(errors)), 3)
    return scores


def choose(scores: dict[str, float]) -> str | None:
    """The best model if it beats the mean baseline by TASK_MODEL_MIN_GAIN (relative), else None."""
    best = min((n for n in scores if n != "mean"), key=lambda n: scores[n], default=None)
    if best is None or scores[best] > scores["mean"] * (1 - params.TASK_MODEL_MIN_GAIN):
        return None
    return best


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def cached_embedder(engine: Engine, remote: Callable[[list[str]], list[list[float]]]) -> Embedder:
    """BGE-M3 vectors, each text embedded once and kept in `task_embedding`."""

    def embed(texts: list[str]) -> tuple[np.ndarray, str]:
        keys = [_hash(t) for t in texts]
        with engine.connect() as conn:
            stored = {
                r.text_hash: json.loads(r.vector)
                for r in conn.execute(select(embedding_table))
                if r.model == params.TASK_EMBEDDING_MODEL
            }
        missing = sorted({t for t, k in zip(texts, keys, strict=True) if k not in stored})
        if missing:
            vectors = remote(missing)
            with engine.begin() as conn:
                for text, vector in zip(missing, vectors, strict=True):
                    conn.execute(
                        insert(embedding_table).values(
                            text_hash=_hash(text),
                            model=params.TASK_EMBEDDING_MODEL,
                            vector=json.dumps(vector),
                        )
                    )
                    stored[_hash(text)] = vector
        return np.array([stored[k] for k in keys]), "bge-m3"

    return embed


def run(
    engine: Engine, rows: list[Row], embedder: Embedder | None, run_id: int | None
) -> dict[str, Any]:
    """Train, choose and predict when the training data or the tasks changed; store a version."""
    train, y, period = training_set(rows)
    predict = prediction_set(rows)
    if len(train) < params.TASK_MODEL_MIN_TRAIN or not predict:
        return {
            "status": "skipped",
            "note": f"{len(train)} training tasks, {len(predict)} to predict",
        }
    digest = _hash(
        json.dumps([[t.task, v] for t, v in zip(train, y.tolist(), strict=True)])
        + json.dumps([[t.soc, t.task] for t in predict])
        + params.TASK_MODEL_VERSION
        + period
    )
    with engine.connect() as conn:
        last = conn.execute(select(version_table).order_by(version_table.c.id.desc())).first()
    # Unchanged data skips the re-fit, unless the last fit fell back to TF-IDF and RunPod is back.
    upgrade = last is not None and last.features == "tfidf" and embedder is not None
    if last is not None and last.data_hash == digest and not upgrade:
        return {"status": "ok", "note": f"task model unchanged (version {last.id})"}
    texts = [t.text for t in train] + [t.text for t in predict]
    engine_name = "tfidf"
    features: np.ndarray | None = None
    if embedder is not None:
        try:
            features, engine_name = embedder(texts)
        except Exception as exc:  # noqa: BLE001  RunPod down: fall back and say so
            log.warning("task model: embeddings unavailable (%s); TF-IDF features used", exc)
    if features is None:
        features = tfidf_features(texts)
    x_train, x_pred = features[: len(train)], features[len(train) :]
    scores = cross_validate(x_train, y)
    best = choose(scores)
    observed = {t.task: v for t, v in zip(train, y.tolist(), strict=True)}
    predictions: list[float | None] = [None] * len(predict)
    if best is not None:
        model = candidates(x_train.shape[1])[best]().fit(x_train, y)
        predictions = [round(float(v), 2) for v in np.clip(model.predict(x_pred), 0, 100)]
    with engine.begin() as conn:
        key = conn.execute(
            insert(version_table).values(
                created_at=datetime.now(UTC),
                run_id=run_id,
                period=period,
                features=engine_name,
                n_train=len(train),
                n_predict=len(predict),
                scores=json.dumps(scores),
                best=best or "none",
                data_hash=digest,
            )
        ).inserted_primary_key
        assert key is not None
        version_id = key[0]
        for task, predicted in zip(predict, predictions, strict=True):
            conn.execute(
                insert(prediction_table).values(
                    version_id=version_id,
                    soc=task.soc,
                    task=task.task,
                    text=task.text,
                    importance=task.importance,
                    observed=observed.get(task.task),
                    predicted=predicted,
                )
            )
    chosen = f"{best} MAE {scores[best]}" if best else "no model beat the baseline"
    return {
        "status": "ok",
        "note": (
            f"task model v{version_id}: {len(train)} training tasks ({period}, {engine_name}); "
            f"{chosen} vs mean {scores['mean']}; {len(predict)} tasks predicted"
        ),
    }


def latest(engine: Engine, period: str | None = None) -> tuple[Row | None, list[Row]]:
    """The newest model version and its per-task rows (observed and predicted shares).

    With `period` (the newest Economic Index month in a person's accepted evidence), only a
    version trained on that month or an earlier one: a model fitted on a newer month reaches the
    person when they accept that month's evidence, like any other new evidence."""
    query = select(version_table).order_by(version_table.c.id.desc())
    if period is not None:
        query = query.where(version_table.c.period <= period)
    with engine.connect() as conn:
        version = conn.execute(query).first()
        if version is None:
            return None, []
        tasks = conn.execute(
            select(prediction_table).where(prediction_table.c.version_id == version.id)
        ).mappings()
        return dict(version._mapping), [dict(t) for t in tasks]

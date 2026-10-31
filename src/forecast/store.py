"""Tables of the forecast layer: task-model versions, their per-task rows, and cached embeddings.

A version is stored only when its training data or the predicted tasks changed, so the history
shows when and why the model was re-fitted, with every candidate's cross-validated error.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, Text

from src.db import metadata

version_table = Table(
    "task_model_version",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("run_id", Integer, nullable=True),
    Column("period", String(16), nullable=False),  # Economic Index month trained on
    Column("features", String(16), nullable=False),  # "bge-m3" or "tfidf"
    Column("n_train", Integer, nullable=False),
    Column("n_predict", Integer, nullable=False),
    Column("scores", Text, nullable=False),  # JSON: candidate -> cross-validated MAE
    Column("best", String(32), nullable=False),  # chosen model, or "none"
    Column("data_hash", String(64), nullable=False),
)

prediction_table = Table(
    "task_prediction",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("version_id", Integer, ForeignKey("task_model_version.id"), nullable=False),
    Column("soc", String(16), nullable=False),
    Column("task", String(16), nullable=False),
    Column("text", Text, nullable=False),
    Column("importance", Float, nullable=True),  # O*NET IM 1-5; None = not rated
    Column("observed", Float, nullable=True),  # Economic Index share when observed
    Column("predicted", Float, nullable=True),  # model estimate; None = no model adopted
)

embedding_table = Table(
    "task_embedding",
    metadata,
    Column("text_hash", String(64), primary_key=True),
    Column("model", String(64), nullable=False),
    Column("vector", Text, nullable=False),  # JSON list of floats
)

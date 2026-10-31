from src.db import init_db, make_engine
from src.intake import cache


def test_the_same_cv_text_gets_the_stored_reading(tmp_path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'c.sqlite'}")
    init_db(engine)
    k = cache.key("Processed supplier invoices.", "gpt-4.1-mini", "prompt-v1")
    assert cache.get(engine, k) is None
    cache.put(engine, k, "gpt-4.1-mini", {"skills": [{"skill": "invoice_processing", "level": 4}]})
    cache.put(engine, k, "gpt-4.1-mini", {"skills": []})  # the first reading stays
    assert cache.get(engine, k) == {"skills": [{"skill": "invoice_processing", "level": 4}]}
    # A new model or new instructions read the CV again.
    assert cache.key("Processed supplier invoices.", "other-model", "prompt-v1") != k
    assert cache.key("Processed supplier invoices.", "gpt-4.1-mini", "prompt-v2") != k
    engine.dispose()

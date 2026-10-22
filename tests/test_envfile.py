"""The .env loader sets missing variables only and never needs a library."""

from pathlib import Path

from src.envfile import load_env_file


def test_loads_missing_values_and_keeps_existing_ones(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        '# comment\nLLM_API_KEY="sk-test"\nexport RUNPOD_ENDPOINT_ID=abc\n'
        "EMPTY=\nRUNPOD_API_KEY=new\n",
        encoding="utf-8",
    )
    environ = {"RUNPOD_API_KEY": "from-replit-secrets"}
    loaded = load_env_file(env_file, environ)
    assert sorted(loaded) == ["LLM_API_KEY", "RUNPOD_ENDPOINT_ID"]
    assert environ == {
        "RUNPOD_API_KEY": "from-replit-secrets",
        "LLM_API_KEY": "sk-test",
        "RUNPOD_ENDPOINT_ID": "abc",
    }


def test_missing_file_loads_nothing(tmp_path: Path) -> None:
    assert load_env_file(tmp_path / ".env", {}) == []

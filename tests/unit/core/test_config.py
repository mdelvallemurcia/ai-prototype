"""Unit tests for src/core/config.py — Settings dataclass and load_settings()."""

from unittest.mock import patch

from src.core.config import Settings, load_settings

# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------


def test_settings_direct_construction_stores_fields():
    # Arrange
    expected_api_key = "test-api-key"
    expected_model = "meta/llama-test"
    expected_embed_model = "nvidia/embed-test"
    expected_db_url = "postgresql+psycopg://user:pass@localhost/db"

    # Act
    settings = Settings(
        nvidia_api_key=expected_api_key,
        nvidia_model=expected_model,
        nvidia_embed_model=expected_embed_model,
        db_url=expected_db_url,
    )

    # Assert
    assert settings.nvidia_api_key == expected_api_key
    assert settings.nvidia_model == expected_model
    assert settings.nvidia_embed_model == expected_embed_model
    assert settings.db_url == expected_db_url


# ---------------------------------------------------------------------------
# load_settings()
# ---------------------------------------------------------------------------


def test_load_settings_reads_env_vars():
    # Arrange
    env_vars = {
        "MEALMATE_NVIDIA_API_KEY": "my-api-key",
        "MEALMATE_NVIDIA_MODEL": "meta/llama-custom",
        "MEALMATE_NVIDIA_EMBED_MODEL": "nvidia/embed-custom",
        "MEALMATE_DB_URL": "postgresql+psycopg://user:pass@host/db",
    }

    # Act
    with patch("src.core.config.load_dotenv"), patch.dict("os.environ", env_vars, clear=True):
        result = load_settings()

    # Assert
    assert result.nvidia_api_key == "my-api-key"
    assert result.nvidia_model == "meta/llama-custom"
    assert result.nvidia_embed_model == "nvidia/embed-custom"
    assert result.db_url == "postgresql+psycopg://user:pass@host/db"


def test_load_settings_uses_defaults_when_env_missing():
    # Arrange — empty environment (no MEALMATE_* vars)

    # Act
    with patch("src.core.config.load_dotenv"), patch.dict("os.environ", {}, clear=True):
        result = load_settings()

    # Assert
    assert result.nvidia_api_key == ""
    assert result.nvidia_model == "meta/llama-3.1-8b-instruct"
    assert result.nvidia_embed_model == "nvidia/nv-embedqa-e5-v5"
    assert result.db_url == "postgresql+psycopg://mealmate:mealmate_dev@localhost:5432/mealmate"

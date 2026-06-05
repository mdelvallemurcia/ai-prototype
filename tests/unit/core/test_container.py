"""Unit tests for src/core/container.py — Container lazy properties and create_container()."""

from unittest.mock import MagicMock, patch

from src.core.config import Settings
from src.core.container import Container, create_container

# ---------------------------------------------------------------------------
# Shared test fixture
# ---------------------------------------------------------------------------


def make_settings() -> Settings:
    return Settings(
        nvidia_api_key="test-api-key",
        nvidia_model="meta/llama-test",
        nvidia_embed_model="nvidia/embed-test",
        db_url="postgresql+psycopg://user:pass@localhost/testdb",
    )


# ---------------------------------------------------------------------------
# Container.settings property
# ---------------------------------------------------------------------------


def test_container_settings_property_returns_settings():
    # Arrange
    settings = make_settings()

    # Act
    container = Container(settings)

    # Assert
    assert container.settings is settings


# ---------------------------------------------------------------------------
# Container.engine — lazy construction and caching
# ---------------------------------------------------------------------------


def test_container_engine_constructed_with_db_url():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with patch("src.core.container.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engine_first = container.engine
        engine_second = container.engine

    # Assert
    mock_create_engine.assert_called_once_with(settings.db_url)
    assert engine_first is mock_engine
    assert engine_second is mock_engine


# ---------------------------------------------------------------------------
# Container.session_factory — lazy construction and caching
# ---------------------------------------------------------------------------


def test_container_session_factory_constructed_with_engine():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with (
        patch("src.core.container.create_engine") as mock_create_engine,
        patch("src.core.container.sessionmaker") as mock_sessionmaker,
    ):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_factory = MagicMock()
        mock_sessionmaker.return_value = mock_factory

        sf_first = container.session_factory
        sf_second = container.session_factory

    # Assert
    mock_sessionmaker.assert_called_once_with(bind=mock_engine)
    assert sf_first is mock_factory
    assert sf_second is mock_factory


# ---------------------------------------------------------------------------
# Container.get_session — delegates to session_factory()
# ---------------------------------------------------------------------------


def test_container_get_session_returns_session_factory_result():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with (
        patch("src.core.container.create_engine"),
        patch("src.core.container.sessionmaker") as mock_sessionmaker,
    ):
        mock_factory = MagicMock()
        mock_session = MagicMock()
        mock_factory.return_value = mock_session
        mock_sessionmaker.return_value = mock_factory

        result = container.get_session()

    # Assert
    mock_factory.assert_called_once()
    assert result is mock_session


# ---------------------------------------------------------------------------
# Container.embeddings — deferred import, lazy construction and caching
# ---------------------------------------------------------------------------


def test_container_embeddings_constructed_with_correct_args():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with patch("langchain_nvidia_ai_endpoints.NVIDIAEmbeddings") as mock_embeddings_cls:
        mock_embeddings = MagicMock()
        mock_embeddings_cls.return_value = mock_embeddings

        emb_first = container.embeddings
        emb_second = container.embeddings

    # Assert
    mock_embeddings_cls.assert_called_once_with(
        model=settings.nvidia_embed_model,
        api_key=settings.nvidia_api_key,
    )
    assert emb_first is mock_embeddings
    assert emb_second is mock_embeddings


# ---------------------------------------------------------------------------
# Container.vector_store — deferred import, lazy construction and caching
# ---------------------------------------------------------------------------


def test_container_vector_store_constructed_with_correct_args():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with (
        patch("langchain_nvidia_ai_endpoints.NVIDIAEmbeddings") as mock_embeddings_cls,
        patch("langchain_postgres.PGVector") as mock_pgvector_cls,
    ):
        mock_embeddings = MagicMock()
        mock_embeddings_cls.return_value = mock_embeddings
        mock_vector_store = MagicMock()
        mock_pgvector_cls.return_value = mock_vector_store

        vs_first = container.vector_store
        vs_second = container.vector_store

    # Assert
    mock_pgvector_cls.assert_called_once_with(
        connection=settings.db_url,
        embeddings=mock_embeddings,
        collection_name="recipes",
    )
    assert vs_first is mock_vector_store
    assert vs_second is mock_vector_store


# ---------------------------------------------------------------------------
# Container.retriever — delegates to vector_store.as_retriever
# ---------------------------------------------------------------------------


def test_container_retriever_calls_as_retriever():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with (
        patch("langchain_nvidia_ai_endpoints.NVIDIAEmbeddings"),
        patch("langchain_postgres.PGVector") as mock_pgvector_cls,
    ):
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_pgvector_cls.return_value = mock_vector_store

        ret_first = container.retriever
        ret_second = container.retriever

    # Assert
    mock_vector_store.as_retriever.assert_called_once_with(search_kwargs={"k": 5})
    assert ret_first is mock_retriever
    assert ret_second is mock_retriever


# ---------------------------------------------------------------------------
# create_container() factory
# ---------------------------------------------------------------------------


def test_create_container_uses_provided_settings():
    # Arrange
    settings = make_settings()

    # Act
    with patch("src.core.container.load_settings") as mock_load_settings:
        container = create_container(settings=settings)

    # Assert
    mock_load_settings.assert_not_called()
    assert container.settings is settings


def test_create_container_calls_load_settings_when_none():
    # Arrange
    fake_settings = make_settings()

    # Act
    with patch("src.core.container.load_settings", return_value=fake_settings) as mock_load:
        container = create_container()

    # Assert
    mock_load.assert_called_once()
    assert container.settings is fake_settings


# ---------------------------------------------------------------------------
# Container.chat_model — deferred import, lazy construction and caching (WLI-01..03)
# ---------------------------------------------------------------------------


def test_container_chat_model_constructed_with_correct_args():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with patch("langchain_nvidia_ai_endpoints.ChatNVIDIA") as mock_chat_cls:
        mock_chat = MagicMock()
        mock_chat_cls.return_value = mock_chat

        result = container.chat_model

    # Assert
    mock_chat_cls.assert_called_once_with(
        model=settings.nvidia_model,
        api_key=settings.nvidia_api_key,
    )
    assert result is mock_chat


def test_container_chat_model_cached_on_repeated_access():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with patch("langchain_nvidia_ai_endpoints.ChatNVIDIA") as mock_chat_cls:
        mock_chat = MagicMock()
        mock_chat_cls.return_value = mock_chat

        first = container.chat_model
        second = container.chat_model

    # Assert
    mock_chat_cls.assert_called_once()
    assert first is second


def test_container_chat_model_propagates_empty_model_string():
    # Arrange
    settings = Settings(
        nvidia_api_key="k",
        nvidia_model="",
        nvidia_embed_model="nvidia/embed-test",
        db_url="postgresql+psycopg://user:pass@localhost/testdb",
    )
    container = Container(settings)

    # Act
    with patch("langchain_nvidia_ai_endpoints.ChatNVIDIA") as mock_chat_cls:
        mock_chat_cls.return_value = MagicMock()
        container.chat_model

    # Assert
    mock_chat_cls.assert_called_once_with(model="", api_key="k")


def test_container_chat_model_does_not_access_engine():
    # Arrange
    settings = make_settings()
    container = Container(settings)

    # Act
    with patch("langchain_nvidia_ai_endpoints.ChatNVIDIA") as mock_chat_cls:
        mock_chat_cls.return_value = MagicMock()
        container.chat_model

    # Assert — no DB-related fields were touched
    assert container._engine is None
    assert container._session_factory is None

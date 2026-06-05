from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import Settings, load_settings

if TYPE_CHECKING:
    from langchain_core.vectorstores import VectorStoreRetriever
    from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
    from langchain_postgres import PGVector


class Container:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None
        self._embeddings: NVIDIAEmbeddings | None = None
        self._vector_store: PGVector | None = None
        self._retriever: VectorStoreRetriever | None = None
        self._chat_model: ChatNVIDIA | None = None

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(self._settings.db_url)
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    def get_session(self) -> Session:
        return self.session_factory()

    @property
    def chat_model(self) -> ChatNVIDIA:
        if self._chat_model is None:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            self._chat_model = ChatNVIDIA(
                model=self._settings.nvidia_model,
                api_key=self._settings.nvidia_api_key,
            )
        return self._chat_model

    @property
    def embeddings(self) -> NVIDIAEmbeddings:
        if self._embeddings is None:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

            self._embeddings = NVIDIAEmbeddings(
                model=self._settings.nvidia_embed_model,
                api_key=self._settings.nvidia_api_key,
            )
        return self._embeddings

    @property
    def vector_store(self) -> PGVector:
        if self._vector_store is None:
            from langchain_postgres import PGVector

            self._vector_store = PGVector(
                connection=self._settings.db_url,
                embeddings=self.embeddings,
                collection_name="recipes",
            )
        return self._vector_store

    @property
    def retriever(self) -> VectorStoreRetriever:
        if self._retriever is None:
            self._retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
        return self._retriever


def create_container(settings: Settings | None = None) -> Container:
    if settings is None:
        settings = load_settings()
    return Container(settings)

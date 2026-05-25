from langchain_postgres import PGVector

from src.core.config import settings
from src.core.embeddings import embeddings

vector_store = PGVector(
    connection=settings.db_url,
    embeddings=embeddings,
    collection_name="recipes",
)

retriever = vector_store.as_retriever(search_kwargs={"k": 5})

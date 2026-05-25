from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from src.core.config import settings

embeddings = NVIDIAEmbeddings(
    model=settings.nvidia_embed_model,
    api_key=settings.nvidia_api_key,
)

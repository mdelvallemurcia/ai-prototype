from dataclasses import dataclass
from os import environ

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str
    nvidia_model: str
    nvidia_embed_model: str
    db_url: str


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        nvidia_api_key=environ.get("MEALMATE_NVIDIA_API_KEY", ""),
        nvidia_model=environ.get("MEALMATE_NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"),
        nvidia_embed_model=environ.get("MEALMATE_NVIDIA_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5"),
        db_url=environ.get(
            "MEALMATE_DB_URL",
            "postgresql+psycopg://mealmate:mealmate_dev@localhost:5432/mealmate",
        ),
    )

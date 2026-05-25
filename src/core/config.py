from dataclasses import dataclass
from os import environ

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str = environ.get("MEALMATE_NVIDIA_API_KEY", "")
    nvidia_model: str = environ.get("MEALMATE_NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
    nvidia_embed_model: str = environ.get("MEALMATE_NVIDIA_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")
    db_url: str = environ.get(
        "MEALMATE_DB_URL", "postgresql+psycopg://mealmate:mealmate_dev@localhost:5432/mealmate"
    )


settings = Settings()

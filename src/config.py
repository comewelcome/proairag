from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # PostgreSQL (required — no default)
    database_url: str = ""

    # Neo4j (required — no default)
    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""

    # Embedding
    embedding_model: str = "sentence-transformers/paraphrase-MiniLM-L3-v2"
    embedding_dimension: int = 384

    # API
    secret_key: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5

    # LLM (OpenAI-compatible API on llama.cpp localhost:1234)
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_api_base: str = "http://localhost:1234/v1"
    openai_model: str = "Qwen3.6-27B-UD-Q5_K_XL.gguf"

    # Ollama fallback
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # LLM generation
    llm_max_tokens: int = 500

    # Super admin (global — auto-seed at startup)
    super_admin_email: str = ""
    super_admin_password: str = ""

    # Dashboard auto-seed tenants (DASHBOARD_LOGIN_1, DASHBOARD_PASSWORD_1, etc.)
    dashboard_login_1: str = ""
    dashboard_password_1: str = ""
    dashboard_login_2: str = ""
    dashboard_password_2: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    def __init__(self, **data):
        super().__init__(**data)
        required = ["database_url", "neo4j_uri", "neo4j_user", "neo4j_password", "secret_key"]
        missing = [k for k in required if not getattr(self, k)]
        if missing:
            raise ValueError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Set them in your .env file or environment."
            )

    def get_dashboard_seeds(self) -> list[dict]:
        """Return list of {email, password} for auto-seeded dashboard tenants."""
        seeds = []
        i = 1
        while True:
            email = getattr(self, f"dashboard_login_{i}", "") or ""
            password = getattr(self, f"dashboard_password_{i}", "") or ""
            if not email or not password:
                break
            seeds.append({"email": email, "password": password})
            i += 1
        return seeds


@lru_cache()
def get_settings() -> Settings:
    return Settings()

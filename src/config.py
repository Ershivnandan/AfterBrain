from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout: float = 120.0

    # After Effects bridge mode: 'auto', 'live', or 'mock'
    ae_execution_mode: str = "auto"
    ae_binary_path: str = ""

    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent
    output_scripts_dir: Path = Path(__file__).resolve().parent.parent / "output_scripts"
    character_registry_path: Path = Path(__file__).resolve().parent.parent / "data" / "character_registry.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure directories exist
settings.output_scripts_dir.mkdir(parents=True, exist_ok=True)
settings.character_registry_path.parent.mkdir(parents=True, exist_ok=True)

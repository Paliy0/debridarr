"""Configuration and settings."""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings, loaded from env vars or config file."""

    # Real-Debrid
    rd_token: str = ""
    rd_token_file: Optional[str] = None  # Path to file containing token

    # Downloads
    download_dir: str = "/downloads"
    max_concurrent_downloads: int = 3

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    model_config = {"env_prefix": "RD_"}

    def get_token(self) -> str:
        """Get API token, checking file if configured."""
        if self.rd_token_file:
            path = Path(self.rd_token_file)
            if path.exists():
                return path.read_text().strip()
        return self.rd_token

    def validate(self):
        """Validate that we have a token."""
        token = self.get_token()
        if not token:
            raise ValueError(
                "No Real-Debrid API token configured. "
                "Set RD_TOKEN environment variable or RD_TOKEN_FILE path."
            )


# Global settings instance
settings = Settings()

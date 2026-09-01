"""Application configuration loaded from environment variables.

Every tunable value of the MVP lives here so that no secret or environment
specific path is hard-coded anywhere else in the code base.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated view over the process environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Anthropic / Claude ------------------------------------------------
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-opus-5", alias="CLAUDE_MODEL")
    claude_extraction_effort: str = Field(default="medium", alias="CLAUDE_EXTRACTION_EFFORT")
    claude_classification_effort: str = Field(default="high", alias="CLAUDE_CLASSIFICATION_EFFORT")

    # --- MongoDB -----------------------------------------------------------
    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db: str = Field(default="tariff_assistant", alias="MONGO_DB")

    # --- Authentication ----------------------------------------------------
    jwt_secret: str = Field(default="insecure-development-secret", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(default=8, alias="JWT_EXPIRE_HOURS")
    seed_user_email: str = Field(default="demo@aduana.mx", alias="SEED_USER_EMAIL")
    seed_user_password: str = Field(default="demo1234", alias="SEED_USER_PASSWORD")

    # --- File storage ------------------------------------------------------
    upload_dir: Path = Field(default=Path("/data/uploads"), alias="UPLOAD_DIR")
    pedimento_dir: Path = Field(default=Path("/data/pedimentos"), alias="PEDIMENTO_DIR")
    catalog_json_path: Path = Field(
        default=Path("/data/catalog/tariff_items.json"), alias="CATALOG_JSON_PATH"
    )
    sat_excel_path: Path = Field(
        default=Path("/data/c_FraccionArancelaria.xlsx"), alias="SAT_EXCEL_PATH"
    )
    snice_excel_path: Path = Field(
        default=Path("/data/snice_aranceles.xlsx"), alias="SNICE_EXCEL_PATH"
    )
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")

    # --- Business rules ----------------------------------------------------
    confidence_threshold: float = Field(default=0.6, alias="CONFIDENCE_THRESHOLD")
    default_exchange_rate: float = Field(default=17.50, alias="DEFAULT_EXCHANGE_RATE")

    # Mock counterparties preloaded into the operation form (RF-07), so the
    # demo can be completed in one click without inventing data on camera.
    default_origin_country: str = Field(default="CN", alias="DEFAULT_ORIGIN_COUNTRY")
    default_importer_rfc: str = Field(default="XAXX010101000", alias="DEFAULT_IMPORTER_RFC")
    default_importer_name: str = Field(
        default="Importadora Demo SA de CV", alias="DEFAULT_IMPORTER_NAME"
    )
    default_supplier_name: str = Field(
        default="Shenzhen Electronics Co Ltd", alias="DEFAULT_SUPPLIER_NAME"
    )
    default_supplier_country: str = Field(
        default="CN", alias="DEFAULT_SUPPLIER_COUNTRY"
    )

    # --- API ---------------------------------------------------------------
    # Kept as plain text: pydantic-settings would otherwise try to JSON-decode
    # a list-typed field, which makes the .env file awkward to write by hand.
    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> list[str]:
        """Allowed browser origins, parsed from the comma separated setting."""
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached because FastAPI resolves this dependency on every request and reading
    the environment repeatedly buys nothing.
    """
    return Settings()

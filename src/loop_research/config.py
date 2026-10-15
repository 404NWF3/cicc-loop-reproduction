from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True, hide_input_in_errors=True
    )

    state_dir: Path = Field(Path("artifacts/runtime"), validation_alias="LOOP_STATE_DIR")
    data_dir: Path = Field(Path("data"), validation_alias="LOOP_DATA_DIR")
    web_dist: Path = Field(Path("web/dist"), validation_alias="LOOP_WEB_DIST")
    worker_autostart: bool = Field(True, validation_alias="LOOP_WORKER_AUTOSTART")
    fixture_step_seconds: float = Field(
        0.3, ge=0.01, le=5, validation_alias="LOOP_FIXTURE_STEP_SECONDS"
    )
    auth_required: bool = Field(False, validation_alias="LOOP_AUTH_REQUIRED")
    auth_username: str = Field("", validation_alias="LOOP_AUTH_USERNAME")
    auth_password: SecretStr = Field(
        default=SecretStr(""), validation_alias="LOOP_AUTH_PASSWORD", repr=False
    )
    deepseek_api_key: str = Field("", repr=False)
    deepseek_model: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    @model_validator(mode="after")
    def validate_auth(self):
        password = self.auth_password.get_secret_value()
        if self.auth_required or self.auth_username or password:
            if not self.auth_username or not password:
                raise ValueError("请同时设置 LOOP_AUTH_USERNAME 和 LOOP_AUTH_PASSWORD。")
            if ":" in self.auth_username or any(
                c.isspace() or not c.isprintable() for c in self.auth_username
            ):
                raise ValueError("LOOP_AUTH_USERNAME 不能包含空白、控制字符或冒号。")
            if len(password) < 16:
                raise ValueError("LOOP_AUTH_PASSWORD 至少需要 16 个字符。")
        return self

    @property
    def auth_enabled(self) -> bool:
        return bool(self.auth_username and self.auth_password.get_secret_value())

    @field_validator("deepseek_base_url")
    @classmethod
    def official_endpoint_only(cls, value: str) -> str:
        value = value.rstrip("/")
        if value not in {"https://api.deepseek.com", "https://api.deepseek.com/v1"}:
            raise ValueError("Use the official HTTPS DeepSeek endpoint")
        return value

    @property
    def database_path(self) -> Path:
        return self.state_dir.resolve() / "loop.sqlite3"

    def model_status(self) -> dict:
        configured = bool(self.deepseek_api_key and self.deepseek_model)
        return {
            "provider": "DeepSeek",
            "requested_name": "DeepSeek 4.1 Flash",
            "model_id": self.deepseek_model or None,
            "key_present": bool(self.deepseek_api_key),
            "configured": configured,
            "verified": False,
            "status": "configured_unverified" if configured else "not_configured",
        }

"""Load local assistant settings without exporting secrets to child processes."""

import os
from decimal import Decimal
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel, Field, SecretStr

MODEL = "claude-haiku-5-5"
ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / "data" / "ai-usage.sqlite3"


class AISettings(BaseModel):
    enabled: bool = False
    api_key: SecretStr | None = Field(default=None, repr=False)
    model: Literal["claude-haiku-5-5"] = MODEL
    budget: Decimal = Field(default=Decimal("2.00"), gt=0, le=2, decimal_places=9)
    tool_rounds: int = Field(default=5, ge=0, le=5)
    output_tokens: int = Field(default=1500, ge=1, le=1500)
    requests_per_minute: int = Field(default=5, ge=1, le=5)
    question_length: int = Field(default=2000, ge=1, le=2000)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.get_secret_value().strip())

    @classmethod
    def load(cls) -> "AISettings":
        names = dict(
            enabled="AI_ENABLED", api_key="ANTHROPIC_API_KEY", model="ANTHROPIC_MODEL",
            budget="AI_BUDGET_USD", tool_rounds="AI_MAX_TOOL_ROUNDS",
            output_tokens="AI_MAX_OUTPUT_TOKENS", requests_per_minute="AI_MAX_REQUESTS_PER_MINUTE",
            question_length="AI_MAX_QUESTION_LENGTH",
        )
        # An explicit environment override is useful for disabled-mode verification.
        enabled = os.environ.get("AI_ENABLED")
        if enabled is not None and enabled.strip().lower() in {"false", "0", "off", "no"}:
            return cls()
        local = dotenv_values(ROOT / ".env", interpolate=False)
        values = {
            field: os.environ.get(name, local.get(name))
            for field, name in names.items() if name in os.environ or name in local
        }
        return cls.model_validate(values)

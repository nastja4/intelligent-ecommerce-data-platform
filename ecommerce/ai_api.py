"""Local-only routes for the optional assistant."""

import asyncio
import ipaddress
import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ecommerce import ai_agent
from ecommerce.ai_config import LEDGER_PATH, MODEL, AISettings
from ecommerce.ai_usage import BudgetExceeded, Ledger, RateExceeded, usd

router = APIRouter(prefix="/api/v1/chat", tags=["Local AI assistant"])

HOSTS = {"127.0.0.1", "localhost", "[::1]"}
ALLOWED_HOSTS = HOSTS | {f"{host}:{port}" for host in HOSTS for port in (8000, 5173)}
ORIGINS = {f"http://{host}" for host in ALLOWED_HOSTS}


def require_local(request: Request, response: Response) -> None:
    try:
        local_peer = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        local_peer = False
    origin = request.headers.get("origin")
    if (not local_peer or request.headers.get("host", "").lower() not in ALLOWED_HOSTS
        or (origin is not None and origin not in ORIGINS)
        or request.headers.get("sec-fetch-site") == "cross-site"):
        raise HTTPException(403, "Chat is available only from the local dashboard.")
    if request.method == "POST" and request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "Use application/json for chat requests.")
    response.headers["Cache-Control"] = "no-store"


class ChatStatus(BaseModel):
    enabled: bool
    model: str = MODEL
    availability: Literal["disabled", "unconfigured", "ready", "unavailable", "budget_exhausted"]
    estimated_usage_usd: str | None = None
    remaining_budget_usd: str | None = None


@router.get("/status", dependencies=[Depends(require_local)])
def status() -> ChatStatus:
    settings = None
    try:
        settings = AISettings.load()
        if not settings.enabled:
            return ChatStatus(enabled=False, availability="disabled")
        if not settings.configured:
            return ChatStatus(enabled=True, availability="unconfigured")
        ledger = Ledger(LEDGER_PATH, settings.budget)
        spent, remaining = ledger.balances()
        maximum = ai_agent.Usage(
            input_tokens=ai_agent.RESERVED_INPUT_TOKENS, output_tokens=settings.output_tokens,
        ).cost_units()
        return ChatStatus(enabled=True, availability="ready" if remaining >= maximum else "budget_exhausted",
                          estimated_usage_usd=usd(spent), remaining_budget_usd=usd(remaining))
    except Exception:
        return ChatStatus(enabled=settings.enabled if settings else False, availability="unavailable")


@router.post("", dependencies=[Depends(require_local)])
async def chat(payload: ai_agent.ChatRequest) -> ai_agent.ChatResponse:
    try:
        settings = AISettings.load()
        if not settings.enabled or not settings.configured:
            raise HTTPException(503, "The assistant is disabled or missing local configuration.")
        ledger = Ledger(LEDGER_PATH, settings.budget)
        await asyncio.to_thread(ledger.admit, settings.requests_per_minute)
        return await ai_agent.run_chat(payload, settings, ledger)
    except HTTPException:
        raise
    except BudgetExceeded:
        raise HTTPException(429, "The remaining application budget cannot cover another model call.") from None
    except RateExceeded:
        raise HTTPException(429, "The local chat request limit was reached. Try again in a minute.") from None
    except ai_agent.InputTooLarge:
        raise HTTPException(422, "The question or conversation context exceeds the configured limits.") from None
    except TimeoutError:
        raise HTTPException(504, "The assistant timed out. A model call with unknown usage remains reserved.") from None
    except (ai_agent.ProviderUnavailable, ai_agent.InvalidProviderResponse):
        raise HTTPException(502, "The model provider did not return a usable answer.") from None
    except (sqlite3.Error, OSError):
        raise HTTPException(503, "The local assistant is unavailable.") from None
    except Exception:
        raise HTTPException(503, "The assistant configuration or analytical tools are unavailable.") from None

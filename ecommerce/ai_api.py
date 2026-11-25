"""Local-only routes for the optional assistant."""

import asyncio
import ipaddress
import os
import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ecommerce import ai_agent
from ecommerce.ai_config import MODEL, AISettings, usage_path_from_env
from ecommerce.ai_usage import BudgetExceeded, Ledger, RateExceeded, usd

router = APIRouter(prefix="/api/v1/chat", tags=["Local AI assistant"])

HOSTS = {"127.0.0.1", "localhost", "[::1]"}
ALLOWED_HOSTS = HOSTS | {f"{host}:{port}" for host in HOSTS for port in (8000, 5173)}
ORIGINS = {f"http://{host}" for host in ALLOWED_HOSTS}
DOCKER_HOST = "127.0.0.1:8000"
DOCKER_ORIGIN = f"http://{DOCKER_HOST}"


def require_local(request: Request, response: Response) -> None:
    try:
        peer = ipaddress.ip_address(request.client.host) if request.client else None
    except ValueError:
        peer = None
    host = request.headers.get("host", "").lower()
    origin = request.headers.get("origin")
    fetch_site = request.headers.get("sec-fetch-site")
    native = (
        peer is not None and peer.is_loopback and host in ALLOWED_HOSTS
        and (origin is None or origin in ORIGINS) and fetch_site != "cross-site"
    )
    # The dedicated Compose bridge has one explicitly trusted gateway. Forwarded
    # headers are disabled at Uvicorn, and sibling container addresses are rejected.
    docker = (
        isinstance(peer, ipaddress.IPv4Address) and peer.is_private and not peer.is_loopback
        and str(peer) == os.environ.get("AI_DOCKER_TRUSTED_PEER")
        and host == DOCKER_HOST and (origin is None or origin == DOCKER_ORIGIN)
        and fetch_site in {None, "same-origin"}
        and (request.method != "POST" or (origin == DOCKER_ORIGIN and fetch_site == "same-origin"))
    )
    if not (native or docker):
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
        ledger = Ledger(usage_path_from_env(), settings.budget)
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
        ledger = Ledger(usage_path_from_env(), settings.budget)
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

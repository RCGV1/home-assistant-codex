"""Worker discovery helpers for the Codex integration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession

from .api import CodexCliApiClient, CodexCliApiError, CodexCliAuthError
from .const import WORKER_ADDON_NAME, WORKER_ADDON_SLUG


@dataclass(slots=True, frozen=True)
class WorkerConnection:
    """Discovered worker connection details."""

    base_url: str
    api_token: str
    addon_slug: str | None = None


def _add_candidate(candidates: list[str], base_url: str) -> None:
    base_url = base_url.rstrip("/")
    if base_url and base_url not in candidates:
        candidates.append(base_url)


def _addon_matches(addon: dict[str, Any]) -> bool:
    """Return true if a Supervisor add-on/app entry is the Codex worker."""
    slug = str(addon.get("slug") or "")
    name = str(addon.get("name") or "")
    if addon.get("installed") is False:
        return False
    return (
        slug == WORKER_ADDON_SLUG
        or slug.endswith(f"_{WORKER_ADDON_SLUG}")
        or name.casefold() == WORKER_ADDON_NAME.casefold()
    )


def _supervisor_token() -> str:
    """Return the Supervisor token made available to Home Assistant Core."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise CodexCliApiError("Supervisor token is not available")
    return token


async def _async_supervisor_get(session: ClientSession, path: str) -> dict[str, Any]:
    """Fetch one Supervisor API endpoint."""
    token = _supervisor_token()
    try:
        async with session.get(
            f"http://supervisor{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        ) as response:
            if response.status != 200:
                raise CodexCliApiError(f"Supervisor returned HTTP {response.status}")
            payload = await response.json(content_type=None)
    except (ClientError, TimeoutError, ValueError):
        raise CodexCliApiError("Could not query Supervisor for the Codex worker") from None

    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        raise CodexCliApiError("Supervisor returned invalid app metadata")
    return data


async def _async_supervisor_addons(session: ClientSession) -> list[dict[str, Any]]:
    """Return installed Supervisor app metadata."""
    data = await _async_supervisor_get(session, "/addons")
    addons = data.get("addons", []) if isinstance(data, dict) else []
    return [addon for addon in addons if isinstance(addon, dict)]


async def _async_supervisor_addon_info(session: ClientSession, slug: str) -> dict[str, Any]:
    """Return one Supervisor app info payload."""
    return await _async_supervisor_get(session, f"/addons/{slug}/info")


def _candidate_urls_from_addon(addon: dict[str, Any]) -> list[str]:
    """Return URL candidates for one Supervisor app entry."""
    candidates: list[str] = []
    hostname = str(addon.get("hostname") or "")
    slug = str(addon.get("slug") or "")

    if hostname:
        _add_candidate(candidates, f"http://{hostname}:9123")
    if slug:
        _add_candidate(candidates, f"http://{slug.replace('_', '-')}:9123")

    return candidates


async def _async_worker_addons(session: ClientSession) -> list[dict[str, Any]]:
    """Return installed Codex worker app info payloads."""
    workers: list[dict[str, Any]] = []
    for addon in await _async_supervisor_addons(session):
        if not _addon_matches(addon):
            continue
        slug = str(addon.get("slug") or "")
        if not slug:
            continue
        info = await _async_supervisor_addon_info(session, slug)
        workers.append({**addon, **info})
    return workers


async def async_discover_worker(session: ClientSession) -> WorkerConnection:
    """Find the reachable worker app and its generated API token."""
    workers = await _async_worker_addons(session)
    if not workers:
        raise CodexCliApiError("Codex CLI Worker app is not installed")

    last_error: CodexCliApiError | None = None
    for addon in workers:
        options = addon.get("options") if isinstance(addon.get("options"), dict) else {}
        api_token = str(options.get("api_token") or "")
        if not api_token:
            raise CodexCliApiError("Codex CLI Worker API token has not been generated yet")

        for base_url in _candidate_urls_from_addon(addon):
            client = CodexCliApiClient(session, base_url, api_token)
            try:
                await client.status()
            except CodexCliAuthError as exc:
                last_error = exc
                continue
            except CodexCliApiError as exc:
                last_error = exc
                continue
            return WorkerConnection(
                base_url=base_url,
                api_token=api_token,
                addon_slug=str(addon.get("slug") or "") or None,
            )

    if last_error is not None:
        raise CodexCliApiError(f"Could not connect to the Codex worker: {last_error}") from last_error
    raise CodexCliApiError("Could not discover the Codex worker app")

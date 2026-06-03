"""Conversation support for Codex CLI."""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CodexCliApiError
from .const import CONF_BASE_URL, DOMAIN

PARALLEL_UPDATES = 0
INLINE_WAIT_SECONDS = 90
INLINE_POLL_SECONDS = 2


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Codex CLI conversation entity."""
    async_add_entities([CodexConversationEntity(entry)])


class CodexConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """Conversation agent that starts safe Codex config tasks."""

    _attr_has_entity_name = True
    _attr_name = "Assistant"
    _attr_translation_key = "assistant"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the Codex conversation entity."""
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_conversation"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Codex",
            "manufacturer": "OpenAI",
            "model": "Codex CLI Worker",
            "configuration_url": entry.data.get(CONF_BASE_URL),
        }

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Register this entity as a conversation agent."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister this entity as a conversation agent."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process a message by starting a Codex task when appropriate."""
        text = user_input.text.strip()

        if not text:
            return self._result(
                user_input,
                "Tell me what you want Codex to inspect, explain, fix, or do for the house.",
            )

        runtime_data = getattr(self.entry, "runtime_data", None)
        if runtime_data is None:
            return self._result(
                user_input,
                "Codex is installed but not loaded yet. Check the Codex integration and worker app before starting a task.",
            )

        coordinator = runtime_data.coordinator
        data: dict[str, Any] = coordinator.data or {}
        if data.get("active_task_id") or int(data.get("active_task_count") or 0) > 0:
            active_task_id = data.get("active_task_id") or "the active task"
            return self._result(
                user_input,
                f"Codex is already working on {active_task_id}. Wait for that task to finish before starting another one.",
            )

        login = data.get("codex_login") or {}
        if not login.get("status_ok"):
            return self._result(
                user_input,
                "Codex is not signed in yet. Start the Codex sign-in flow, authenticate it, then ask me again.",
            )

        prompt = _build_codex_prompt(text)
        try:
            result = await runtime_data.client.start_task(prompt)
        except CodexCliApiError as exc:
            return self._result(
                user_input,
                f"I could not start the Codex task: {exc}",
            )

        await coordinator.async_request_refresh()
        task_id = result.get("task_id", "unknown")
        inline_speech = await _async_wait_for_task(
            runtime_data.client,
            str(task_id),
            timeout=INLINE_WAIT_SECONDS,
        )
        await coordinator.async_request_refresh()

        if inline_speech:
            return self._result(user_input, inline_speech)

        return self._result(
            user_input,
            f"I started a Codex background task for that. Task id: {task_id}. I will notify you when it finishes or needs input.",
        )

    def _result(
        self,
        user_input: conversation.ConversationInput,
        speech: str,
        *,
        continue_conversation: bool = False,
    ) -> conversation.ConversationResult:
        """Create a Home Assistant conversation result."""
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(speech)
        return conversation.ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
            continue_conversation=continue_conversation,
        )


def _build_codex_prompt(user_prompt: str) -> str:
    """Wrap the user prompt with safety and operating instructions."""
    return (
        "You are Codex working inside Benjamin's Home Assistant configuration. "
        "Follow safety best practices. Prefer reversible, auditable changes. "
        "Handle every user request as the Home Assistant Codex assistant. "
        "For simple live-status questions, prefer fast direct Home Assistant API state checks using HA_TOKEN instead of scanning the whole config tree. "
        "For general house questions, inspect current Home Assistant state, relevant dashboards, automations, repairs, integrations, sensors, and recent task context as needed, then report clearly. "
        "For configuration changes, inspect the current state first, preserve unrelated user changes, create or rely on existing backups where available, validate configuration when possible, and report what changed. "
        "For immediate physical actions involving locks, alarms, garage doors, cameras, speakers, thermostats, security state, or anything disruptive, do not act silently. Confirm the exact action and safety impact unless the user's request is explicit, low-risk, and necessary. "
        "If a request is ambiguous or high-impact, ask for input instead of guessing. "
        "Focus on being practically useful for this house: dashboards, automations, sensors, Nest doorbell/event media, security visibility, cleaning/vacuum workflows, backups, repairs, and integration health.\n\n"
        f"User request: {user_prompt}"
    )


async def _async_wait_for_task(client: Any, task_id: str, *, timeout: int) -> str | None:
    """Wait briefly for a task and return speech if it finishes."""
    if not task_id or task_id == "unknown":
        return None

    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(INLINE_POLL_SECONDS)
        try:
            task_result = await client.get_task(task_id)
        except CodexCliApiError:
            return None

        task = task_result.get("task") or {}
        status = task.get("status")
        if status in ("queued", "running"):
            continue

        summary = str(task.get("summary") or "").strip()
        question = str(task.get("question") or "").strip()
        details = str(task.get("details") or "").strip()

        if status == "waiting_for_input":
            return question or summary or "Codex needs more information before it can continue."

        if status == "completed":
            return _format_inline_task_response(summary, details)

        if status == "failed":
            return _format_inline_task_response(
                summary or "Codex could not complete that request.",
                details,
            )

        return _format_inline_task_response(summary, details)

    return None


def _format_inline_task_response(summary: str, details: str) -> str:
    """Format a completed task for an Assist response."""
    if not details:
        return summary or "Codex finished."

    if summary and details.startswith(summary):
        return details

    if len(details) <= 900:
        if summary:
            return f"{summary}\n\n{details}"
        return details

    return summary or details[:900]

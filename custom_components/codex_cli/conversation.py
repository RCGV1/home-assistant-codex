"""Conversation support for Codex CLI."""

from __future__ import annotations

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

CONFIG_TASK_KEYWORDS = (
    "automation",
    "automations",
    "dashboard",
    "dashboards",
    "lovelace",
    "script",
    "scripts",
    "scene",
    "scenes",
    "helper",
    "helpers",
    "integration",
    "integrations",
    "config",
    "configuration",
    "yaml",
    "hacs",
    "repair",
    "repairs",
    "trace",
    "traces",
    "debug",
    "fix",
    "improve",
    "organize",
    "review",
    "clean up",
    "setup",
    "set up",
    "install",
    "remove",
    "update",
    "status",
    "health",
    "house",
    "home",
    "what's up",
    "whats up",
    "what is up",
    "anything wrong",
    "problems",
    "issues",
    "overview",
    "check my",
    "look at my",
)

DIRECT_CONTROL_HINTS = (
    "turn on",
    "turn off",
    "switch on",
    "switch off",
    "open ",
    "close ",
    "unlock",
    "lock ",
    "arm ",
    "disarm",
    "set temperature",
    "set the temperature",
    "play ",
    "pause ",
    "stop ",
)


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
        lower_text = text.lower()

        if not text:
            return self._result(
                user_input,
                "Tell me what Home Assistant configuration, dashboard, or automation work you want Codex to do.",
            )

        if _is_help_request(lower_text):
            return self._result(user_input, _help_response())

        if _looks_like_direct_control(lower_text) and not _looks_like_config_task(
            lower_text
        ):
            return self._result(
                user_input,
                "Use the normal Home Assistant assistant for immediate device control. "
                "I handle Codex background work like dashboards, automations, scripts, integrations, and troubleshooting.",
            )

        if not _looks_like_config_task(lower_text):
            return self._result(
                user_input,
                "I can help by starting a Codex background task for Home Assistant configuration, dashboards, automations, integrations, and debugging. "
                "Please describe the change or investigation you want.",
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


def _is_help_request(text: str) -> bool:
    """Return whether the user is asking what Codex can do."""
    return text in {
        "help",
        "what can you do",
        "what can codex do",
        "how can you help",
        "how can codex help",
    } or ("what" in text and "codex" in text and "do" in text)


def _looks_like_config_task(text: str) -> bool:
    """Return whether the request looks like a config/debugging task."""
    return any(keyword in text for keyword in CONFIG_TASK_KEYWORDS)


def _looks_like_direct_control(text: str) -> bool:
    """Return whether the request looks like immediate device control."""
    return any(hint in text for hint in DIRECT_CONTROL_HINTS)


def _help_response() -> str:
    """Return the short voice help response."""
    return (
        "I am the Codex configuration assistant for this Home Assistant instance. "
        "I can start background tasks to review, fix, and improve dashboards, automations, scripts, integrations, repairs, and configuration. "
        "For immediate actions like lights, locks, media, climate, or arming security, use the normal Home Assistant assistant."
    )


def _build_codex_prompt(user_prompt: str) -> str:
    """Wrap the user prompt with safety and operating instructions."""
    return (
        "You are Codex working inside Benjamin's Home Assistant configuration. "
        "Follow safety best practices. Prefer reversible, auditable changes. "
        "Do not directly operate physical devices, locks, alarms, garage doors, cameras, speakers, thermostats, or security state unless the user explicitly requested that exact action and it is necessary. "
        "For configuration changes, inspect the current state first, preserve unrelated user changes, create or rely on existing backups where available, validate configuration when possible, and report what changed. "
        "If a request is ambiguous or high-impact, ask for input instead of guessing. "
        "Focus on being practically useful for this house: dashboards, automations, sensors, Nest doorbell/event media, security visibility, cleaning/vacuum workflows, backups, repairs, and integration health.\n\n"
        f"User request: {user_prompt}"
    )

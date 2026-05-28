"""Sensors for the Codex CLI integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BASE_URL, DOMAIN
from .coordinator import CodexCliCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Codex CLI sensors."""
    coordinator: CodexCliCoordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            CodexLastTaskSensor(coordinator, entry),
            CodexTaskCountSensor(coordinator, entry),
            CodexAuthSensor(coordinator, entry),
            CodexFiveHourLimitSensor(coordinator, entry),
            CodexWeeklyLimitSensor(coordinator, entry),
        ]
    )


class _CodexSensor(CoordinatorEntity[CodexCliCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: CodexCliCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Codex",
            "manufacturer": "OpenAI",
            "model": "Codex CLI Worker",
            "configuration_url": entry.data.get(CONF_BASE_URL),
        }


class CodexLastTaskSensor(_CodexSensor):
    """Show the latest Codex task status."""

    _attr_icon = "mdi:clipboard-text-clock-outline"
    _attr_translation_key = "last_task"

    def __init__(self, coordinator: CodexCliCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "last_task")

    @property
    def native_value(self) -> str:
        latest = (self.coordinator.data or {}).get("latest_task") or {}
        return latest.get("status") or "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        latest = (self.coordinator.data or {}).get("latest_task") or {}
        return {
            "task_id": latest.get("task_id"),
            "title": latest.get("title"),
            "summary": latest.get("summary"),
            "question": latest.get("question"),
            "updated_at": latest.get("updated_at"),
            "active_task_id": (self.coordinator.data or {}).get("active_task_id"),
            "error": (self.coordinator.data or {}).get("error"),
        }


class CodexTaskCountSensor(_CodexSensor):
    """Show how many Codex tasks are active."""

    _attr_icon = "mdi:progress-clock"
    _attr_translation_key = "active_tasks"

    def __init__(self, coordinator: CodexCliCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "task_count")

    @property
    def native_value(self) -> int:
        data = self.coordinator.data or {}
        return int(data.get("active_task_count") or data.get("task_count") or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "active_task_id": data.get("active_task_id"),
            "total_task_count": data.get("total_task_count"),
        }


class CodexAuthSensor(_CodexSensor):
    """Show Codex login status."""

    _attr_icon = "mdi:account-key-outline"
    _attr_translation_key = "auth_status"

    def __init__(self, coordinator: CodexCliCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "auth_status")

    @property
    def native_value(self) -> str:
        login = (self.coordinator.data or {}).get("codex_login") or {}
        if login.get("status_ok"):
            return "logged_in"
        if login.get("has_auth_file"):
            return "auth_file_present"
        return "not_logged_in"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        login = (self.coordinator.data or {}).get("codex_login") or {}
        auth_flow = (self.coordinator.data or {}).get("auth_flow") or {}
        return {
            "message": login.get("message"),
            "has_auth_file": login.get("has_auth_file"),
            "auth_flow_status": auth_flow.get("status"),
            "verification_url": auth_flow.get("verification_url"),
            "user_code": auth_flow.get("user_code"),
            "qr_url": auth_flow.get("qr_url"),
        }


class CodexFiveHourLimitSensor(_CodexSensor):
    """Show Codex 5-hour usage line from interactive status."""

    _attr_icon = "mdi:timer-sand"
    _attr_translation_key = "five_hour_limit"

    def __init__(self, coordinator: CodexCliCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "five_hour_limit")

    @property
    def native_value(self) -> str:
        usage = (self.coordinator.data or {}).get("codex_usage") or {}
        return str(usage.get("five_hour_limit") or "unavailable")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        usage = (self.coordinator.data or {}).get("codex_usage") or {}
        return {
            "usage_status": usage.get("status"),
            "updated_at": usage.get("updated_at"),
            "error": usage.get("error"),
            "weekly_limit": usage.get("weekly_limit"),
            "context_remaining": usage.get("context_remaining"),
        }


class CodexWeeklyLimitSensor(_CodexSensor):
    """Show Codex weekly usage line from interactive status."""

    _attr_icon = "mdi:calendar-week"
    _attr_translation_key = "weekly_limit"

    def __init__(self, coordinator: CodexCliCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "weekly_limit")

    @property
    def native_value(self) -> str:
        usage = (self.coordinator.data or {}).get("codex_usage") or {}
        return str(usage.get("weekly_limit") or "unavailable")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        usage = (self.coordinator.data or {}).get("codex_usage") or {}
        return {
            "usage_status": usage.get("status"),
            "updated_at": usage.get("updated_at"),
            "error": usage.get("error"),
            "five_hour_limit": usage.get("five_hour_limit"),
            "context_remaining": usage.get("context_remaining"),
        }

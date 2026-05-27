"""Config flow for the Codex integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CodexCliApiClient, CodexCliApiError, CodexCliAuthError
from .const import CONF_API_TOKEN, CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, DEFAULT_BASE_URL)): str,
            vol.Required(CONF_API_TOKEN, default=defaults.get(CONF_API_TOKEN, "")): str,
        }
    )


async def _validate_input(hass: HomeAssistant, user_input: dict[str, Any]) -> None:
    """Validate the worker URL and API token."""
    client = CodexCliApiClient(
        async_get_clientsession(hass),
        user_input[CONF_BASE_URL],
        user_input[CONF_API_TOKEN],
    )
    await client.status()


def _error_for_exception(exc: CodexCliApiError) -> str:
    """Map API exceptions to config-flow error keys."""
    if isinstance(exc, CodexCliAuthError):
        return "invalid_auth"
    return "cannot_connect"


class CodexCliConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Codex."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Set up the integration from the Home Assistant UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            try:
                await _validate_input(self.hass, user_input)
            except CodexCliApiError as exc:
                errors["base"] = _error_for_exception(exc)
            else:
                return self.async_create_entry(title="Codex", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return CodexCliOptionsFlow(config_entry)

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        """Handle reauthentication requests."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        """Confirm new worker credentials."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}
        defaults = {**entry.data, **entry.options}

        if user_input is not None:
            try:
                await _validate_input(self.hass, user_input)
            except CodexCliApiError as exc:
                errors["base"] = _error_for_exception(exc)
            else:
                self.hass.config_entries.async_update_entry(entry, data=user_input, options={})
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_schema(user_input or defaults),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Handle UI reconfiguration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}
        defaults = {**entry.data, **entry.options}

        if user_input is not None:
            try:
                await _validate_input(self.hass, user_input)
            except CodexCliApiError as exc:
                errors["base"] = _error_for_exception(exc)
            else:
                self.hass.config_entries.async_update_entry(entry, data=user_input, options={})
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(user_input or defaults),
            errors=errors,
        )


class CodexCliOptionsFlow(config_entries.OptionsFlow):
    """Handle Codex options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        if user_input is not None:
            errors: dict[str, str] = {}
            try:
                await _validate_input(self.hass, user_input)
            except CodexCliApiError as exc:
                errors["base"] = _error_for_exception(exc)
                return self.async_show_form(
                    step_id="init",
                    data_schema=_schema(user_input),
                    errors=errors,
                )
            return self.async_create_entry(title="", data=user_input)

        defaults = {
            **self._config_entry.data,
            **self._config_entry.options,
        }
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(defaults),
        )

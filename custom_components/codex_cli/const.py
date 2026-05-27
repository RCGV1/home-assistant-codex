"""Constants for the Codex CLI integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "codex_cli"

CONF_BASE_URL: Final = "base_url"
CONF_API_TOKEN: Final = "api_token"

DEFAULT_BASE_URL: Final = "http://local-codex-cli-worker:9123"
LEGACY_DEFAULT_BASE_URL: Final = "http://192.168.1.229:9123"
DEFAULT_SCAN_INTERVAL_SECONDS: Final = 30

SERVICE_START_TASK: Final = "start_task"
SERVICE_GET_TASK: Final = "get_task"
SERVICE_LIST_TASKS: Final = "list_tasks"
SERVICE_CANCEL_TASK: Final = "cancel_task"
SERVICE_REPLY_TASK: Final = "reply_task"
SERVICE_START_LOGIN: Final = "start_login"
SERVICE_GET_LOGIN_STATUS: Final = "get_login_status"

ATTR_PROMPT: Final = "prompt"
ATTR_TITLE: Final = "title"
ATTR_TASK_ID: Final = "task_id"
ATTR_REPLY: Final = "reply"
ATTR_FORCE: Final = "force"

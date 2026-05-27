# Codex CLI Worker

This app runs Codex CLI tasks against the Home Assistant config folder mounted at `/config`.

This app is distributed from:

```text
https://github.com/moryoav/home-assistant-codex
```

Prebuilt images are published to `ghcr.io/moryoav/codex-cli-worker` for `amd64` and `aarch64`.

## Security Model

The web UI is intended to be opened only through Home Assistant Ingress. The app does not publish its HTTP port to the LAN by default, and the Flask server rejects spoofed Ingress requests unless they come from the Home Assistant Ingress proxy address.

Programmatic API calls still require the worker API token unless they are proxied through authenticated Home Assistant Ingress. The Home Assistant Codex integration should use the internal app hostname:

```text
http://local-codex-cli-worker:9123
```

The app does not request host networking, Docker API access, full access, host PID/UTS access, privileged kernel capabilities, or elevated Supervisor roles. It keeps AppArmor enabled and ships a custom `apparmor.txt` profile. The `/config` mount is intentionally read-write because editing Home Assistant configuration is the core purpose of the app.

## API Token

The API token protects the worker HTTP API. Leave `api_token` empty on first start and the app generates a random token, stores it back into the app options, and uses it immediately. Use the same token when adding the Home Assistant `Codex` integration.

The token is not your OpenAI or ChatGPT credential. Codex authentication is still handled separately with `codex login`.

## Model

`codex_model` is a fixed selection to avoid typo-prone free text. `gpt-5.3-codex` is the default because OpenAI lists it as the current most capable agentic coding model. Use `default` to let the installed Codex CLI choose its bundled default model.

## Sandbox

- `read-only`: Codex can inspect files and run read-only commands, but should not edit `/config`.
- `workspace-write`: Codex can edit the mounted `/config` workspace while generated shell commands remain sandboxed. This is the recommended mode.
- `danger-full-access`: Codex sandboxing is disabled inside the add-on container. The container still only mounts the configured add-on volumes, but this should be used only when a task cannot work in `workspace-write`.

## Codex Sign-In

Use the add-on web UI or the Home Assistant service `codex_cli.start_login` to start `codex login --device-auth`.

The add-on posts a Home Assistant persistent notification containing a QR code, link, and one-time device code. The QR code opens the OpenAI device page; type the code from the same notification into that page. The add-on refreshes the notification when the code appears and detects completion automatically. You do not need to run `docker exec`.

When opened through Home Assistant Ingress, the app web UI can start the login flow without entering the worker API token because Home Assistant already authenticated the session. Direct HTTP/API calls still require the worker API token.

The app uses the built-in Supervisor token for Home Assistant notifications and dashboard saves through the Home Assistant Core API proxy. No Home Assistant long-lived access token is required.

## Notifications

Leave `notify_service` unset or empty to use Home Assistant persistent notifications for task completion, failures, and questions. If you want push notifications, set it to a Home Assistant notify service such as `notify.mobile_app_your_phone`.

Home Assistant app configuration schemas do not currently provide a Home Assistant service autocomplete selector, so this option remains a plain text field.

## Human Input

Runs are non-interactive. If Codex needs a decision, it should return `needs_input`; Home Assistant marks the task as waiting and you can continue it with `codex_cli.reply_task`.

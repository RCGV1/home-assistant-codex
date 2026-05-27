# Codex

Codex connects Home Assistant to the local Codex CLI Worker add-on. It lets Home Assistant start Codex tasks against the configuration folder, monitor active work, reply to tasks that need input, and start the Codex sign-in flow.

## Installation

1. Add `https://github.com/moryoav/home-assistant-codex` as a Home Assistant app repository.
2. Install and start the Codex CLI Worker app.
3. Install this integration with HACS as a custom integration, or copy `custom_components/codex_cli` into `/config/custom_components/codex_cli`.
4. Restart Home Assistant.
5. Add the Codex integration from Settings > Devices & services.

## Configuration

- Worker URL: The local HTTP URL for the Codex CLI Worker app API. The recommended URL is `http://local-codex-cli-worker:9123`, which uses Home Assistant's internal app network instead of a LAN-exposed port.
- API token: The shared token that allows Home Assistant to call the worker API.

The integration can be reconfigured from the integration options or by using the reconfigure flow.

## Entities

- Auth status: Shows whether Codex CLI is signed in.
- Active tasks: Shows the number of currently running Codex tasks.
- Last task: Shows the latest known task status and related attributes.
- Task running: Binary sensor that is on while a task is active.

All entities are diagnostic entities on the Codex device.

## Actions

- `codex_cli.start_task`: Start a Codex task. Requires `prompt`; optional `title`.
- `codex_cli.start_login`: Start the Codex sign-in flow; optional `force`.
- `codex_cli.get_login_status`: Return current sign-in status.
- `codex_cli.list_tasks`: Return known tasks.
- `codex_cli.get_task`: Return one task by task ID.
- `codex_cli.cancel_task`: Cancel one task by task ID.
- `codex_cli.reply_task`: Send a reply to a waiting task.

Example automation action:

```yaml
action: codex_cli.start_task
data:
  title: Check dashboard
  prompt: Can you inspect my Home dashboard and report any obvious issues?
response_variable: codex_result
```

## Data Updates

The integration polls the worker every 30 seconds. Actions that start, cancel, or reply to tasks request an immediate refresh after the worker responds.

## Troubleshooting

- If entities are unavailable, check that the Codex CLI Worker add-on is running and that the worker URL is reachable.
- If Home Assistant asks for reauthentication, update the API token so it matches the add-on configuration.
- If Codex is not signed in, run `codex_cli.start_login` or use the add-on web UI to start the sign-in flow.
- If a task needs input, use `codex_cli.reply_task` with the task ID and reply text.

## Removal

1. Delete the Codex integration from Settings > Devices & services.
2. Disable or uninstall the Codex CLI Worker add-on if it is no longer needed.

## Known Limitations

- This integration controls a single local Codex CLI Worker instance.
- It does not auto-discover the add-on URL.
- It depends on the worker add-on for task execution, Codex authentication, and notification delivery.

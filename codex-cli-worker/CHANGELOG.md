# Changelog

## 0.1.14

- Advertise the worker app through Supervisor discovery for the Codex integration.
- Document automatic worker connection, Codex device-code prerequisites, and subscription requirements.

## 0.1.13

- Broadened the custom AppArmor profile so the Python/Node worker can start while keeping AppArmor enabled.

## 0.1.12

- Removed the default LAN port publication so the web UI is accessed through Home Assistant Ingress.
- Added exact Ingress proxy source validation in the worker server.
- Blocked direct non-Ingress access to the web UI.
- Required worker API authentication for `/health`.
- Added constant-time worker API token comparison.
- Added a custom AppArmor profile.
- Added README and expanded security documentation.

## 0.1.11

- Added generated worker API token support.
- Added Codex device-code sign-in notifications.
- Added task execution and status APIs for the Home Assistant Codex integration.

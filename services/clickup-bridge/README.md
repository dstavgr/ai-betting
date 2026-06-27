# ClickUp Bridge

Host-run FastAPI bridge for ClickUp task comments. It lets a ClickUp user mention an agent in a task comment and receive a reply in the same task.

This service is intentionally **not** Dockerized. It runs under systemd on the host so it can call host-installed CLI binaries such as Claude, Gemini, Codex, and agy.

## Behavior

- `GET /health` returns `ok`.
- `POST /clickup/webhook` verifies `X-Signature` as a hex HMAC-SHA256 over the raw request body using `CLICKUP_WEBHOOK_SECRET`.
- Only `taskCommentPosted` events are handled.
- Comments starting with `[agent-reply]` are ignored to prevent loops.
- Comments authored by `CLICKUP_BOT_USER_ID` are ignored when that env var is set.
- The first mention among `@claude2`, `@claude`, `@gemini`, `@codex`, `@agy`, and `@jules` chooses the agent.
- The mention is stripped and the remaining text is passed as the instruction.
- The webhook returns immediately; agent work runs in the FastAPI background task.
- Replies are posted back to ClickUp as:

```text
[agent-reply] @<agent>:
<agent output>
```

## Security Notes

- ClickUp comment text is untrusted data. The bridge never treats it as instructions for itself.
- CLI calls use subprocess argument lists with `shell=False`; the comment text is never interpolated into a shell command.
- Instructions are capped at `MAX_INSTRUCTION_CHARS` characters, default `2000`.
- Replies are capped at `MAX_OUTPUT_CHARS` characters, default `6000`.
- In-memory rate limits default to `PER_TASK_PER_MIN=3` and `GLOBAL_PER_MIN=20`.
- The bridge only acts on tasks in `CLICKUP_TEAM_ID`, default `90151427181`. If the webhook payload does not include a team id, the background task fetches task metadata from ClickUp before invoking an agent.
- Secrets are read only from the environment loaded by systemd.

## Environment

Required:

- `CLICKUP_WEBHOOK_SECRET`: ClickUp webhook signing secret.
- `CLICKUP_API_TOKEN`: token used to post task comments and, when needed, verify task metadata.
- `CLICKUP_TEAM_ID`: allowed ClickUp workspace/team id. Defaults to `90151427181`.

Agent-specific:

- `CLAUDE_CODE_OAUTH_TOKEN`: available to the Claude CLI.
- `CLAUDE2_CODE_OAUTH_TOKEN`: available to the Claude 2 CLI.
- `GEMINI_API_KEY`: available to the Gemini CLI.
- `JULES_API_KEY`: used for Jules session creation.

Optional:

- `CLICKUP_BOT_USER_ID`: ClickUp user id for the bridge bot; matching comments are ignored.
- `CLAUDE_BIN`: default `/home/ubuntu/.npm-global/bin/claude`.
- `CLAUDE2_BIN`: default `/home/ubuntu/.npm-global/bin/claude`.
- `GEMINI_BIN`: default `/home/ubuntu/.npm-global/bin/gemini`.
- `AGY_BIN`: default `/home/ubuntu/.local/bin/agy`.
- `CODEX_BIN`: default `codex`.
- `REPO`: default `/home/ubuntu/ai-betting`.
- `AGENT_TIMEOUT_SECONDS`: default `240`.
- `MAX_INSTRUCTION_CHARS`: default `2000`.
- `MAX_OUTPUT_CHARS`: default `6000`.
- `PER_TASK_PER_MIN`: default `3`.
- `GLOBAL_PER_MIN`: default `20`.

## Supervisor Deployment

Claude, as supervisor, handles deployment and registration.

Typical deployment steps for the supervisor:

1. Install Python dependencies for the host service environment from `services/clickup-bridge/requirements.txt`.
2. Install or symlink `services/clickup-bridge/clickup-bridge.service` into systemd.
3. Ensure `/home/ubuntu/ai-betting/.env` contains the required ClickUp and agent secrets.
4. Reload systemd, enable/start the service, and point the ClickUp webhook at the internal route exposed by nginx.
5. Register the ClickUp webhook with the same `CLICKUP_WEBHOOK_SECRET`.

Codex should not run, deploy, register, or restart this service.

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse


LOG = logging.getLogger("clickup_bridge")

REPLY_MARKER = "agent-reply::"

CLI_GUARDRAIL = (
    "You are answering a ClickUp message as a read-only assistant. "
    "Reply with TEXT ONLY. Do NOT edit, create, or delete files; do NOT run git, "
    "gh, commit, push, or open pull requests. If code changes are needed, describe "
    "them in your reply and tell the user to route the work to @jules.\n\n---\n\n"
)


def is_bot_reply(text):
    # SECURITY/loop-prevention: ClickUp escapes markdown brackets (e.g. [..] -> \[..\]),
    # so match the bracket-free token after stripping backslashes. Without this the
    # chat poller would answer its own replies forever (denial-of-wallet loop).
    return "agent-reply" in (text or "").replace(chr(92), "").lower()
CLICKUP_COMMENT_URL = "https://api.clickup.com/api/v2/task/{task_id}/comment"
CLICKUP_TASK_URL = "https://api.clickup.com/api/v2/task/{task_id}"
CLICKUP_CHAT_CHANNELS_URL = "https://api.clickup.com/api/v3/workspaces/{team_id}/chat/channels"
CLICKUP_CHAT_MESSAGES_URL = "https://api.clickup.com/api/v3/workspaces/{team_id}/chat/channels/{channel_id}/messages"
JULES_SESSIONS_URL = "https://jules.googleapis.com/v1alpha/sessions"
MENTION_RE = re.compile(r"@(claude2|claude|gemini|codex|agy|jules)\b", re.IGNORECASE)

app = FastAPI(title="ClickUp Agent Bridge")


@dataclass(frozen=True)
class Config:
    clickup_webhook_secret: str
    clickup_api_token: str
    clickup_team_id: str
    clickup_bot_user_id: str | None
    claude_bin: str
    claude2_bin: str
    gemini_bin: str
    agy_bin: str
    codex_bin: str
    repo: str
    agent_timeout_seconds: float
    max_instruction_chars: int
    max_output_chars: int
    per_task_per_min: int
    global_per_min: int
    jules_api_key: str | None
    chat_enabled: bool
    chat_poll_interval_seconds: float

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            clickup_webhook_secret=os.environ.get("CLICKUP_WEBHOOK_SECRET", ""),
            clickup_api_token=os.environ.get("CLICKUP_API_TOKEN", ""),
            clickup_team_id=os.environ.get("CLICKUP_TEAM_ID", "90151427181"),
            clickup_bot_user_id=os.environ.get("CLICKUP_BOT_USER_ID") or None,
            claude_bin=os.environ.get("CLAUDE_BIN", "/home/ubuntu/.npm-global/bin/claude"),
            claude2_bin=os.environ.get("CLAUDE2_BIN", "/home/ubuntu/.npm-global/bin/claude"),
            gemini_bin=os.environ.get("GEMINI_BIN", "/home/ubuntu/.npm-global/bin/gemini"),
            agy_bin=os.environ.get("AGY_BIN", "/home/ubuntu/.local/bin/agy"),
            codex_bin=os.environ.get("CODEX_BIN", "codex"),
            repo=os.environ.get("REPO", "/home/ubuntu/ai-betting"),
            agent_timeout_seconds=float(os.environ.get("AGENT_TIMEOUT_SECONDS", "240")),
            max_instruction_chars=int(os.environ.get("MAX_INSTRUCTION_CHARS", "2000")),
            max_output_chars=int(os.environ.get("MAX_OUTPUT_CHARS", "6000")),
            per_task_per_min=int(os.environ.get("PER_TASK_PER_MIN", "3")),
            global_per_min=int(os.environ.get("GLOBAL_PER_MIN", "20")),
            jules_api_key=os.environ.get("JULES_API_KEY") or None,
            chat_enabled=parse_env_bool(os.environ.get("CHAT_ENABLED", "true")),
            chat_poll_interval_seconds=float(os.environ.get("CHAT_POLL_INTERVAL_SECONDS", "15")),
        )


@dataclass(frozen=True)
class Mention:
    agent: str
    instruction: str


@dataclass(frozen=True)
class AgentRequest:
    task_id: str
    agent: str
    instruction: str
    payload_team_id: str | None


@dataclass(frozen=True)
class ChatBaseline:
    message_id: str | None
    date_ms: int | None


class MinuteRateLimiter:
    def __init__(self) -> None:
        self._global_hits: deque[float] = deque()
        self._task_hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, task_id: str, per_task_limit: int, global_limit: int) -> bool:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - 60
            self._prune(self._global_hits, cutoff)
            task_hits = self._task_hits[task_id]
            self._prune(task_hits, cutoff)

            if len(self._global_hits) >= global_limit or len(task_hits) >= per_task_limit:
                return False

            self._global_hits.append(now)
            task_hits.append(now)
            return True

    @staticmethod
    def _prune(hits: deque[float], cutoff: float) -> None:
        while hits and hits[0] < cutoff:
            hits.popleft()


rate_limiter = MinuteRateLimiter()


@app.get("/health")
async def health() -> PlainTextResponse:
    return PlainTextResponse("ok\n")


@app.on_event("startup")
async def start_chat_poller() -> None:
    config = Config.from_env()
    if not config.chat_enabled:
        LOG.info("ClickUp chat poller disabled by CHAT_ENABLED")
        return
    if not config.clickup_api_token:
        LOG.warning("ClickUp chat poller disabled: missing CLICKUP_API_TOKEN")
        return
    if not config.clickup_team_id:
        LOG.warning("ClickUp chat poller disabled: missing CLICKUP_TEAM_ID")
        return

    app.state.chat_poller_task = asyncio.create_task(chat_poll_loop(config))


@app.on_event("shutdown")
async def stop_chat_poller() -> None:
    task = getattr(app.state, "chat_poller_task", None)
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@app.post("/clickup/webhook")
async def clickup_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    config = Config.from_env()
    body = await request.body()
    verify_clickup_signature(body, request.headers.get("X-Signature"), config)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc

    if payload.get("event") != "taskCommentPosted":
        return JSONResponse({"status": "ignored", "reason": "event"})

    task_id = extract_task_id(payload)
    comment_text = extract_comment_text(payload)
    author_id = extract_author_id(payload)
    payload_team_id = extract_team_id(payload)

    if not task_id or not comment_text:
        return JSONResponse({"status": "ignored", "reason": "missing task or comment"})

    if payload_team_id and payload_team_id != config.clickup_team_id:
        return JSONResponse({"status": "ignored", "reason": "team"})

    if is_bot_reply(comment_text):
        return JSONResponse({"status": "ignored", "reason": "loop marker"})

    if config.clickup_bot_user_id and author_id == config.clickup_bot_user_id:
        return JSONResponse({"status": "ignored", "reason": "bot user"})

    mention = parse_first_mention(comment_text, config.max_instruction_chars)
    if mention is None:
        return JSONResponse({"status": "ignored", "reason": "no mention"})

    if not mention.instruction:
        background_tasks.add_task(
            post_clickup_comment_if_allowed,
            task_id,
            payload_team_id,
            mention.agent,
            "No instruction was provided after the agent mention.",
            config,
        )
        return JSONResponse({"status": "accepted"})

    if not await rate_limiter.allow(task_id, config.per_task_per_min, config.global_per_min):
        background_tasks.add_task(
            post_clickup_comment_if_allowed,
            task_id,
            payload_team_id,
            mention.agent,
            "Rate limited. Please wait before asking another agent from this task.",
            config,
        )
        return JSONResponse({"status": "accepted", "reason": "rate limited"})

    background_tasks.add_task(
        process_agent_request,
        AgentRequest(
            task_id=task_id,
            agent=mention.agent,
            instruction=mention.instruction,
            payload_team_id=payload_team_id,
        ),
        config,
    )
    return JSONResponse({"status": "accepted"})


async def chat_poll_loop(config: Config) -> None:
    baselines: dict[str, ChatBaseline] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        await initialize_chat_baselines(client, config, baselines)
        while True:
            await asyncio.sleep(config.chat_poll_interval_seconds)
            try:
                await poll_chat_once(client, config, baselines)
            except asyncio.CancelledError:
                raise
            except Exception:
                LOG.warning("ClickUp chat poll cycle failed", exc_info=True)


async def initialize_chat_baselines(
    client: httpx.AsyncClient,
    config: Config,
    baselines: dict[str, ChatBaseline],
) -> None:
    try:
        channels = await list_chat_channels(client, config)
    except Exception:
        LOG.warning("ClickUp chat baseline initialization failed while listing channels", exc_info=True)
        return

    for channel in channels:
        channel_id = stringify(channel.get("id")) if isinstance(channel, dict) else None
        if not channel_id:
            continue
        try:
            messages = await list_chat_messages(client, config, channel_id)
        except Exception:
            LOG.warning("ClickUp chat baseline initialization failed for channel %s", channel_id, exc_info=True)
            continue
        baselines[channel_id] = newest_chat_baseline(messages) or ChatBaseline(None, None)

    LOG.info("ClickUp chat poller initialized with %s channel baselines", len(baselines))


async def poll_chat_once(
    client: httpx.AsyncClient,
    config: Config,
    baselines: dict[str, ChatBaseline],
) -> None:
    try:
        channels = await list_chat_channels(client, config)
    except Exception:
        LOG.warning("ClickUp chat poll failed while listing channels", exc_info=True)
        return

    for channel in channels:
        if not isinstance(channel, dict):
            continue
        channel_id = stringify(channel.get("id"))
        if not channel_id:
            continue

        try:
            messages = await list_chat_messages(client, config, channel_id)
            previous = baselines.get(channel_id)
            if previous is None:
                baselines[channel_id] = newest_chat_baseline(messages) or ChatBaseline(None, None)
                LOG.info("ClickUp chat poller initialized new channel baseline for %s", channel_id)
                continue

            new_messages = [message for message in messages if chat_message_is_newer(message, previous)]
            newest = newest_chat_baseline(messages, previous) or previous

            for message in sorted(new_messages, key=chat_message_sort_key):
                await handle_chat_message(channel_id, message, config)

            baselines[channel_id] = newest
        except asyncio.CancelledError:
            raise
        except Exception:
            LOG.warning("ClickUp chat poll failed for channel %s", channel_id, exc_info=True)


async def handle_chat_message(channel_id: str, message: dict[str, Any], config: Config) -> None:
    text = extract_chat_message_text(message)
    if not text:
        return

    if is_bot_reply(text):
        return

    author_id = extract_chat_author_id(message)
    if config.clickup_bot_user_id and author_id == config.clickup_bot_user_id:
        return

    mention = parse_first_mention(text, config.max_instruction_chars)
    if mention is None:
        return

    send_field = chat_send_field_for_message(message)
    if not await rate_limiter.allow(channel_id, config.per_task_per_min, config.global_per_min):
        await post_clickup_chat_message(
            channel_id,
            mention.agent,
            "Rate limited. Please wait before asking another agent from this channel.",
            config,
            send_field,
        )
        return

    if not mention.instruction:
        await post_clickup_chat_message(
            channel_id,
            mention.agent,
            "No instruction was provided after the agent mention.",
            config,
            send_field,
        )
        return

    await process_chat_agent_request(
        AgentRequest(
            task_id=channel_id,
            agent=mention.agent,
            instruction=mention.instruction,
            payload_team_id=config.clickup_team_id,
        ),
        config,
        send_field,
    )


async def process_chat_agent_request(
    agent_request: AgentRequest,
    config: Config,
    send_field: str,
) -> None:
    try:
        if agent_request.agent == "jules":
            output = await call_jules(agent_request, config)
        else:
            output = await call_cli_agent(agent_request, config)
    except AgentFailure as exc:
        output = str(exc)
    except Exception:
        LOG.exception("Unexpected agent failure for ClickUp chat channel %s", agent_request.task_id)
        output = "Agent failed unexpectedly. Check the bridge logs for details."

    await post_clickup_chat_message(agent_request.task_id, agent_request.agent, output, config, send_field)


async def list_chat_channels(client: httpx.AsyncClient, config: Config) -> list[dict[str, Any]]:
    response = await client.get(
        CLICKUP_CHAT_CHANNELS_URL.format(team_id=config.clickup_team_id),
        headers={"Authorization": config.clickup_api_token},
    )
    if response.status_code >= 400:
        raise RuntimeError(f"ClickUp chat channel list failed with status {response.status_code}")

    data = response.json()
    channels = data.get("data")
    if not isinstance(channels, list):
        LOG.warning("ClickUp chat channel list response did not include a data array")
        return []
    return [channel for channel in channels if isinstance(channel, dict)]


async def list_chat_messages(
    client: httpx.AsyncClient,
    config: Config,
    channel_id: str,
) -> list[dict[str, Any]]:
    response = await client.get(
        CLICKUP_CHAT_MESSAGES_URL.format(team_id=config.clickup_team_id, channel_id=channel_id),
        headers={"Authorization": config.clickup_api_token},
    )
    if response.status_code >= 400:
        raise RuntimeError(f"ClickUp chat message list failed with status {response.status_code}")

    data = response.json()
    messages = data.get("data")
    if not isinstance(messages, list):
        LOG.warning("ClickUp chat message list response for channel %s did not include a data array", channel_id)
        return []
    return [message for message in messages if isinstance(message, dict)]


async def post_clickup_chat_message(
    channel_id: str,
    agent: str,
    output: str,
    config: Config,
    send_field: str,
) -> None:
    if not config.clickup_api_token:
        LOG.warning("Cannot post ClickUp chat reply without CLICKUP_API_TOKEN")
        return

    reply_text = f"{REPLY_MARKER} @{agent}:\n{truncate_output(output, config.max_output_chars)}"
    fields_to_try = [send_field]
    alternate = "text_content" if send_field == "content" else "content"
    if alternate not in fields_to_try:
        fields_to_try.append(alternate)

    async with httpx.AsyncClient(timeout=30) as client:
        for field in fields_to_try:
            response = await client.post(
                CLICKUP_CHAT_MESSAGES_URL.format(team_id=config.clickup_team_id, channel_id=channel_id),
                headers={"Authorization": config.clickup_api_token},
                json={field: reply_text},
            )
            if response.status_code < 400:
                return
            LOG.warning(
                "ClickUp chat reply post failed for channel %s using %s with status %s",
                channel_id,
                field,
                response.status_code,
            )


def newest_chat_baseline(
    messages: list[dict[str, Any]],
    current: ChatBaseline | None = None,
) -> ChatBaseline | None:
    newest = current
    for message in messages:
        baseline = chat_baseline_from_message(message)
        if baseline is None:
            continue
        if newest is None or chat_baseline_is_newer(baseline, newest):
            newest = baseline
    return newest


def chat_baseline_from_message(message: dict[str, Any]) -> ChatBaseline | None:
    message_id = stringify(message.get("id"))
    date_ms = parse_int(message.get("date"))
    if message_id is None and date_ms is None:
        return None
    return ChatBaseline(message_id=message_id, date_ms=date_ms)


def chat_message_is_newer(message: dict[str, Any], baseline: ChatBaseline) -> bool:
    candidate = chat_baseline_from_message(message)
    if candidate is None:
        return False
    return chat_baseline_is_newer(candidate, baseline)


def chat_baseline_is_newer(candidate: ChatBaseline, baseline: ChatBaseline) -> bool:
    candidate_id = parse_int(candidate.message_id)
    baseline_id = parse_int(baseline.message_id)
    if candidate_id is not None and baseline_id is not None:
        return candidate_id > baseline_id

    if candidate.date_ms is not None and baseline.date_ms is not None and candidate.date_ms != baseline.date_ms:
        return candidate.date_ms > baseline.date_ms

    if candidate.message_id is not None and baseline.message_id is not None:
        return candidate.message_id > baseline.message_id

    if candidate.date_ms is not None and baseline.date_ms is not None:
        return candidate.date_ms > baseline.date_ms

    return candidate.message_id is not None and baseline.message_id is None


def chat_message_sort_key(message: dict[str, Any]) -> tuple[int, int, str]:
    message_id = stringify(message.get("id"))
    parsed_id = parse_int(message_id)
    return (
        parsed_id if parsed_id is not None else -1,
        parse_int(message.get("date")) or 0,
        message_id or "",
    )


def extract_chat_message_text(message: dict[str, Any]) -> str | None:
    value = first_path(
        message,
        (
            ("text_content",),
            ("content",),
        ),
    )
    return normalize_comment_text(value)


def extract_chat_author_id(message: dict[str, Any]) -> str | None:
    value = first_path(
        message,
        (
            ("user_id",),
            ("author_id",),
            ("sender_id",),
            ("user", "id"),
            ("author", "id"),
            ("sender", "id"),
            ("creator", "id"),
            ("created_by",),
            ("created_by", "id"),
        ),
    )
    return stringify(value)


def chat_send_field_for_message(message: dict[str, Any]) -> str:
    if "content" in message:
        return "content"
    if "text_content" in message:
        return "text_content"
    return "content"


def verify_clickup_signature(body: bytes, signature: str | None, config: Config) -> None:
    if not config.clickup_webhook_secret:
        raise HTTPException(status_code=500, detail="missing webhook secret")
    if not signature:
        raise HTTPException(status_code=401, detail="missing signature")

    # SECURITY: Verify the ClickUp signature over the raw request body bytes.
    # Re-serializing JSON would change the bytes and invalidate the HMAC contract.
    expected = hmac.new(
        config.clickup_webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected.lower(), signature.lower()):
        raise HTTPException(status_code=401, detail="invalid signature")


def parse_first_mention(comment_text: str, max_instruction_chars: int) -> Mention | None:
    match = MENTION_RE.search(comment_text)
    if match is None:
        return None

    agent = match.group(1).lower()
    instruction = f"{comment_text[:match.start()]}{comment_text[match.end():]}".strip()

    # SECURITY: ClickUp comments are untrusted external input. Cap the amount of
    # data passed to agent CLIs so a single comment cannot drive unbounded work.
    if len(instruction) > max_instruction_chars:
        instruction = instruction[:max_instruction_chars].rstrip()

    return Mention(agent=agent, instruction=instruction)


async def process_agent_request(agent_request: AgentRequest, config: Config) -> None:
    if not await task_is_allowed(agent_request.task_id, agent_request.payload_team_id, config):
        LOG.info("Ignoring task %s outside allowed ClickUp team", agent_request.task_id)
        return

    try:
        if agent_request.agent == "jules":
            output = await call_jules(agent_request, config)
        else:
            output = await call_cli_agent(agent_request, config)
    except AgentFailure as exc:
        output = str(exc)
    except Exception:
        LOG.exception("Unexpected agent failure for task %s", agent_request.task_id)
        output = "Agent failed unexpectedly. Check the bridge logs for details."

    await post_clickup_comment(agent_request.task_id, agent_request.agent, output, config)


async def task_is_allowed(task_id: str, payload_team_id: str | None, config: Config) -> bool:
    if payload_team_id is not None:
        return payload_team_id == config.clickup_team_id

    if not config.clickup_api_token:
        LOG.warning("Cannot verify ClickUp task team without CLICKUP_API_TOKEN")
        return False

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            CLICKUP_TASK_URL.format(task_id=task_id),
            headers={"Authorization": config.clickup_api_token},
        )

    if response.status_code >= 400:
        LOG.warning("ClickUp task verification failed with status %s", response.status_code)
        return False

    task_data = response.json()
    return extract_team_id(task_data) == config.clickup_team_id


async def call_cli_agent(agent_request: AgentRequest, config: Config) -> str:
    command = cli_command(agent_request.agent, agent_request.instruction, config)
    env = os.environ.copy()

    if agent_request.agent == "claude2" and "CLAUDE2_CODE_OAUTH_TOKEN" in env:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = env["CLAUDE2_CODE_OAUTH_TOKEN"]

    # SECURITY: Never build a shell command string from untrusted ClickUp text.
    # The instruction is passed as one subprocess argument with shell=False.
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=config.repo,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, _stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=config.agent_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise AgentFailure(f"@{agent_request.agent} timed out after {int(config.agent_timeout_seconds)} seconds.") from exc

    if process.returncode != 0:
        LOG.warning("agent %s exit %s STDERR: %s", agent_request.agent, process.returncode, _stderr.decode("utf-8", "replace")[-800:])
        raise AgentFailure(f"@{agent_request.agent} exited with code {process.returncode}.")

    output = stdout.decode("utf-8", errors="replace").strip()
    if not output:
        return f"@{agent_request.agent} completed but returned no output."
    return output


def cli_command(agent: str, instruction: str, config: Config) -> list[str]:
    instruction = CLI_GUARDRAIL + instruction
    if agent == "claude2":
        return [config.claude2_bin, "-p", instruction]
    if agent == "claude":
        return [config.claude_bin, "-p", instruction]
    if agent == "gemini":
        return [config.gemini_bin, "-p", instruction]
    if agent == "codex":
        return [
            config.codex_bin,
            "exec",
            "--skip-git-repo-check",
            "-C",
            config.repo,
            "-m",
            "gpt-5.5",
            "--sandbox",
            "read-only",
            instruction,
        ]
    if agent == "agy":
        return [config.agy_bin, "--sandbox", "-p", instruction]
    raise AgentFailure(f"Unsupported agent @{agent}.")


async def call_jules(agent_request: AgentRequest, config: Config) -> str:
    if not config.jules_api_key:
        raise AgentFailure("@jules is not configured: missing JULES_API_KEY.")

    payload = {
        "prompt": agent_request.instruction,
        "title": f"ClickUp task {agent_request.task_id}",
        "sourceContext": {
            "source": "sources/github/dstavgr/ai-betting",
            "githubRepoContext": {"startingBranch": "main"},
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            JULES_SESSIONS_URL,
            headers={"X-Goog-Api-Key": config.jules_api_key},
            json=payload,
        )

    if response.status_code >= 400:
        raise AgentFailure(f"@jules session creation failed with status {response.status_code}.")

    data = response.json()
    session_url = (
        data.get("url")
        or data.get("sessionUrl")
        or data.get("session_url")
        or data.get("htmlUrl")
        or data.get("html_url")
    )
    if session_url:
        return f"Jules session created: {session_url}"

    session_name = data.get("name")
    if session_name:
        return f"Jules session created: {session_name}"

    return "Jules session created, but the API response did not include a session URL."


async def post_clickup_comment(task_id: str, agent: str, output: str, config: Config) -> None:
    if not config.clickup_api_token:
        LOG.warning("Cannot post ClickUp reply without CLICKUP_API_TOKEN")
        return

    comment_text = f"{REPLY_MARKER} @{agent}:\n{truncate_output(output, config.max_output_chars)}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            CLICKUP_COMMENT_URL.format(task_id=task_id),
            headers={"Authorization": config.clickup_api_token},
            json={"comment_text": comment_text},
        )

    if response.status_code >= 400:
        LOG.warning("ClickUp reply post failed with status %s", response.status_code)


async def post_clickup_comment_if_allowed(
    task_id: str,
    payload_team_id: str | None,
    agent: str,
    output: str,
    config: Config,
) -> None:
    if not await task_is_allowed(task_id, payload_team_id, config):
        LOG.info("Skipping ClickUp reply for task %s outside allowed team", task_id)
        return
    await post_clickup_comment(task_id, agent, output, config)


def truncate_output(output: str, max_chars: int) -> str:
    if len(output) <= max_chars:
        return output
    suffix = "\n\n[output truncated]"
    return output[: max(0, max_chars - len(suffix))].rstrip() + suffix


def extract_task_id(payload: dict[str, Any]) -> str | None:
    value = first_path(
        payload,
        (
            ("task_id",),
            ("task", "id"),
            ("history_items", 0, "task_id"),
            ("history_items", 0, "parent_id"),
        ),
    )
    return stringify(value)


def extract_comment_text(payload: dict[str, Any]) -> str | None:
    value = first_path(
        payload,
        (
            ("comment_text",),
            ("text",),
            ("comment",),
            ("comment", "text"),
            ("comment", "comment_text"),
            ("history_items", 0, "comment"),
            ("history_items", 0, "comment", "text"),
            ("history_items", 0, "data", "comment"),
            ("history_items", 0, "data", "comment_text"),
            ("history_items", 0, "data", "text"),
        ),
    )
    return normalize_comment_text(value)


def extract_author_id(payload: dict[str, Any]) -> str | None:
    value = first_path(
        payload,
        (
            ("user", "id"),
            ("author", "id"),
            ("comment", "user", "id"),
            ("comment", "author", "id"),
            ("history_items", 0, "user", "id"),
            ("history_items", 0, "comment", "user", "id"),
        ),
    )
    return stringify(value)


def extract_team_id(payload: dict[str, Any]) -> str | None:
    value = first_path(
        payload,
        (
            ("team_id",),
            ("workspace_id",),
            ("team", "id"),
            ("space", "team_id"),
            ("webhook", "team_id"),
            ("task", "team_id"),
            ("history_items", 0, "team_id"),
        ),
    )
    return stringify(value)


def first_path(payload: Any, paths: tuple[tuple[str | int, ...], ...]) -> Any:
    for path in paths:
        value = read_path(payload, path)
        if value is not None:
            return value
    return None


def read_path(value: Any, path: tuple[str | int, ...]) -> Any:
    current = value
    for part in path:
        if isinstance(part, int):
            if not isinstance(current, list) or len(current) <= part:
                return None
            current = current[part]
        else:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
    return current


def normalize_comment_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [normalize_comment_text(item) for item in value]
        return "".join(part for part in parts if part).strip() or None
    if isinstance(value, dict):
        for key in ("text", "comment_text", "plain_text", "content", "body", "comment"):
            text = normalize_comment_text(value.get(key))
            if text:
                return text
    return None


def stringify(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def parse_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def parse_env_bool(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "off"}


class AgentFailure(Exception):
    pass

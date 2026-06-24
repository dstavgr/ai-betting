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

REPLY_MARKER = "[agent-reply]"
CLICKUP_COMMENT_URL = "https://api.clickup.com/api/v2/task/{task_id}/comment"
CLICKUP_TASK_URL = "https://api.clickup.com/api/v2/task/{task_id}"
JULES_SESSIONS_URL = "https://jules.googleapis.com/v1alpha/sessions"
MENTION_RE = re.compile(r"@(claude|gemini|codex|agy|jules)\b", re.IGNORECASE)

app = FastAPI(title="ClickUp Agent Bridge")


@dataclass(frozen=True)
class Config:
    clickup_webhook_secret: str
    clickup_api_token: str
    clickup_team_id: str
    clickup_bot_user_id: str | None
    claude_bin: str
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

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            clickup_webhook_secret=os.environ.get("CLICKUP_WEBHOOK_SECRET", ""),
            clickup_api_token=os.environ.get("CLICKUP_API_TOKEN", ""),
            clickup_team_id=os.environ.get("CLICKUP_TEAM_ID", "90151427181"),
            clickup_bot_user_id=os.environ.get("CLICKUP_BOT_USER_ID") or None,
            claude_bin=os.environ.get("CLAUDE_BIN", "/home/ubuntu/.npm-global/bin/claude"),
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

    if comment_text.startswith(REPLY_MARKER):
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
        return [config.agy_bin, "-p", instruction]
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


class AgentFailure(Exception):
    pass

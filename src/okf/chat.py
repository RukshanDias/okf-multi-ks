"""OKF Server (`okf serve`): the persistent per-notebook loopback runtime
(ADR-0008 — evolved from the Chat bridge in ADR-0007's candidate design).

Serves the viewer over HTTP, relays Notebook chat to one coding agent ACP
subprocess (stdio, newline-delimited JSON-RPC, spawned lazily on first use —
a pure regenerate/off-board session never pays for a Node process it doesn't
need), and executes notebook actions (regenerate, off-board) in-process on
request — no subprocess/shell-out for those.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from okf.offboard import execute_offboard, plan_offboard
from okf.store import index_dir
from okf.viewer import generate_workspace_visualization

# Logical spawn argv per agent; argv[0] is resolved via PATH at spawn time
# (on Windows `npx`/`opencode` are .cmd shims).
DEFAULT_AGENTS: dict[str, list[str]] = {
    "claude": ["npx", "-y", "@agentclientprotocol/claude-agent-acp"],
    "opencode": ["opencode", "acp"],
}


# Fixed port + persisted token keep the viewer URL stable across runs so an
# already-open app window reconnects instead of a duplicate being spawned.
DEFAULT_CHAT_PORT = 48762


def load_chat_token(workspace_root: Path) -> str:
    """Per-notebook server token, minted once (overlay file, gitignored area).
    yagni: persistent loopback token, same trust boundary as the files the
    agent reads; rotate by deleting .okf/chat-token."""
    path = index_dir(Path(workspace_root)) / "chat-token"
    if path.is_file():
        token = path.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(16)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token + "\n", encoding="utf-8")
    return token


def find_chromium() -> str | None:
    """Edge/Chrome executable for an app-mode window; None when neither is
    installed (open_viewer() falls back to the OS default browser then)."""
    for name in ("msedge", "chrome", "chromium", "google-chrome"):
        exe = shutil.which(name)
        if exe:
            return exe
    program_dirs = [
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("ProgramFiles"),
    ]
    for base in filter(None, program_dirs):
        for rel in (
            r"Microsoft\Edge\Application\msedge.exe",
            r"Google\Chrome\Application\chrome.exe",
        ):
            candidate = Path(base) / rel
            if candidate.is_file():
                return str(candidate)
    # macOS: not on PATH by default (apps live under /Applications, not PATH).
    for app, binary in (
        ("Microsoft Edge.app", "Microsoft Edge"),
        ("Google Chrome.app", "Google Chrome"),
    ):
        candidate = Path("/Applications") / app / "Contents/MacOS" / binary
        if candidate.is_file():
            return str(candidate)
    return None


def open_viewer(url: str) -> None:
    """Open the viewer like the OKF Viewer shortcut: a Chromium app-mode
    window (standalone, own taskbar icon). Default browser as fallback."""
    exe = find_chromium()
    if exe:
        subprocess.Popen([exe, f"--app={url}"])
    else:
        webbrowser.open(url)


def _probe_server(port: int) -> dict | None:
    """Running OKF Server's /status, or None (port free / not our server)."""
    from urllib.request import urlopen

    try:
        with urlopen(f"http://127.0.0.1:{port}/status", timeout=2) as resp:
            data = json.loads(resp.read())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("okf") else None


def _has_console() -> bool:
    """False under pythonw (`okf-gui.exe serve`): the process has no std
    handles at all. Checked on the original stream because windowless_log()
    replaces sys.stderr with the log file."""
    return sys.__stderr__ is not None


def windowless_log(workspace_root: Path) -> None:
    """No console (`okf-gui.exe serve`: pythonw) -> our prints and the agent's
    stderr go to `.okf/serve.log`. Inheriting a windowless parent's stderr
    hands the child a pipe nobody reads; the ACP agent died on its first log
    line (mid session/new) and chat stayed dead for the server's lifetime."""
    if _has_console():
        return
    path = index_dir(Path(workspace_root)) / "serve.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = open(path, "a", encoding="utf-8", buffering=1)  # lives as long as the server


def run_server(agent_argv: list[str], *, workspace_root: Path, viz_path: Path) -> int:
    """Start (or reuse) OKF Server and get exactly one viewer window on it: a
    still-open window reconnects to the stable URL; a new window is spawned
    only when none is connected."""

    windowless_log(workspace_root)
    token = load_chat_token(workspace_root)
    port = DEFAULT_CHAT_PORT
    url = f"http://127.0.0.1:{port}/#chat={port}:{token}"

    existing = _probe_server(port)
    if existing is not None:
        if existing.get("client"):
            print("OKF Server already running with a connected viewer window", flush=True)
        else:
            print(f"OKF Server already running; opening {url}", flush=True)
            open_viewer(url)
        return 0

    async def serve() -> None:
        server = OKFServer(
            agent_argv, cwd=workspace_root, token=token, page=Path(viz_path)
        )
        await server.start(port)
        print(f"OKF Server listening on 127.0.0.1:{port}", flush=True)
        print(f"viewer url: {url}", flush=True)
        print("Ctrl+C to stop", flush=True)
        # Grace period: a viewer window left open from a previous run
        # reconnects on its own; only spawn a window if none shows up.
        await asyncio.sleep(2.5)
        if not server.client_connected:
            open_viewer(url)
        try:
            await asyncio.Event().wait()
        finally:
            await server.stop()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("OKF Server stopped")
    except OSError as e:
        print(f"error: cannot listen on 127.0.0.1:{port} ({e})", flush=True)
        return 1
    return 0


class OKFServer:
    """Persistent per-notebook loopback process (ADR-0008).

    Serves the viewer over HTTP, relays one viewer WebSocket to one agent ACP
    subprocess (ndjson stdio), and answers notebook action routes
    (regenerate, off-board) by calling the same functions the CLI uses,
    in-process — never a subprocess/shell-out, never a generic
    run-this-command endpoint.

    The viewer speaks raw ACP JSON-RPC frames over the socket; the bridge only
    intercepts session/request_permission to apply the write gate. Agent
    stderr is inherited so it lands in the `okf serve` terminal (serve.log
    when there is none, see windowless_log). The agent subprocess itself
    spawns lazily, on the first message a connected client sends — not at
    `start()` — so a session that only regenerates/off-boards never pays for
    it. If the agent exits, the viewer socket is closed with the exit code as
    reason and the next message spawns a fresh one.
    """

    def __init__(
        self,
        agent_argv: list[str],
        *,
        cwd: Path,
        token: str,
        page: Path | None = None,
    ) -> None:
        self._argv = list(agent_argv)
        self._cwd = Path(cwd)
        self._token = token
        self._page = Path(page) if page is not None else None
        self._proc: asyncio.subprocess.Process | None = None
        self._server = None
        self._pump_task: asyncio.Task | None = None
        self._client = None

    @property
    def client_connected(self) -> bool:
        return self._client is not None

    @property
    def agent_spawned(self) -> bool:
        return self._proc is not None

    async def start(self, port: int = 0) -> int:
        """Listen on 127.0.0.1; return the bound port. Does not spawn the
        agent — see `_ensure_agent`."""
        import websockets

        self._server = await websockets.serve(
            self._handle_client, "127.0.0.1", port, process_request=self._serve_page
        )
        return self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._pump_task is not None:
            self._pump_task.cancel()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            await self._proc.wait()

    async def _ensure_agent(self) -> asyncio.subprocess.Process:
        """Spawn the ACP agent subprocess on first use (ADR-0008). Returns the
        live process so callers keep their own reference instead of re-reading
        `self._proc`, which `_agent_gone` may clear at any suspension point."""
        if self._proc is not None:
            return self._proc
        # PATH lookup so `npx`/`opencode` resolve to their .cmd shims on Windows.
        exe = shutil.which(self._argv[0]) or self._argv[0]
        # Windowless server (pythonw): stderr goes to serve.log (windowless_log
        # put it in sys.stderr; never inherit — that pipe has no reader) and the
        # console-subsystem chain (npx/node/claude) must not pop a console window.
        console = _has_console()
        self._proc = await asyncio.create_subprocess_exec(
            exe,
            *self._argv[1:],
            cwd=self._cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None if console else (sys.stderr or subprocess.DEVNULL),
            creationflags=0 if console or os.name != "nt" else subprocess.CREATE_NO_WINDOW,
        )
        self._pump_task = asyncio.ensure_future(self._pump_agent(self._proc))
        return self._proc

    async def _agent_gone(self, proc: asyncio.subprocess.Process) -> None:
        """Forget a dead agent so the next message respawns one, and tell the
        viewer why its in-flight request died (close reason), so it shows the
        cause instead of a bare 'disconnected' and re-runs its handshake."""
        if self._proc is not proc:
            return  # already handled (write failure and pump EOF can both notice)
        self._proc = None
        try:
            # Bounded: asyncio's Windows wait() also needs every inherited pipe
            # closed, which an orphaned grandchild (npx shim chain) can hold.
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            pass
        code = proc.returncode
        code_s = str(code) if code is not None else "unknown"
        reason = f"agent exited (code {code_s})"
        print(f"[chat] {reason}", flush=True)
        if self._client is not None:
            await self._client.close(1011, reason)

    def _serve_page(self, connection, request):
        """Answer plain HTTP GETs: /status, the viewer page, and the token-
        gated action routes (/regenerate, /offboard). OKF Server runs the
        viewer from a loopback http origin because browsers (Chrome's Local
        Network Access) can gate a file:// page's WebSocket to 127.0.0.1."""
        if "websocket" in request.headers.get("Upgrade", "").lower():
            return None  # continue the WS handshake
        from http import HTTPStatus

        from websockets.datastructures import Headers
        from websockets.http11 import Response

        def respond(status: HTTPStatus, content_type: str, body: bytes):
            headers = Headers(
                [
                    ("Content-Type", content_type),
                    ("Content-Length", str(len(body))),
                    ("Connection", "close"),
                ]
            )
            return Response(status, status.phrase, headers, body)

        def json_response(status: HTTPStatus, payload: dict):
            return respond(status, "application/json", json.dumps(payload).encode("utf-8"))

        parsed = urlparse(request.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/status":
            return json_response(HTTPStatus.OK, {"okf": True, "client": self._client is not None})

        if path in ("/regenerate", "/offboard"):
            if query.get("token") != [self._token]:
                return json_response(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "invalid token"})
            if self._page is None:
                return connection.respond(HTTPStatus.NOT_FOUND, "not found\n")
            try:
                if path == "/regenerate":
                    stats = generate_workspace_visualization(self._cwd, self._page)
                    result = {"ok": True, **stats}
                else:
                    label = (query.get("label") or [None])[0]
                    if not label:
                        return json_response(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing label"})
                    plan = plan_offboard(self._cwd, label)
                    execute_offboard(self._cwd, plan)
                    stats = generate_workspace_visualization(self._cwd, self._page)
                    result = {"ok": True, "label": label, **stats}
                return json_response(HTTPStatus.OK, result)
            except Exception as e:
                return json_response(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(e)})

        if self._page is not None and path == "/":
            return respond(HTTPStatus.OK, "text/html; charset=utf-8", self._page.read_bytes())

        return connection.respond(HTTPStatus.NOT_FOUND, "not found\n")

    @staticmethod
    def _log_event(msg: dict) -> None:
        """Terminal breadcrumb for the prompt round-trip. yagni: two events
        only (prompt out, final response in); the agent's own stderr already
        carries the detailed phase logs."""
        if msg.get("method") == "session/prompt":
            print("[chat] prompt sent to agent", flush=True)
        elif isinstance(msg.get("result"), dict) and "stopReason" in msg["result"]:
            stop = msg["result"]["stopReason"]
            print(f"[chat] response received (stopReason={stop})", flush=True)

    async def _send_agent(
        self, proc: asyncio.subprocess.Process, obj: dict
    ) -> None:
        proc.stdin.write(json.dumps(obj).encode("utf-8") + b"\n")
        await proc.stdin.drain()

    async def _handle_client(self, ws) -> None:
        from websockets.exceptions import ConnectionClosed

        query = parse_qs(urlparse(ws.request.path).query)
        if query.get("token") != [self._token]:
            await ws.close(1008, "invalid token")
            return
        if self._client is not None:
            await ws.close(1013, "chat already connected in another tab")
            return
        self._client = ws
        try:
            async for raw in ws:  # viewer -> agent
                text = raw if isinstance(raw, str) else raw.decode("utf-8")
                try:
                    self._log_event(json.loads(text))
                except json.JSONDecodeError:
                    pass
                proc = await self._ensure_agent()
                try:
                    proc.stdin.write(text.strip().encode("utf-8") + b"\n")
                    await proc.stdin.drain()
                except OSError:  # agent died under us (broken stdin pipe)
                    await self._agent_gone(proc)
                    return
        except ConnectionClosed:
            pass  # viewer went away, or _agent_gone closed it on purpose
        finally:
            self._client = None

    async def _pump_agent(self, proc: asyncio.subprocess.Process) -> None:
        while True:
            line = await proc.stdout.readline()
            if not line:
                await self._agent_gone(proc)
                return
            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                continue  # stray non-protocol output; don't kill the relay
            self._log_event(msg)
            if msg.get("method") == "session/request_permission" and "id" in msg:
                outcome = route_permission(msg.get("params") or {})
                if outcome is not None:
                    await self._send_agent(
                        proc,
                        {"jsonrpc": "2.0", "id": msg["id"], "result": {"outcome": outcome}},
                    )
                    continue
            if self._client is not None:
                await self._client.send(text)


# Write gate (grill 2026-09-05): reads flow, raw file mutations are never
# sanctioned (Separation rule risk), everything else — incl. `okf associate`
# executes — goes to the human as an approve/deny card.
_AUTO_ALLOW_KINDS = {"read", "search", "fetch"}
_AUTO_DENY_KINDS = {"edit", "delete", "move"}


def _pick_option(options: list[dict], prefix: str) -> str | None:
    for opt in options:
        if str(opt.get("kind", "")).startswith(prefix):
            return opt.get("optionId")
    return None


def route_permission(params: dict) -> dict | None:
    """Auto-response outcome for an ACP session/request_permission, or None
    to forward the request to the human in the chat panel."""
    kind = (params.get("toolCall") or {}).get("kind")
    options = params.get("options") or []
    if kind in _AUTO_ALLOW_KINDS:
        option_id = _pick_option(options, "allow")
    elif kind in _AUTO_DENY_KINDS:
        option_id = _pick_option(options, "reject")
    else:
        return None
    if option_id is None:
        return None
    return {"outcome": "selected", "optionId": option_id}


def resolve_agent(name: str | None, workspace_root: Path) -> list[str]:
    """Spawn argv for the requested agent.

    Machine-local registry lives in the Notebook home's config.json
    (`agents`: {name: argv-or-string}, `default_agent`), merged over built-in
    claude/opencode defaults.
    """
    agents = dict(DEFAULT_AGENTS)
    default = "claude"
    config_path = index_dir(Path(workspace_root)) / "config.json"
    if config_path.is_file():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        for label, argv in (raw.get("agents") or {}).items():
            agents[label] = [argv] if isinstance(argv, str) else list(argv)
        default = raw.get("default_agent") or default
    if name is None:
        name = default
    if name not in agents:
        known = ", ".join(sorted(agents))
        raise ValueError(f"unknown agent {name!r} (known: {known})")
    return list(agents[name])

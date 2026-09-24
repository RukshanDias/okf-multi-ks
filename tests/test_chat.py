"""OKF Server: agent registry, write-gate policy, viewer/action routes, relay."""

from __future__ import annotations

import asyncio
import json
import sys

import pytest

import okf.chat as chat_mod
from okf.chat import OKFServer, resolve_agent, route_permission
from okf.cli import main


def test_resolve_agent_builtin_defaults(tmp_path):
    assert resolve_agent("opencode", tmp_path) == ["opencode", "acp"]
    # Bare `okf serve` uses claude unless config says otherwise.
    assert resolve_agent(None, tmp_path) == resolve_agent("claude", tmp_path)
    # -y is load-bearing: npx's install prompt would otherwise eat the ACP stdin pipe.
    assert resolve_agent("claude", tmp_path) == [
        "npx",
        "-y",
        "@agentclientprotocol/claude-agent-acp",
    ]


def test_resolve_agent_config_overrides_and_default(tmp_path):
    overlay = tmp_path / ".okf"
    overlay.mkdir()
    (overlay / "config.json").write_text(
        json.dumps(
            {
                "agents": {"claude": ["my-claude", "--acp"], "custom": "my-agent"},
                "default_agent": "custom",
            }
        ),
        encoding="utf-8",
    )
    assert resolve_agent("claude", tmp_path) == ["my-claude", "--acp"]
    assert resolve_agent(None, tmp_path) == ["my-agent"]
    # Built-ins not overridden stay available.
    assert resolve_agent("opencode", tmp_path) == ["opencode", "acp"]


def test_resolve_agent_unknown_name_errors(tmp_path):
    with pytest.raises(ValueError, match="claude"):
        resolve_agent("nope", tmp_path)


def test_chat_token_persists_across_runs(tmp_path):
    """Stable token + fixed port -> viewer URL identical every run, so an
    already-open app window can reconnect instead of spawning a duplicate."""
    first = chat_mod.load_chat_token(tmp_path)
    assert first
    assert chat_mod.load_chat_token(tmp_path) == first
    assert (tmp_path / ".okf" / "chat-token").read_text(encoding="utf-8").strip() == first


def test_server_status_endpoint_reports_client_presence(tmp_path):
    import websockets
    from urllib.request import urlopen

    async def status(port):
        return json.loads(
            await asyncio.to_thread(
                lambda: urlopen(f"http://127.0.0.1:{port}/status", timeout=10).read()
            )
        )

    async def scenario():
        server = _fake_server(tmp_path)
        port = await server.start()
        try:
            assert await status(port) == {"okf": True, "client": False}
            async with websockets.connect(f"ws://127.0.0.1:{port}/?token=tok"):
                assert await status(port) == {"okf": True, "client": True}
        finally:
            await server.stop()

    asyncio.run(scenario())


def test_open_viewer_uses_chromium_app_window(monkeypatch):
    """Server opens like the OKF Viewer shortcut (install_viewer_shortcut.ps1):
    a Chromium app-mode window, not a regular browser tab."""
    launched = []
    monkeypatch.setattr(chat_mod, "find_chromium", lambda: "C:/fake/msedge.exe")
    monkeypatch.setattr(
        chat_mod.subprocess, "Popen", lambda argv, **kw: launched.append(argv)
    )
    chat_mod.open_viewer("http://127.0.0.1:1/#chat=1:t")
    assert launched == [["C:/fake/msedge.exe", "--app=http://127.0.0.1:1/#chat=1:t"]]


def test_open_viewer_falls_back_to_default_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(chat_mod, "find_chromium", lambda: None)
    monkeypatch.setattr(chat_mod.webbrowser, "open", lambda url: opened.append(url))
    chat_mod.open_viewer("http://127.0.0.1:1/")
    assert opened == ["http://127.0.0.1:1/"]


def test_cli_serve_unknown_agent_errors(tmp_path, capsys):
    assert main(["--workspace", str(tmp_path), "serve", "--agent", "nope"]) == 1
    assert "unknown agent" in capsys.readouterr().err


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_generated_viz_ships_inert_chat_panel(workspace_root, tmp_path):
    """The panel is in every viz.html but stays hidden unless the page is
    opened by `okf serve` with a #chat=port:token fragment (static viewer
    keeps working with no server)."""
    from okf.viewer import generate_workspace_visualization

    out = tmp_path / "viz.html"
    generate_workspace_visualization(workspace_root, out)
    html = out.read_text(encoding="utf-8")
    assert 'id="chat-panel" hidden' in html
    assert "#chat=" in html  # fragment gate lives in the bundled viz.js
    # Header toggle ships hidden too; initChat reveals it only with a server.
    assert 'id="chat-toggle"' in html
    assert html.index('id="chat-toggle"') < html.index('id="chat-panel"')
    # display:flex etc. must never override the hidden attribute (toggle bug).
    assert "[hidden] { display: none !important; }" in html
    # Closed by default even under `okf serve`; the drag handle ships with it.
    assert "panel.hidden = false" not in html
    assert 'id="chat-resizer"' in html
    assert 'id="chat-skill"' in html


def _perm_request(kind: str, options: list | None = None) -> dict:
    """ACP session/request_permission params as the agent sends them."""
    if options is None:
        options = [
            {"optionId": "yes", "name": "Allow", "kind": "allow_once"},
            {"optionId": "no", "name": "Reject", "kind": "reject_once"},
        ]
    return {"sessionId": "s1", "toolCall": {"kind": kind}, "options": options}


def test_route_permission_auto_allows_reads():
    for kind in ("read", "search", "fetch"):
        assert route_permission(_perm_request(kind)) == {
            "outcome": "selected",
            "optionId": "yes",
        }


def test_route_permission_auto_denies_raw_edits():
    for kind in ("edit", "delete", "move"):
        assert route_permission(_perm_request(kind)) == {
            "outcome": "selected",
            "optionId": "no",
        }


def test_route_permission_forwards_executes_to_human():
    # `okf associate` / ingest arrive as execute tool calls: human decides.
    assert route_permission(_perm_request("execute")) is None
    assert route_permission(_perm_request("other")) is None


def test_route_permission_forwards_when_no_matching_option():
    only_allow = [{"optionId": "yes", "name": "Allow", "kind": "allow_once"}]
    assert route_permission(_perm_request("edit", options=only_allow)) is None


# A stand-in ACP agent speaking newline-delimited JSON-RPC on stdio:
# `ping` answers directly; `noisy` logs to stderr first (like the real agent's
# phase logs); `die` exits with code 3; `ask_read`/`ask_exec` first raise a
# session/request_permission (kind read/execute) and echo the outcome back.
FAKE_AGENT = r"""
import json
import sys

def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

pending = {}
next_id = 1000
for line in sys.stdin:
    msg = json.loads(line)
    if msg.get("method") == "ping":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"pong": True}})
    elif msg.get("method") == "noisy":
        sys.stderr.write("[phase] booting\n")
        sys.stderr.flush()
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"pong": True}})
    elif msg.get("method") == "die":
        sys.exit(3)
    elif msg.get("method") in ("ask_read", "ask_exec"):
        kind = "read" if msg["method"] == "ask_read" else "execute"
        rid = next_id
        next_id += 1
        pending[rid] = msg["id"]
        send({
            "jsonrpc": "2.0", "id": rid,
            "method": "session/request_permission",
            "params": {
                "sessionId": "s", "toolCall": {"kind": kind},
                "options": [
                    {"optionId": "yes", "name": "Allow", "kind": "allow_once"},
                    {"optionId": "no", "name": "Reject", "kind": "reject_once"},
                ],
            },
        })
    elif "id" in msg and msg["id"] in pending:
        send({"jsonrpc": "2.0", "id": pending.pop(msg["id"]),
              "result": msg.get("result")})
"""


def _fake_server(tmp_path, page=None) -> OKFServer:
    script = tmp_path / "fake_agent.py"
    script.write_text(FAKE_AGENT, encoding="utf-8")
    return OKFServer([sys.executable, str(script)], cwd=tmp_path, token="tok", page=page)


def test_agent_exit_closes_viewer_with_reason_and_respawns_on_next_message(tmp_path):
    """Regression: a dead agent used to stay cached in the server, so every
    later message hit a broken stdin pipe, the handler raised and the viewer
    saw a bare 'disconnected' forever (while /regenerate kept working). Now
    the viewer is told why, and the next message gets a fresh agent."""
    import websockets

    async def scenario():
        server = _fake_server(tmp_path)
        port = await server.start()
        try:
            uri = f"ws://127.0.0.1:{port}/?token=tok"
            async with websockets.connect(uri) as ws:
                await _rpc(ws, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "die"}))
                with pytest.raises(websockets.exceptions.ConnectionClosed) as exc_info:
                    await asyncio.wait_for(ws.recv(), timeout=10)
            assert exc_info.value.rcvd.code == 1011
            assert exc_info.value.rcvd.reason == "agent exited (code 3)"
            assert server.agent_spawned is False
            for _ in range(100):  # handler cleanup runs just after the close frame
                if not server.client_connected:
                    break
                await asyncio.sleep(0.02)
            assert server.client_connected is False

            # Viewer reconnects (viz-chat.js does this itself) and chats again.
            async with websockets.connect(uri) as ws:
                reply = await _rpc(ws, {"jsonrpc": "2.0", "id": 3, "method": "ping"})
                assert reply["result"] == {"pong": True}
                assert server.agent_spawned is True
        finally:
            await server.stop()

    asyncio.run(scenario())


def test_windowless_server_logs_agent_stderr_and_hides_console(tmp_path, monkeypatch):
    """pythonw (`okf-gui.exe serve`) has no std handles. Inheriting stderr
    handed the agent a closed pipe and killed it on its first log line — the
    bug behind the viewer's 'disconnected' after the first message. Now its
    stderr follows windowless_log's redirect, and the agent chain gets no
    console window of its own."""
    import subprocess

    import websockets

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(sys, "__stderr__", None)
    chat_mod.windowless_log(tmp_path)
    log_path = tmp_path / ".okf" / "serve.log"
    assert sys.stdout is sys.stderr and sys.stderr.name == str(log_path)

    spawn_kwargs = {}
    real_spawn = asyncio.create_subprocess_exec

    async def spy(*args, **kwargs):
        spawn_kwargs.update(kwargs)
        return await real_spawn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    async def scenario():
        server = _fake_server(tmp_path)
        port = await server.start()
        try:
            async with websockets.connect(f"ws://127.0.0.1:{port}/?token=tok") as ws:
                reply = await _rpc(ws, {"jsonrpc": "2.0", "id": 1, "method": "noisy"})
                assert reply["result"] == {"pong": True}
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "die"}))
                with pytest.raises(websockets.exceptions.ConnectionClosed):
                    await asyncio.wait_for(ws.recv(), timeout=10)
        finally:
            await server.stop()

    asyncio.run(scenario())
    sys.stderr.close()
    assert "[phase] booting" in log_path.read_text(encoding="utf-8")  # agent stderr
    assert "[chat] agent exited" in log_path.read_text(encoding="utf-8")  # our prints
    if sys.platform == "win32":
        assert spawn_kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW


def test_windowless_log_is_noop_with_a_console(tmp_path):
    chat_mod.windowless_log(tmp_path)
    assert not (tmp_path / ".okf" / "serve.log").exists()


async def _rpc(ws, request: dict) -> dict:
    await ws.send(json.dumps(request))
    return json.loads(await asyncio.wait_for(ws.recv(), timeout=10))


def test_server_relays_jsonrpc_both_ways(tmp_path):
    import websockets

    async def scenario():
        server = _fake_server(tmp_path)
        port = await server.start()
        try:
            uri = f"ws://127.0.0.1:{port}/?token=tok"
            async with websockets.connect(uri) as ws:
                reply = await _rpc(ws, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
                assert reply == {"jsonrpc": "2.0", "id": 1, "result": {"pong": True}}
        finally:
            await server.stop()

    asyncio.run(scenario())


def test_agent_subprocess_spawns_lazily_on_first_message(tmp_path):
    """ADR-0008: a session that never chats never pays for the Node process —
    start() must not spawn it; only the first inbound client message does."""
    import websockets

    async def scenario():
        server = _fake_server(tmp_path)
        port = await server.start()
        try:
            assert server.agent_spawned is False
            uri = f"ws://127.0.0.1:{port}/?token=tok"
            async with websockets.connect(uri) as ws:
                assert server.agent_spawned is False
                await _rpc(ws, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
                assert server.agent_spawned is True
        finally:
            await server.stop()

    asyncio.run(scenario())


def test_server_answers_read_permission_itself_and_forwards_execute(tmp_path):
    import websockets

    async def scenario():
        server = _fake_server(tmp_path)
        port = await server.start()
        try:
            uri = f"ws://127.0.0.1:{port}/?token=tok"
            async with websockets.connect(uri) as ws:
                # Read: server auto-allows; the viewer only ever sees the
                # agent's final answer, never a permission request.
                reply = await _rpc(ws, {"jsonrpc": "2.0", "id": 2, "method": "ask_read"})
                assert reply["id"] == 2
                assert reply["result"]["outcome"] == {
                    "outcome": "selected",
                    "optionId": "yes",
                }

                # Execute: forwarded to the human, whose choice reaches the agent.
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ask_exec"}))
                perm = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                assert perm["method"] == "session/request_permission"
                assert perm["params"]["toolCall"]["kind"] == "execute"
                await ws.send(json.dumps({
                    "jsonrpc": "2.0", "id": perm["id"],
                    "result": {"outcome": {"outcome": "selected", "optionId": "no"}},
                }))
                reply = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                assert reply["id"] == 3
                assert reply["result"]["outcome"] == {
                    "outcome": "selected",
                    "optionId": "no",
                }
        finally:
            await server.stop()

    asyncio.run(scenario())


def test_server_serves_viewer_page_over_http(tmp_path):
    """OKF Server opens the viewer from http://127.0.0.1 (not file://) so
    browsers never gate the loopback WebSocket behind Local Network Access."""
    from urllib.request import urlopen

    page = tmp_path / "viz.html"
    page.write_text("<html>VIEWER</html>", encoding="utf-8")
    server = _fake_server(tmp_path, page=page)

    async def scenario():
        port = await server.start()
        try:
            body = await asyncio.to_thread(
                lambda: urlopen(f"http://127.0.0.1:{port}/", timeout=10).read()
            )
            assert body == b"<html>VIEWER</html>"
        finally:
            await server.stop()

    asyncio.run(scenario())


def _seed_workspace(root, label="personal"):
    from tests.conftest import write_concept

    (root / "okf.yaml").write_text(
        f"version: 1\nks:\n  {label}:\n    path: ks/{label}\n", encoding="utf-8"
    )
    write_concept(
        root / "ks" / label / "note.md",
        type_="Learning",
        title="Note",
        description="A note.",
        body="Body.\n",
    )


def test_regenerate_route_calls_generator_in_process(tmp_path):
    """Actions 'Regenerate now' hits this route, which calls
    generate_workspace_visualization directly in the server process — no
    subprocess, no shell-out to the CLI (ADR-0008 supersedes the copy-command
    flow in ADR-0003 for server-mode viewing)."""
    from urllib.request import urlopen

    _seed_workspace(tmp_path)
    page = tmp_path / "viz.html"
    server = _fake_server(tmp_path, page=page)

    async def scenario():
        port = await server.start()
        try:
            return await asyncio.to_thread(
                lambda: urlopen(
                    f"http://127.0.0.1:{port}/regenerate?token=tok", timeout=10
                ).read()
            )
        finally:
            await server.stop()

    result = json.loads(asyncio.run(scenario()))
    assert result["ok"] is True
    assert result["concepts"] == 1
    assert page.is_file()


def test_action_routes_reject_missing_or_wrong_token(tmp_path):
    """ADR-0008: action routes require the same per-notebook token the chat
    WebSocket already checks — closing the gap the first PoC left open."""
    from urllib.error import HTTPError
    from urllib.request import urlopen

    _seed_workspace(tmp_path)
    page = tmp_path / "viz.html"

    async def scenario(url):
        server = _fake_server(tmp_path, page=page)
        port = await server.start()
        try:
            return await asyncio.to_thread(
                lambda: urlopen(f"http://127.0.0.1:{port}{url}", timeout=10)
            )
        finally:
            await server.stop()

    for bad_url in ("/regenerate", "/regenerate?token=WRONG", "/offboard?label=personal"):
        with pytest.raises(HTTPError) as exc_info:
            asyncio.run(scenario(bad_url))
        assert exc_info.value.code == 401
    assert not page.is_file()


def test_offboard_route_deregisters_and_regenerates_viz(tmp_path):
    """Off-board button: one call deregisters the KS and refreshes viz.html,
    same write set as `okf offboard <label> --yes` (ADR-0006), no subprocess."""
    from urllib.request import urlopen

    _seed_workspace(tmp_path)
    page = tmp_path / "viz.html"
    server = _fake_server(tmp_path, page=page)

    async def scenario():
        port = await server.start()
        try:
            return await asyncio.to_thread(
                lambda: urlopen(
                    f"http://127.0.0.1:{port}/offboard?label=personal&token=tok",
                    timeout=10,
                ).read()
            )
        finally:
            await server.stop()

    result = json.loads(asyncio.run(scenario()))
    assert result == {"ok": True, "label": "personal", "concepts": 0, "edges": 0, "bytes": result["bytes"]}
    config = (tmp_path / "okf.yaml").read_text(encoding="utf-8")
    assert "personal" not in config


def test_offboard_route_unknown_label_errors_without_writing(tmp_path):
    from urllib.error import HTTPError
    from urllib.request import urlopen

    _seed_workspace(tmp_path)
    page = tmp_path / "viz.html"
    server = _fake_server(tmp_path, page=page)

    async def scenario():
        port = await server.start()
        try:
            return await asyncio.to_thread(
                lambda: urlopen(
                    f"http://127.0.0.1:{port}/offboard?label=nope&token=tok", timeout=10
                ).read()
            )
        except HTTPError as e:
            return e.read()
        finally:
            await server.stop()

    result = json.loads(asyncio.run(scenario()))
    assert result["ok"] is False
    assert "nope" in result["error"]
    assert not page.is_file()
    assert "personal:" in (tmp_path / "okf.yaml").read_text(encoding="utf-8")


def test_log_event_marks_prompt_roundtrip_only(capsys):
    OKFServer._log_event({"jsonrpc": "2.0", "id": 1, "method": "session/prompt"})
    OKFServer._log_event({"jsonrpc": "2.0", "id": 1, "result": {"stopReason": "end_turn"}})
    # Streaming chunks and permission traffic stay quiet.
    OKFServer._log_event({"jsonrpc": "2.0", "method": "session/update", "params": {}})
    OKFServer._log_event({"jsonrpc": "2.0", "id": 2, "result": {"outcome": {}}})
    assert capsys.readouterr().out.splitlines() == [
        "[chat] prompt sent to agent",
        "[chat] response received (stopReason=end_turn)",
    ]


def test_server_rejects_wrong_token(tmp_path):
    import websockets

    async def scenario():
        server = _fake_server(tmp_path)
        port = await server.start()
        try:
            async with websockets.connect(f"ws://127.0.0.1:{port}/?token=WRONG") as ws:
                with pytest.raises(websockets.exceptions.ConnectionClosed):
                    await _rpc(ws, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
        finally:
            await server.stop()

    asyncio.run(scenario())

// Notebook chat: ACP client over OKF Server. Gated on the #chat=port:token
// fragment (chatFrag, parsed once in viz-core.js) that only `okf serve`
// produces — without it the panel stays hidden and the viewer is the plain
// static file (ADR-0003). The WebSocket connects as soon as the page loads;
// the ACP handshake (and the agent subprocess it requires) is deferred to
// the first message the user actually sends (ADR-0008).
(function initChat() {
  if (!chatFrag) return;
  const panel = document.getElementById("chat-panel");
  const messages = document.getElementById("chat-messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");
  const cancelBtn = document.getElementById("chat-cancel");
  const statusEl = document.getElementById("chat-status");
  const chip = document.getElementById("chat-chip");
  const chipLabel = document.getElementById("chat-chip-label");

  const toggle = document.getElementById("chat-toggle");
  toggle.hidden = false;
  toggle.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
    renderer.resize(); // the graph pane just gained or lost the panel's width
  });

  // Drag the panel's left edge to resize it. Pointer capture releases itself
  // on pointerup, so no document-level listeners are needed.
  const resizer = document.getElementById("chat-resizer");
  resizer.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    resizer.setPointerCapture(e.pointerId);
  });
  resizer.addEventListener("pointermove", (e) => {
    if (!resizer.hasPointerCapture(e.pointerId)) return;
    const want = panel.getBoundingClientRect().right - e.clientX;
    const width = Math.min(Math.max(want, 240), window.innerWidth * 0.6);
    panel.style.flexBasis = `${width}px`;
    renderer.resize();
  });

  // Selection chip: user-controlled context (grill 2026-09-05)
  let context = null;
  chatSelect = (data) => {
    context = { id: data.id, label: data.label };
    chipLabel.textContent = data.label;
    chip.hidden = false;
  };
  document.getElementById("chat-chip-remove").addEventListener("click", () => {
    context = null;
    chip.hidden = true;
  });

  let ws = null;
  let nextId = 1;
  const pending = new Map();
  let sessionId = null;
  let agentBuf = "";
  let agentEl = null;
  const toolEls = new Map();

  function setStatus(text) { statusEl.textContent = text; }
  function jsonSend(obj) { ws.send(JSON.stringify(obj)); }
  function request(method, params) {
    return new Promise((resolve, reject) => {
      const id = nextId++;
      pending.set(id, { resolve, reject });
      jsonSend({ jsonrpc: "2.0", id, method, params });
    });
  }
  function addMsg(cls) {
    const div = document.createElement("div");
    div.className = `chat-msg ${cls}`;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function onOpen() {
    // Connected, but no ACP session yet — that (and the agent subprocess it
    // needs) waits for the first message actually sent (ensureSession()).
    input.disabled = false;
    sendBtn.disabled = false;
    setStatus("ready");
  }

  async function ensureSession() {
    if (sessionId) return;
    setStatus("starting session…");
    await request("initialize", {
      protocolVersion: 1,
      clientCapabilities: { fs: { readTextFile: false, writeTextFile: false } },
    });
    const res = await request("session/new", { cwd: workspace, mcpServers: [] });
    sessionId = res.sessionId;
  }

  function onClose(ev) {
    input.disabled = true;
    sendBtn.disabled = true;
    sessionId = null;
    // The server closes with a reason when the agent itself died
    // ("agent exited (code N)"); surface that instead of a bare "disconnected".
    for (const p of pending.values()) p.reject(new Error(ev.reason || "disconnected"));
    pending.clear();
    if (ev.code === 1008 || ev.code === 1013) {
      setStatus(ev.reason || "connection rejected");
      return; // auth / second-tab rejection: retry would spin forever
    }
    // Server gone (Ctrl+C) or not yet back: keep trying so a fresh
    // `okf serve` reclaims this window instead of spawning another.
    setStatus("disconnected — waiting for `okf serve`…");
    setTimeout(connect, 2500);
  }

  function onMessage(ev) {
    const msg = JSON.parse(ev.data);
    if (msg.id !== undefined && msg.method === undefined) {
      const p = pending.get(msg.id);
      if (!p) return;
      pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error.message || "agent error"));
      else p.resolve(msg.result);
      return;
    }
    if (msg.method === "session/update") {
      onUpdate((msg.params && msg.params.update) || {});
    } else if (msg.method === "session/request_permission") {
      onPermission(msg);
    } else if (msg.id !== undefined) {
      jsonSend({
        jsonrpc: "2.0",
        id: msg.id,
        error: { code: -32601, message: "not supported by the OKF viewer" },
      });
    }
  }

  function connect() {
    setStatus("connecting…");
    ws = new WebSocket(`ws://127.0.0.1:${chatFrag[1]}/?token=${chatFrag[2]}`);
    ws.addEventListener("open", onOpen);
    ws.addEventListener("close", onClose);
    ws.addEventListener("message", onMessage);
  }
  connect();

  function onUpdate(u) {
    if (u.sessionUpdate === "agent_message_chunk" && u.content && u.content.type === "text") {
      if (!agentEl) agentEl = addMsg("agent");
      agentBuf += u.content.text;
      agentEl.innerHTML = marked.parse(agentBuf, { breaks: false, gfm: true });
      messages.scrollTop = messages.scrollHeight;
    } else if (u.sessionUpdate === "tool_call" || u.sessionUpdate === "tool_call_update") {
      let el = toolEls.get(u.toolCallId);
      if (!el) {
        el = addMsg("tool");
        toolEls.set(u.toolCallId, el);
      }
      const title = u.title || el.dataset.title || "tool";
      el.dataset.title = title;
      el.textContent = `⚙ ${title}${u.status ? ` — ${u.status}` : ""}`;
      // A tool call ends the current message bubble; the next chunk starts fresh.
      agentEl = null;
      agentBuf = "";
    }
  }

  // Write gate, human side: the bridge only forwards what a human must decide.
  function onPermission(msg) {
    const card = addMsg("perm");
    const title =
      (msg.params.toolCall && msg.params.toolCall.title) || "The agent asks for permission";
    const label = document.createElement("div");
    label.textContent = title;
    card.appendChild(label);
    for (const opt of msg.params.options || []) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = opt.name || opt.optionId;
      btn.addEventListener("click", () => {
        jsonSend({
          jsonrpc: "2.0",
          id: msg.id,
          result: { outcome: { outcome: "selected", optionId: opt.optionId } },
        });
        card.textContent = `${title} — ${opt.name || opt.optionId}`;
      });
      card.appendChild(btn);
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text || sendBtn.disabled) return;
    // Skill invoke: the slash command must lead the prompt, so the selection
    // context trails the message instead of preceding it.
    let promptText = `/${document.getElementById("chat-skill").value} ${text}`;
    if (context) {
      promptText +=
        `\n\nContext: the user has concept ${context.id} ("${context.label}") ` +
        `selected in the OKF viewer.`;
    }
    addMsg("user").textContent = text;
    input.value = "";
    agentEl = null;
    agentBuf = "";
    sendBtn.disabled = true;
    cancelBtn.hidden = false;
    try {
      await ensureSession(); // first message only: spawns the agent (ADR-0008)
      setStatus("thinking…");
      await request("session/prompt", {
        sessionId,
        prompt: [{ type: "text", text: promptText }],
      });
    } catch (err) {
      addMsg("error").textContent = err.message;
    }
    agentEl = null;
    agentBuf = "";
    sendBtn.disabled = false;
    cancelBtn.hidden = true;
    setStatus("ready");
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  cancelBtn.addEventListener("click", () => {
    if (sessionId) jsonSend({ jsonrpc: "2.0", method: "session/cancel", params: { sessionId } });
  });
})();

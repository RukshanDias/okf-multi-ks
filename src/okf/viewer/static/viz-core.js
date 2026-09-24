// Shared state, filters, and the View-mode switch. Renderers implement the
// ADR-0007 contract: { mount, unmount, focusNode(id|null), applyDim(Set), reset }.
const bundle = window.BUNDLE;
const bundleName = window.BUNDLE_NAME;
document.title = `${bundleName} — OKF Viewer`;
document.getElementById("bundle-name").textContent = bundleName;

// Populate KS + type filters (single viz.html; filter others out client-side)
const ksSelect = document.getElementById("filter-ks");
for (const ks of bundle.knowledgeSystems || []) {
  const opt = document.createElement("option");
  opt.value = ks;
  opt.textContent = ks;
  ksSelect.appendChild(opt);
}
const typeSelect = document.getElementById("filter-type");
for (const t of bundle.types) {
  const opt = document.createElement("option");
  opt.value = t;
  opt.textContent = t;
  typeSelect.appendChild(opt);
}

// Build reverse-link index for backlinks
const backlinks = {};
for (const edge of bundle.edges) {
  const { source, target } = edge.data;
  (backlinks[target] ||= []).push(source);
}

// Look up node label/type by id
const nodeIndex = {};
for (const n of bundle.nodes) nodeIndex[n.data.id] = n.data;

// View mode: renderers are lazy-created, then kept alive and toggled so
// switching never loses camera/layout state (ADR-0007).
const renderers = {};
let renderer = null;
let selectedId = null;

function setViewMode(mode) {
  if (mode === "3d" && !renderers["3d"]) {
    const r = create3dRenderer();
    if (r) {
      renderers["3d"] = r;
    } else {
      // yagni: alert over a styled notice; restyle if it ever annoys anyone
      alert("3D view unavailable (WebGL or the 3D library failed to load). Staying in 2D.");
      document.getElementById("view-mode").value = "2d";
      mode = "2d";
    }
  }
  if (mode === "2d" && !renderers["2d"]) renderers["2d"] = create2dRenderer();
  const next = renderers[mode];
  if (renderer !== next) {
    if (renderer) renderer.unmount();
    renderer = next;
    renderer.mount();
  }
  // The dark theme is a property of the 3D View mode, not a separate setting.
  if (mode === "3d") document.documentElement.setAttribute("data-theme", "dark");
  else document.documentElement.removeAttribute("data-theme");
  document.getElementById("layout").hidden = mode !== "2d"; // layouts are 2D-only
  try {
    localStorage.setItem("okf-view-mode", mode);
  } catch {}
  renderer.applyDim(computeDim());
  if (selectedId) renderer.focusNode(selectedId);
}

function computeDim() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const ks = document.getElementById("filter-ks").value;
  const t = document.getElementById("filter-type").value;
  const dim = new Set();
  for (const n of bundle.nodes) {
    const d = n.data;
    const hay =
      (d.label || "").toLowerCase() +
      " " +
      d.id.toLowerCase() +
      " " +
      (d.tags || []).join(" ").toLowerCase();
    const missSearch = q && !hay.includes(q);
    const missKs = ks && d.ks !== ks;
    const missType = t && d.type !== t;
    if (missSearch || missKs || missType) dim.add(d.id);
  }
  return dim;
}

function applyFilters() {
  if (renderer) renderer.applyDim(computeDim());
}

document.getElementById("search").addEventListener("input", applyFilters);
document.getElementById("filter-ks").addEventListener("change", applyFilters);
document.getElementById("filter-type").addEventListener("change", applyFilters);

document.getElementById("reset").addEventListener("click", () => {
  renderer.reset();
  clearSelection();
});

function clearSelection() {
  selectedId = null;
  renderer.focusNode(null);
  document.getElementById("detail-empty").hidden = false;
  document.getElementById("detail-content").hidden = true;
}

let chatSelect = null; // set by initChat when OKF Server is present

// #chat=port:token — the one signal that OKF Server (not a static file://
// open) is serving this page (ADR-0008). Shared by initChat (viz-chat.js,
// concatenated after this file) and the live Actions buttons below.
const chatFrag = /[#&]chat=(\d+):([A-Za-z0-9_~.-]+)/.exec(location.hash);

// Actions: copy-only commands (ADR-0003, amended: paths injected at generation)
function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  ta.remove();
  return Promise.resolve();
}

const actionsBtn = document.getElementById("actions");
const actionsDialog = document.getElementById("actions-dialog");
const actionsCmd = document.getElementById("actions-cmd");
// Both injected at generation time: href-parsing can't distinguish a flat
// Notebook home (~/.okf/viz.html) from a nested overlay (<ws>/.okf/viz.html).
const workspace = __OKF_WORKSPACE__;
const okfCli = __OKF_CLI__;
if (workspace && actionsBtn && actionsDialog && actionsCmd) {
  const cmd = `& "${okfCli}" --workspace "${workspace}" viz`;
  const chatCmd = `& "${okfCli}" --workspace "${workspace}" serve`;
  actionsBtn.hidden = false;
  actionsBtn.addEventListener("click", () => {
    actionsCmd.textContent = cmd;
    document.getElementById("actions-chat-cmd").textContent = chatCmd;
    actionsDialog.showModal();
  });
  document.getElementById("actions-copy").addEventListener("click", () => {
    copyText(cmd);
  });
  document.getElementById("actions-chat-copy").addEventListener("click", () => {
    copyText(chatCmd);
  });
  for (const btn of actionsDialog.querySelectorAll(".offboard-copy")) {
    btn.addEventListener("click", () => {
      copyText(btn.previousElementSibling.textContent);
    });
  }

  // OKF Server (ADR-0008): action routes are live, token-gated, in-process —
  // no copy/paste. Inert without chatFrag (static file:// viewing).
  if (chatFrag) {
    const token = chatFrag[2];

    const runAction = async (btn, busyLabel, idleLabel, url) => {
      btn.disabled = true;
      btn.textContent = busyLabel;
      try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.ok) {
          location.reload();
          return;
        }
        alert(data.error || "action failed");
      } catch (e) {
        alert(e.message);
      }
      btn.disabled = false;
      btn.textContent = idleLabel;
    };

    const regenBtn = document.getElementById("actions-regenerate-live");
    if (regenBtn) {
      regenBtn.hidden = false;
      regenBtn.addEventListener("click", () =>
        runAction(regenBtn, "Regenerating…", "Regenerate now", `/regenerate?token=${encodeURIComponent(token)}`)
      );
    }

    for (const btn of actionsDialog.querySelectorAll(".offboard-live")) {
      btn.hidden = false;
      const label = btn.dataset.ks;
      btn.addEventListener("click", () => {
        if (!confirm(`Off-board "${label}"? Its Cross-KS associations will be removed. The KS folder stays on disk.`)) {
          return;
        }
        runAction(
          btn,
          "Off-boarding…",
          "Off-board now",
          `/offboard?label=${encodeURIComponent(label)}&token=${encodeURIComponent(token)}`
        );
      });
    }
  }
}

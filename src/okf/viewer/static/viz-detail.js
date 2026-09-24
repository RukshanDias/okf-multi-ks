// Concept detail panel (markdown preview, projected Cross-KS, backlinks).
function showDetail(conceptId) {
  const data = nodeIndex[conceptId];
  if (!data) return;
  if (chatSelect) chatSelect(data);
  selectedId = conceptId;
  renderer.focusNode(conceptId);

  document.getElementById("detail-empty").hidden = true;
  const content = document.getElementById("detail-content");
  content.hidden = false;

  const chip = document.getElementById("detail-type");
  chip.textContent = data.type ? `${data.ks} > ${data.type}` : data.ks;
  chip.style.background = data.color;

  document.getElementById("detail-title").textContent = data.label;
  document.getElementById("detail-id").textContent = conceptId;
  document.getElementById("detail-description").textContent = data.description || "—";

  const resourceEl = document.getElementById("detail-resource");
  resourceEl.innerHTML = "";
  if (data.resource) {
    const a = document.createElement("a");
    a.href = data.resource;
    a.textContent = data.resource;
    a.target = "_blank";
    a.rel = "noopener";
    a.className = "external";
    resourceEl.appendChild(a);
  } else {
    resourceEl.textContent = "—";
  }

  const tagsEl = document.getElementById("detail-tags");
  tagsEl.innerHTML = "";
  if (data.tags && data.tags.length) {
    for (const t of data.tags) {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = t;
      tagsEl.appendChild(span);
    }
  } else {
    tagsEl.textContent = "—";
  }

  const body = bundle.bodies[conceptId] || "";
  const html = marked.parse(body, { breaks: false, gfm: true });
  const bodyEl = document.getElementById("detail-body");
  bodyEl.innerHTML = html;
  rewriteImages(bodyEl, conceptId);
  rewriteInternalLinks(bodyEl);

  const proj = (bundle.projected && bundle.projected[conceptId]) || [];
  const projSection = document.getElementById("detail-projected");
  const projList = document.getElementById("projected-list");
  projList.innerHTML = "";
  if (proj.length) {
    projSection.hidden = false;
    for (const item of proj) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.textContent = item.label || item.id;
      a.addEventListener("click", () => showDetail(item.id));
      li.appendChild(a);
      const muted = document.createElement("span");
      muted.className = "muted";
      muted.textContent = ` (${item.id})`;
      li.appendChild(muted);
      projList.appendChild(li);
    }
  } else {
    projSection.hidden = true;
  }

  const bl = backlinks[conceptId] || [];
  const blSection = document.getElementById("detail-backlinks");
  const blList = document.getElementById("backlinks-list");
  blList.innerHTML = "";
  if (bl.length) {
    blSection.hidden = false;
    for (const src of bl) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.textContent = nodeIndex[src]?.label || src;
      a.dataset.target = src;
      a.addEventListener("click", () => showDetail(src));
      li.appendChild(a);
      const muted = document.createElement("span");
      muted.className = "muted";
      muted.textContent = ` (${src})`;
      li.appendChild(muted);
      blList.appendChild(li);
    }
  } else {
    blSection.hidden = true;
  }
}

function rewriteImages(root, conceptId) {
  const base = bundle.sourceDirs && bundle.sourceDirs[conceptId];
  if (!base) return;
  root.querySelectorAll("img[src]").forEach((img) => {
    const src = img.getAttribute("src");
    if (!src || /^(https?:)?\/\//i.test(src)) return;
    img.setAttribute("src", new URL(src, base).href);
  });
}

function rewriteInternalLinks(root) {
  root.querySelectorAll("a[href]").forEach((a) => {
    const href = a.getAttribute("href");
    if (!href) return;
    if (href.startsWith("/") && href.endsWith(".md")) {
      const target = href.slice(1, -3);
      if (nodeIndex[target]) {
        a.className = "internal";
        a.setAttribute("href", "javascript:void(0)");
        a.addEventListener("click", (e) => {
          e.preventDefault();
          showDetail(target);
        });
        return;
      }
    }
    a.className = "external";
    a.setAttribute("target", "_blank");
    a.setAttribute("rel", "noopener");
  });
}

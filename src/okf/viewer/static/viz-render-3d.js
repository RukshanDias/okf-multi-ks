// 3D View mode: 3d-force-graph renderer (ADR-0007 contract). The pinned
// three.min.js matches the three bundled inside 3d-force-graph (r151), so
// THREE objects built here render safely inside the graph's scene.
function create3dRenderer() {
  if (typeof ForceGraph3D === "undefined" || typeof THREE === "undefined") {
    return null; // CDN script missing: caller falls back to 2D
  }
  const container = document.getElementById("graph-3d");

  const nodes = bundle.nodes.map((n) => ({ ...n.data }));
  const links = bundle.edges.map((e) => ({
    source: e.data.source,
    target: e.data.target,
    kind: e.data.kind,
  }));

  // One halo material per KS color: additive radial gradient = the glow.
  // The bright variant highlights the selected node.
  const haloMaterials = {};
  function haloMaterial(color, bright = false) {
    const key = color + (bright ? "!" : "");
    if (!haloMaterials[key]) {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = 128;
      const ctx = canvas.getContext("2d");
      const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
      g.addColorStop(0, color + (bright ? "ff" : "cc")); // #rrggbb + alpha
      g.addColorStop(0.4, color + (bright ? "88" : "44"));
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, 128, 128);
      haloMaterials[key] = new THREE.SpriteMaterial({
        map: new THREE.CanvasTexture(canvas),
        blending: THREE.AdditiveBlending,
        transparent: true,
        depthWrite: false,
      });
    }
    return haloMaterials[key];
  }

  // Pinned label for the selected node (hover labels are the built-in tooltip).
  function textSprite(text, fontPx = 28, color = "#e2e8f0") {
    const pad = 8;
    const canvas = document.createElement("canvas");
    let ctx = canvas.getContext("2d");
    ctx.font = `${fontPx}px sans-serif`;
    canvas.width = Math.ceil(ctx.measureText(text).width) + pad * 2;
    canvas.height = fontPx + pad * 2;
    ctx = canvas.getContext("2d"); // resizing the canvas reset its state
    ctx.font = `${fontPx}px sans-serif`;
    ctx.fillStyle = color;
    ctx.textBaseline = "middle";
    ctx.fillText(text, pad, canvas.height / 2);
    const sprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: new THREE.CanvasTexture(canvas),
        transparent: true,
        depthWrite: false,
      })
    );
    sprite.scale.set(canvas.width / 4, canvas.height / 4, 1);
    return sprite;
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  let graph;
  try {
    // orbit controls: the default trackball has no autoRotate for the ambient spin
    graph = ForceGraph3D({ controlType: "orbit" })(container)
      .backgroundColor("#050510")
      .showNavInfo(false)
      .nodeLabel((n) => escapeHtml(n.label))
      .nodeThreeObject((n) => {
        const group = new THREE.Group();
        const r = n.size / 8;
        group.add(
          new THREE.Mesh(
            new THREE.SphereGeometry(r, 16, 16),
            new THREE.MeshBasicMaterial({ color: n.color })
          )
        );
        const selected = n.id === selectedId;
        const halo = new THREE.Sprite(haloMaterial(n.color, selected));
        const haloScale = r * (selected ? 9 : 6);
        halo.scale.set(haloScale, haloScale, 1);
        group.add(halo);
        if (selected) {
          const label = textSprite(n.label);
          label.position.set(0, r * 2.5, 0);
          group.add(label);
        }
        return group;
      })
      // Intra-KS lighter/more visible; Cross-KS fainter (grill 2026-09-09).
      .linkColor((l) => (l.kind === "association" ? "#3d4a5c" : "#94a3b8"))
      .linkWidth(0.65) // >0 renders cylinders: gives edges visible weight
      .linkOpacity(0.5)
      .onNodeClick((n) => showDetail(n.id))
      .onBackgroundClick(() => clearSelection())
      .graphData({ nodes, links });
  } catch (e) {
    return null; // WebGL unavailable: caller falls back to 2D
  }

  // Same-KS cohesion + gentle pull toward origin so KS clusters stay
  // together and sit closer to each other. Tuned by eye; adjust the pulls.
  const CLUSTER_PULL = 0.08;
  const COMPACT_PULL = 0.015;
  graph.d3Force("cluster", (() => {
    let nodes = [];
    const force = (alpha) => {
      const centroids = {};
      for (const n of nodes) {
        const c = (centroids[n.ks] ||= { x: 0, y: 0, z: 0, count: 0 });
        c.x += n.x;
        c.y += n.y;
        c.z += n.z;
        c.count++;
      }
      for (const c of Object.values(centroids)) {
        c.x /= c.count;
        c.y /= c.count;
        c.z /= c.count;
      }
      for (const n of nodes) {
        const c = centroids[n.ks];
        n.vx += ((c.x - n.x) * CLUSTER_PULL - n.x * COMPACT_PULL) * alpha;
        n.vy += ((c.y - n.y) * CLUSTER_PULL - n.y * COMPACT_PULL) * alpha;
        n.vz += ((c.z - n.z) * CLUSTER_PULL - n.z * COMPACT_PULL) * alpha;
      }
    };
    force.initialize = (ns) => {
      nodes = ns;
    };
    return force;
  })());

  // KS name labels track their cluster's centroid.
  const ksSprites = {};
  for (const ks of bundle.knowledgeSystems || []) {
    const label = ks.charAt(0).toUpperCase() + ks.slice(1);
    const sprite = textSprite(label, 48, (bundle.ksColors || {})[ks] || "#e2e8f0");
    graph.scene().add(sprite);
    ksSprites[ks] = sprite;
  }
  graph.onEngineTick(() => {
    const centroids = {};
    for (const n of graph.graphData().nodes) {
      const c = (centroids[n.ks] ||= { x: 0, y: 0, z: 0, count: 0 });
      c.x += n.x || 0;
      c.y += n.y || 0;
      c.z += n.z || 0;
      c.count++;
    }
    for (const [ks, sprite] of Object.entries(ksSprites)) {
      const c = centroids[ks];
      if (c) sprite.position.set(c.x / c.count, c.y / c.count + 60, c.z / c.count);
    }
  });

  // Default view: once the layout settles, fit exactly like Reset view does.
  let fitted = false;
  graph.onEngineStop(() => {
    if (!fitted) {
      fitted = true;
      graph.zoomToFit(600);
    }
  });

  // Ambient spin: pause while the user interacts, resume after 10s idle.
  const controls = graph.controls();
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.5;
  let resumeTimer = null;
  controls.addEventListener("start", () => {
    controls.autoRotate = false;
    clearTimeout(resumeTimer);
  });
  controls.addEventListener("end", () => {
    clearTimeout(resumeTimer);
    resumeTimer = setTimeout(() => {
      controls.autoRotate = true;
    }, 10000);
  });

  const idOf = (end) => (typeof end === "object" ? end.id : end);

  return {
    mount() {
      container.hidden = false;
      graph.width(container.clientWidth);
      graph.height(container.clientHeight);
    },
    unmount() {
      container.hidden = true;
    },
    resize() {
      graph.width(container.clientWidth);
      graph.height(container.clientHeight);
    },
    focusNode(id) {
      graph.refresh(); // re-evaluates nodeThreeObject so the pinned label follows selectedId
      if (!id) return;
      const node = graph.graphData().nodes.find((n) => n.id === id);
      if (!node || (!node.x && !node.y && !node.z)) return; // layout not settled yet
      const dist = Math.hypot(node.x, node.y, node.z) || 1;
      const ratio = 1 + 140 / dist;
      graph.cameraPosition(
        { x: node.x * ratio, y: node.y * ratio, z: node.z * ratio },
        node,
        800
      );
    },
    applyDim(dimSet) {
      // yagni: filtered-out nodes are hidden, not dimmed like 2D; switch to
      // per-node material opacity if hiding ever confuses
      graph
        .nodeVisibility((n) => !dimSet.has(n.id))
        .linkVisibility(
          (l) => !dimSet.has(idOf(l.source)) && !dimSet.has(idOf(l.target))
        );
    },
    reset() {
      graph.zoomToFit(400);
    },
  };
}

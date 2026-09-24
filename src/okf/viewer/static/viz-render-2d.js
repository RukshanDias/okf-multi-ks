// 2D View mode: cytoscape renderer (ADR-0007 contract).
function create2dRenderer() {
  const container = document.getElementById("graph-2d");
  const cy = cytoscape({
    container,
    elements: [...bundle.nodes, ...bundle.edges],
    style: [
      {
        selector: "node",
        style: {
          "background-color": "data(color)",
          "label": "data(label)",
          "color": "#0f172a",
          "font-size": 11,
          "text-valign": "bottom",
          "text-margin-y": 4,
          "text-wrap": "wrap",
          "text-max-width": 120,
          "width": "data(size)",
          "height": "data(size)",
          "border-width": 1,
          "border-color": "#0f172a",
        },
      },
      {
        selector: "node:selected",
        style: {
          "border-width": 3,
          "border-color": "#f59e0b",
        },
      },
      {
        selector: "edge",
        style: {
          "width": 1.5,
          "line-color": "#cbd5e1",
          "target-arrow-color": "#cbd5e1",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "arrow-scale": 0.9,
          "line-style": "solid",
        },
      },
      {
        selector: "edge.association",
        style: {
          "line-style": "dashed",
          "line-color": "#94a3b8",
          "target-arrow-shape": "none",
          "source-arrow-shape": "none",
          "width": 1.25,
        },
      },
      {
        selector: "edge:selected",
        style: {
          "line-color": "#f59e0b",
          "target-arrow-color": "#f59e0b",
          "width": 2.5,
        },
      },
      {
        selector: ".dim",
        style: { "opacity": 0.15 },
      },
    ],
    wheelSensitivity: 0.2,
  });

  cy.on("tap", "node", (evt) => showDetail(evt.target.id()));
  cy.on("tap", (evt) => {
    if (evt.target === cy) clearSelection();
  });

  document.getElementById("layout").addEventListener("change", (e) => {
    cy.layout({ name: e.target.value, animate: false, padding: 30 }).run();
  });

  // Layout runs on first mount, not at creation: the container may still be
  // hidden here (boot straight into 3D) and cose needs real dimensions.
  let laidOut = false;
  return {
    mount() {
      container.hidden = false;
      cy.resize();
      if (!laidOut) {
        cy.layout({ name: "cose", animate: false, padding: 30 }).run();
        laidOut = true;
      }
    },
    unmount() {
      container.hidden = true;
    },
    resize() {
      cy.resize();
    },
    focusNode(id) {
      cy.elements().unselect();
      if (!id) return;
      const node = cy.getElementById(id);
      if (node.nonempty()) {
        node.select();
        cy.animate(
          { center: { eles: node }, zoom: Math.max(cy.zoom(), 1.0) },
          { duration: 200 }
        );
      }
    },
    applyDim(dimSet) {
      cy.nodes().forEach((n) => n.toggleClass("dim", dimSet.has(n.id())));
      cy.edges().forEach((edge) => {
        edge.toggleClass(
          "dim",
          edge.source().hasClass("dim") || edge.target().hasClass("dim")
        );
      });
    },
    reset() {
      cy.fit(null, 30);
    },
  };
}

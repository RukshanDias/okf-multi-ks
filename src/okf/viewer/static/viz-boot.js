// Boot: restore the last-used View mode. Nothing is selected until the
// user clicks a node; #detail-empty shows the hint until then.
const viewSelect = document.getElementById("view-mode");
let storedMode = null;
try {
  storedMode = localStorage.getItem("okf-view-mode");
} catch {}
viewSelect.value = storedMode === "3d" ? "3d" : "2d";
viewSelect.addEventListener("change", () => setViewMode(viewSelect.value));
setViewMode(viewSelect.value);

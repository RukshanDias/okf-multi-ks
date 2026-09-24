# OKF Multi-Knowledge Notebook

Workspace composition of independent OKF Knowledge Systems with associative transfer learning across them. Glossary only — no implementation details.

## Language

**Knowledge System (KS)**:
An independent OKF bundle root (its own `index.md` and concept markdown). Every configured root is a KS — same rules, same tooling. May use git (any remote visibility) so the same person can keep it in sync across machines, or so others can clone/contribute; git is storage/sync, not a separate product class.
_Avoid_: Brain, private KS, public KS, Local KS, Shared KS (as policy types), vault, corpus, wiki

**Intra-KS edge**:
A relationship authored as a normal markdown link inside one Knowledge System; it ships with that KS when the KS repo is pushed/shared.
_Avoid_: Internal link (ambiguous), local link

**Cross-KS association**:
A many-to-many mapping between concepts in different Knowledge Systems used for associative / transfer learning in the learner’s notebook.
_Avoid_: Cross-brain link, bridge link in source markdown

**Workspace overlay**:
The notebook-local, gitignored layer beside workspace config that holds Cross-KS associations and derived search/graph indexes. Never part of any KS repo — so pushing a KS never ships notebook maps.
_Avoid_: Central graph, merged knowledge base, shared brain

**Association store**:
The durable, gitignored part of the Workspace overlay that records Cross-KS associations so they survive re-index (`.okf/associations.json`). Not concept markdown; never published with a KS.
_Avoid_: Index (the derived query graph), central graph

**Derived index**:
The disposable search/graph built by `okf index` from each KS’s markdown plus the Association store (`.okf/index.json`); safe to delete and rebuild.
_Avoid_: Source of truth, published graph

**Id overlay file**:
Gitignored map at `.okf/id-overlay.json` (`ks:rel_path` → UUID) for concepts missing frontmatter `id`.
_Avoid_: Rewriting cloned KS markdown for local-only ids

**Unified relationship view**:
What readers (agents and the HTML visualizer) use when traversing knowledge: Intra-KS edges from markdown plus Cross-KS associations from the Association store, treated as one graph with two edge kinds.
_Avoid_: Merged markdown, rewritten concept file

**Projected Cross-KS section**:
A view-only “Cross-KS relationships” block shown in the visualizer’s concept preview; assembled from the Association store at render time and never written into the source `.md` file.
_Avoid_: See also (that is authored Intra-KS markdown), frontmatter relations in a KS repo

**Seed pack**:
A bounded set of candidate Cross-KS associations from Catalog-first rule-based propose at onboard (hub/`index.md`-first, capped count; field `similarity_score`). An agent LLM shortlists only semantically valid peers; a human then approves indexes (or discards). Zero accepted associations is better than wrong ones. Not a per-file review of the cloned KS.
_Avoid_: Full auto-map, accept-all on unreviewed pack, per-document approval

**Separation rule**:
Concept markdown may contain only Intra-KS edges. All Cross-KS associations live exclusively in the Association store (and appear to readers only via the Unified relationship view / Projected Cross-KS section). Never write Cross-KS links into source `.md` files. **Same rule for every KS.**
_Avoid_: Cross-KS See also, path links across KS roots in markdown, per-KS directional allow-lists

**Onboard mapping scope**:
A Seed pack for a newly added Knowledge System considers associations to every other currently configured Knowledge System, under a global candidate cap (not a per-target-KS cap that multiplies review size).
_Avoid_: Home-KS-only mapping (unless explicitly overridden for a topic-onboard)

**Catalog-first onboard**:
Default Seed-pack generation reads `index.md` trees and concept frontmatter (title, description, tags, type) and ranks pairs with a rule-based `similarity_score`. An agent then judges valid Cross-KS peers from that catalog (body peek only on ties/uncertainty), shortlists for human approve, and never pads weak links. Full-corpus body reads are out of scope for onboard.
_Avoid_: Read-all-markdown onboard, embedding-first onboard (unless added later as an optional ranker), treating similarity_score as proof of a peer

**Offboard**:
Removing one Knowledge System from the Multi-KS notebook: deregister it from workspace config and delete its notebook-local state (its Cross-KS associations, Id overlay entries, and any Seed pack referencing it). The KS folder itself stays in the KS library — offboard never deletes knowledge. Inverse of onboard for notebook state only; one KS per offboard.
_Avoid_: Uninstall, delete KS (the clone survives), remove from disk, purge

**Publish / sync**:
Pushing a KS git remote (personal sync across machines, or collaborative remote) ships that KS’s markdown only. Does not include the Association store or Derived index. Not a “may I push?” product gate.
_Avoid_: Separate private vs public link policies, “Local KS cannot use git”

**KS check**:
Validation for any Knowledge System: required frontmatter present, concept bodies contain no Cross-KS links (Separation rule). **One policy shape for every KS** — no private/public policy fork.
_Avoid_: Dual Brain directional markdown allow-lists (work→personal in source), publishable vs non-publishable link rules

**Required concept frontmatter**:
Every concept file must declare `type`, `title`, `description`, and a stable `id` used by the Association store and KS check. `tags` are optional but preferred for Catalog-first onboard.
_Avoid_: Path-only identity as the sole handle (paths rename), missing description

**Concept id**:
A UUID (or ULID) in concept frontmatter, minted once at create time, that uniquely identifies the concept within its Knowledge System for Association-store endpoints. Display and navigation still use `title` and path.
_Avoid_: Path-as-id, slug-as-sole-id

**Id overlay**:
A gitignored workspace map of `KS path → Concept id` for concepts that lack frontmatter `id` (typical when cloning a legacy KS). Associations resolve through it until the KS mints real ids; then overlay entries are migrated away. Does not rewrite foreign/cloned KS markdown in the notebook.
_Avoid_: Local-only frontmatter edits pushed back to a foreign remote, path-as-permanent-id

**Association record**:
An undirected Cross-KS pair in the Association store: two endpoints (`ks` + Concept id), optional note/confidence/source (`seed` | `ask` | `manual`), and optional `kind` later. Bidirectional for viz and agent hops in v1.
_Avoid_: Required relation taxonomy in v1, Cross-KS links in markdown

**Multi-KS notebook**:
The workspace composition of N Knowledge Systems plus a Workspace overlay (Association store, Id overlay, Derived index). Former Dual Brain roots (`personal`, `work`) are just labeled KSs — not special policy types. Evolved in place rather than a separate product.
_Avoid_: Dual Brain as a forever-separate link-policy product, merged monolithic bundle, brain terminology in new docs

**OKF system**:
The cloneable code repository: CLI, reference_agent pipeline, skills, visualizer, spec. Contains no user knowledge — no user KSs, no workspace config, no overlay. Users update it with `git pull` without ever touching their notebook.
_Avoid_: The workspace, the notebook repo, "OKF" when the format itself is meant

**KS library**:
The user-configured folder that holds cloned Knowledge System roots side by side, and nothing else — no workspace config, no overlay, no notebook state. The Multi-KS notebook references it via a setting. "Notebooks folder" in casual speech usually means this.
_Avoid_: Notebooks folder (KSs are what get cloned, not notebooks), bundles dir inside the OKF system repo

**Showcase bundle**:
An example Knowledge System shipped inside the OKF system repo (`examples/football`) to demonstrate the format and give first-install users something to browse. A fresh install copies it into the KS library and registers it as the first KS; from then on it is an ordinary KS the user may edit or offboard.
_Avoid_: Demo notebook, sample KS in the KS library, treating showcase content as user-editable

**Notebook chat**:
An agent conversation scoped to the Multi-KS notebook: the agent works from the workspace root and may read workspace config, the configured KS roots, and the Association store. Chat is about the learner's knowledge — not about the OKF system's source code.
_Avoid_: Codebase chat (the OKF system repo is not the chat scope), chat with viz.html (the viewer is the surface, not the scope)

**OKF Server**:
The persistent loopback (127.0.0.1) process that is the default local runtime for a Multi-KS notebook: it serves the viewer over HTTP, relays Notebook chat to a coding agent ACP subprocess, and executes notebook actions (regenerate, off-board, and other future viewer-triggered actions) in-process when clicked. Started once per notebook — not spun up ad hoc per action or per chat session; a still-open viewer window reconnects to it. Holds a per-session token; never notebook state, never part of any KS. Reads fresh from KS markdown + the Association store on every request — no in-memory merged graph held as authoritative between requests.
_Avoid_: Chat bridge (superseded name — scope outgrew chat-only), Chat server (undersells scope), viz backend as a source of truth (it still reads from disk per request, never becomes the authoritative store)

**View mode**:
A way of rendering the same Unified relationship view in the visualizer: 2D (the flat interactive graph, the default) or 3D (a dark, ambient space view of the identical nodes and edge kinds). Switching View mode never changes what knowledge is shown — selection, filters, concept preview, and Notebook chat are mode-independent. Layout choices exist only within the 2D View mode; the dark theme is a property of the 3D View mode, not a separate setting.
_Avoid_: Visualisation type, render mode (implementation term), layout (that is a 2D-only sub-choice), dark mode as an independent feature

**Notebook home**:
The per-user directory that holds the Multi-KS notebook itself: workspace config (okf.yaml, including the KS library setting) and the Workspace overlay. Lives with the user (`~/.okf/`), not inside the OKF system repo and not inside the KS library — so recloning the system or a KS never destroys the Association store.
_Avoid_: Workspace root inside the OKF system repo, config-in-KS-library

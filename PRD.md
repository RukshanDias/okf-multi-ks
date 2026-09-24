# PRD: OKF Multi-KS Notebook

Glossary terms live in [`CONTEXT.md`](CONTEXT.md).

## Problem Statement

I want to learn and query across multiple independent OKF Knowledge Systems the way humans transfer knowledge: connect a new system to what I already know (associative / transfer learning), without permanently entangling those systems.

Any KS (golang textbook, personal learnings, company notes) is the same kind of thing: an OKF bundle that may live in git so I can sync it across machines or collaborate. Each KS must ship with **internal edges only**—no dependence on other KSs or on my notebook’s Cross-KS maps. The notebook’s AI and HTML graph must still see Cross-KS associations while I work.

Today’s Dual Brain overlay indexes N roots (called “brains”) but still allows Cross-KS *markdown* links (work→personal) and splits policy by publishable vs not. That fights KS independence and blocks cloning foreign textbooks without rewriting foundations.

## Solution

Evolve Dual Brain **in place** into a **Multi-KS notebook**:

- Each configured root is a **Knowledge System** (normal OKF bundle). Drop “brain” as the product term.
- **One policy for every KS** — no private/public or Local/Shared policy fork. Git remotes are optional sync/collab, not a separate KS class.
- **Separation rule:** markdown = Intra-KS only; Cross-KS = Association store only.
- Workspace overlay (gitignored): Association store + Id overlay + Derived index — never part of any KS push.
- Onboard a new KS with **Catalog-first** discovery and a bounded **Seed pack** (approve once; map against all configured KSs under a global cap).
- Agents and visualizer use the **Unified relationship view** (solid Intra-KS, dotted Cross-KS; projected Cross-KS section in HTML preview only).
- **KS check:** required frontmatter + no Cross-KS links in bodies (same for every KS).
- **Publish/sync** = git remote for a KS. Association store never ships with a KS.

## User Stories

### Knowledge Systems and sync

1. As a knowledge worker, I want each KS to be an independent OKF bundle, so existing single-bundle tooling still works.
2. As a knowledge worker, I want any KS (including personal learnings) to be git-versioned and syncable across machines, without a special “private KS” type.
3. As a knowledge worker, I want foreign/collaborative KSs I clone to stay Separation-clean so remotes are not centrally dependent on my notebook.
4. As a knowledge worker, I want every KS under the same Separation and KS-check rules — no private vs public link-policy split.
5. As a knowledge worker, I want removing a KS to drop its Cross-KS associations and regenerate the Derived index without rewriting other KSs’ markdown.
6. As a knowledge worker, I want former Dual Brain `personal`/`work` paths to be ordinary labeled KSs, not special roles.

### Separation and associations

7. As a knowledge worker, I want Cross-KS maps only in the Association store, never in concept `.md` files.
8. As a knowledge worker, I want approved associations to survive `okf index` rebuilds.
9. As a knowledge worker, I want associations to be undirected in v1 (optional `kind` later), with optional note/confidence/source.
10. As a knowledge worker, I want to associate any configured KS with any other in the notebook (many-to-many via the store).

### Onboard / transfer learning

11. As a knowledge worker, I want to clone/add a KS and get a bounded Seed pack of candidate Cross-KS associations against all other configured KSs.
12. As a knowledge worker, I want Seed pack review to be one short list (not per-file approval of 100 docs).
13. As a knowledge worker, I want Catalog-first onboard: `index.md` + frontmatter ranking; body reads only on low confidence/ties.
14. As a knowledge worker, I want to deepen maps later via ask/topic-onboard without remapping the whole KS.

### Identity and check

15. As a knowledge worker, I want every concept to declare `type`, `title`, `description`, and a stable UUID `id`.
16. As a knowledge worker, I want an Id overlay for legacy clones missing `id`, without rewriting that KS’s markdown in my notebook.
17. As a knowledge worker, I want `okf check` to fail when required frontmatter is missing or bodies contain Cross-KS links.

### Index, agents, visualizer

18. As a knowledge worker, I want `okf index` to build a Derived index from Intra-KS markdown plus the Association store.
19. As a knowledge worker, I want the overlay (store, Id overlay, Derived index) gitignored beside workspace config.
20. As an AI agent, I want to treat markdown links and Association-store edges as one Unified relationship view when answering.
21. As an AI agent, I want search/backlinks to locate concepts, then open and cite real OKF markdown.
22. As a knowledge worker, I want the HTML graph to show Intra-KS edges solid and Association-store edges dotted.
23. As a knowledge worker, I want the HTML concept preview to show a Projected Cross-KS section that is not in the source file.
24. As a knowledge worker, I want keyword search with KS provenance in v1 (no embeddings required).

### Config and migration

25. As a knowledge worker, I want `okf.yaml` to list N labeled KS roots (evolve Dual Brain `brains` → Knowledge Systems).
26. As a developer, I want OKF SPEC to remain single-bundle; Multi-KS is workspace composition only.
27. As a developer, I want CLI for index, check, search, backlinks, and association/onboard flows humans and agents share.
28. As a developer, I want automated tests for config, Separation, Association store merge, Id overlay, Seed pack caps, and KS check.

## Implementation Decisions

### Product boundary

- Multi-KS notebook is **local workspace tooling** on top of OKF bundles.
- OKF SPEC stays single-bundle; no multi-KS format fork in v1.
- Concept markdown remains source of truth for Intra-KS knowledge; Association store is source of truth for Cross-KS maps; Derived index is disposable.

### KS model

- Workspace indexes **N labeled Knowledge Systems**.
- Each KS: label + path (+ optional git remote metadata for convenience). No Shared/Local/private/public role that changes link policy.
- Former Dual Brain example: `personal` and `work` are just two KS entries — same Separation, same check.
- Ideal layout: each KS its own git repo when sync or collaboration is wanted; folder-only also fine.

### Separation and Association store

- Markdown links resolve only within the same KS root.
- Workspace overlay (gitignored):
  - `.okf/associations.json` — durable Cross-KS store
  - `.okf/id-overlay.json` — durable path→UUID for missing frontmatter `id`
  - `.okf/index.json` — disposable Derived index (typed edges `intra` \| `association`)
- Association record (v1): undirected `{a:{ks,concept_id}, b:{ks,concept_id}, source, id, created_at, note?, confidence?}`; `source` ∈ `seed|ingest|ask|manual`; no `kind` yet.
- On KS remove: delete associations touching that KS; rebuild Derived index.
- Id overlay migrates away when the KS gains real frontmatter `id`.

### Onboard

1. Add/clone KS into workspace config.
2. Catalog-first: indexes + frontmatter; rank vs all other KSs; global candidate cap.
3. Emit Seed pack → human approve → Association store.
4. `okf index` merges markdown + store.

### Indexing pipeline

1. Load `okf.yaml` and KS list.
2. Load each available KS as an OKF bundle.
3. Resolve Intra-KS markdown links (same-KS only); warn/fail Cross-KS in markdown per check rules.
4. Load Association store (+ Id overlay resolution).
5. Build Derived index (forward + backlinks for both edge kinds; edge kind flagged).
6. Keyword search index with KS provenance.
7. Emit warnings (dangling Intra-KS links, stale association endpoints, Id overlay orphans).

### KS check

- Required frontmatter: `type`, `title`, `description`, `id` (UUID/ULID).
- Body must not contain Cross-KS links (Separation).
- Same rules for every KS.
- No product “may I push?” prompt; git remains how a KS syncs or collaborates.

### AI and visualizer

- Agents: Unified relationship view; cite real markdown; never invent Cross-KS See also in files.
- Visualizer: workspace-level HTML over all configured KSs; solid vs dotted edges; Projected Cross-KS section in preview only.
- Extend `okf-reader` / `okf-ingest` skills: Knowledge System language, Separation, Association store, Seed pack (retire brain / private-public policy wording).

### Modules to build / extend

1. Workspace config — KS list + paths (evolve Dual Brain config; drop role-based link policy).
2. Bundle loader — per-KS concepts + frontmatter ids.
3. Intra-KS link resolver + Separation enforcement.
4. Association store + Id overlay.
5. Graph builder — merge markdown + associations; typed edge kind in Derived index.
6. Catalog-first Seed pack proposer + approve CLI/flow.
7. Keyword search with KS provenance.
8. CLI — `index`, `check`, `search`, `backlinks`, association/onboard commands.
9. Viewer — multi-KS + dotted associations + projected section.
10. Skill updates — okf-reader, okf-ingest.

### Adoption of existing Dual Brain layout

- Do not require a mass file move.
- Map `bundles/local/personal` and `bundles/local/work` as ordinary KSs in `okf.yaml`.
- Migrate existing Cross-KS markdown links into the Association store.
- Re-index; `okf check` enforces Separation going forward.
- Rename docs/skills from “brain” → Knowledge System as they are touched.

## Testing Decisions

### What makes a good test

- Observable behavior: Separation violations, association merge, remove-KS cleanup, Seed pack cap, Id overlay resolution, KS check frontmatter.
- Tiny fixture KSs (few concepts + links + association files).
- Assert policy is identical across KS labels (no private/public fork).

### Modules with automated tests

- Config (KS list; no role-based Cross-KS markdown allow)
- Separation (Cross-KS markdown rejected for every KS)
- Association store load/merge/cleanup
- Id overlay
- Catalog-first ranking inputs (fixture catalogs; no live LLM required for core tests)
- Derived index edge kinds
- KS check required fields

### Thinner checks

- CLI smoke on fixture workspaces
- Viewer: assert dotted vs solid / projected section present in generated HTML
- Skills: review accuracy; light automation only

### Prior art

- Existing pytest layout (`tests/`, `pythonpath` via `src`)
- Dual Brain modules already started (config, index, check, search, backlinks) — extend rather than replace; strip directional publishable-link policy

## Out of scope for v1

- Embeddings-first onboard (optional later ranker)
- Required association `kind` taxonomy
- Auto-push of KS remotes
- Writing Cross-KS edges into KS markdown
- Central server-side merged graph as source of truth
- Separate private vs public KS product types

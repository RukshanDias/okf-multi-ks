---
name: okf-reader
description: Guidance for AI agents on how to parse, traverse, and query Open Knowledge Format (OKF) bundles — single-bundle or Multi-KS notebooks (`okf.yaml` + Association store). Minimizes token usage via index.md progressive disclosure. Use when reading, navigating, analyzing, or answering questions about OKF knowledge.
license: Apache-2.0
metadata:
  version: "0.12.0"
  author: Rukshan Dias
  tags: "okf, knowledge-catalog, agent-guidance, documentation, prompt-engineering, multi-ks"
---

# OKF Bundle Reader Guidance Skill

Procedural rules for reading and traversing **any** OKF bundle efficiently. Follow original OKF progressive disclosure (`index.md` → open a concept only when it fits). Do **not** dump `.okf/index.json`, `viz.html`, or the whole Association store into context.

OKF is deliberately flexible: layout and `type` values are producer-defined. Key off frontmatter `type`, `index.md`, markdown links, and `resource`.

## Shared config

If this skill and `~/.okf/config.json` are already in context, **use them** — do not re-read `SKILL.md` or the config mid-session.

Read `~/.okf/config.json` for `okf_cli` and `okf_yaml`; resolve KS roots at runtime from `okf_yaml` (`ks_library` + each `ks.<label>.path`; absolute paths win). Use the full `okf_cli` path — never bare `okf`. The CLI defaults to the notebook at `~/.okf` — no `--workspace` needed.

```powershell
& "<okf_cli>" associations "work:observability-key-components.md"
```

Each association line: `ks:path` → title → description → concept UUID (tab-separated). Pick the best neighbor from title + description; open at most **one** neighbor body when transfer learning needs depth.

## Multi-KS notebooks

When the notebook (`okf_yaml`) configures Knowledge Systems, treat it as a **Multi-KS notebook** — several independent Knowledge Systems (each a normal OKF bundle). **OKF progressive disclosure still applies inside each KS.** The workspace overlay (`.okf/`) holds the Association store + Id overlay + optional `viz.html` — never replaces reading real OKF markdown or each KS’s `index.md`.

Discovery order (OKF-first):

1. **Orient with one relevant KS `index.md`** — progressive disclosure before opening bodies. Open a second KS `index.md` only when the question clearly spans domains or the first KS is a dead end.
2. **Decide fit from index text** — open a concept body only when the index description/title fits the question.
3. **Open the fitting concept**; follow **Intra-KS** markdown links only (Separation).
4. **Cross-KS hops (when needed):** run `okf associations <ks:path>` once; use returned path/title/description to pick a neighbor — never load all of `associations.json`.
5. **Cite real OKF markdown** as `ks:path` (e.g. `personal:tracing.md` → `<ks_library>/personal/tracing.md`).
6. **`okf check`** is for **ingest / workspace validation only** — never during answer retrieval.

**Keyword search:** prefer `index.md` first. Grep is fine when technical terms are clear — search under the KS root resolved from `okf_yaml`. The KS library lives outside the current project; if Cursor Grep returns **0 hits**, run shell `rg --no-ignore-vcs` under that KS root once — **never retry Cursor Grep** on the same query.

Never read `.okf/viz.html` or a Derived `index.json` (removed).

## When to Use

Load this skill when reading, parsing, querying, or analyzing OKF knowledge — **one bundle** or a **Multi-KS notebook**.

## Instructions for Agents

### 0. Retrieval budget (mandatory)

- **Single-KS-first:** start with one KS `index.md`; defer other KS catalogs until needed.
- **Body cap:** at most **two** full concept bodies for the primary answer chain (intra-KS + primary KS).
- **Association body:** when Cross-KS transfer learning is required, at most **one** extra full body — the best neighbor chosen from `okf associations` output (title + description). No frontmatter peeks on neighbors.
- **Cross-KS cap:** at most **one** `okf associations` call per answer, only when intra-KS material is insufficient for the question.
- **Stop when answer-ready:** once you can write the main answer arc (§4), **stop all reads**. No tangential concepts, no post-answer peeks. A config appendix (§4) may use **only facts already in opened bodies** — never extra retrieval. Follow-ups can ask for more.
- **No ritual CLI:** do **not** run `okf check`, `okf --help`, or other discovery commands during retrieval. Those belong to ingest (`okf-ingest` skill).

### 1. Index-first discovery
- **Multi-KS notebook** (notebook `okf_yaml` has KSs):
  1. Use `~/.okf/config.json` for `okf_cli` and `okf_yaml`; resolve KS roots from `okf_yaml`.
  2. **Orient via one KS’s `index.md`** (progressive disclosure).
  3. Grep only when index orientation is insufficient and terms are clear.
  4. Open a concept body when index text shows it fits.
  5. For transfer learning, `okf associations <ks:path>` then optionally open **one** neighbor body.
- **Single bundle** (no `okf.yaml`):
  1. Read the bundle-root `index.md` first if present.
  2. Follow its links to map concepts.
  3. If no `index.md`, shallow `*.md` glob without reading bodies yet.
- **Rule (both modes):** NEVER recursively read every markdown file at startup. NEVER feed overlay JSON dumps into context.

### 2. Route directly to a concept (layout is producer-defined)
- Resolve location from `index.md` links — use each link target **verbatim**.
- Open only the one file you need — don't list or read its siblings.

### 3. Links / associations
- **Intra-KS:** markdown links in concept bodies.
- **Cross-KS:** `okf associations <ks:path>` only when needed. Do not invent Cross-KS See also in markdown.
- **Never write** Cross-KS path links into concept bodies (Separation).
- Connectedness shows up in the **answer** (§4 Sources / edges), not by opening every neighbor.

### 4. Answer composition

Default goal: **engineer Q&A** — synthesize for the user’s mental model. Retrieval supports the answer; it must not dominate it. The notebook stays connected via structure and cites, not by dumping every retrieved fact.

#### Main arc (conceptual / “how does / why / fit into”)

Write in this order unless the question clearly demands otherwise:

1. **What is it?** — role of the thing asked about (explain concepts; don’t assume them).
2. **How does it flow?** — pipeline / mechanism.
3. **Why does that matter?** — e.g. centralization, debugging, transfer learning across Components.
4. **One concrete example** — grounded in opened bodies.
5. **Mental model** — short and memorable (a tiny diagram is fine).
6. **Practical next step** — what to look at or do next (not a full runbook unless asked).

#### Distillation (mandatory)

- Answer the **question**, not the **corpus**.
- Prefer synthesis over reproducing doc headings, product catalogs, or deployment inventories.
- Keep implementation identifiers (env vars, stack chart names, UI menu paths, config class names) **out of the main arc** unless the example needs one specific fact.
- Do **not** mention every concept you opened. Unused material may inform silently; it belongs in Sources / edges at most.
- Do **not** narrate a tour of `index.md` or every association neighbor.

#### Config appendix (conditional)

- **Include** a short trailing section **“If you’re configuring…”** only when the question smells like how-to / configure / wire / deploy / setup.
- That appendix may use **only facts already in opened bodies** — no extra reads.
- **Omit** the appendix for conceptual questions (“what / why / how does X fit”). Invite a follow-up instead of stuffing config noise into the main arc.

#### Sources / edges (connected notebook)

After the main arc (and optional config appendix), add one compact block:

- **Primary:** `ks:path` of concepts that grounded the answer.
- **Cross-KS:** neighbor `ks:path` from the associations CLI when used (title from CLI is enough if the body was not opened).

Edges prove the notebook is connected. Bodies stay under the retrieval budget. Never list every file touched for orientation.

### 5. Source-side catalog: `.okf-metadata.yaml`
- When pointed at a **source directory** with `.okf-metadata.yaml`, read that flat `path: description` catalog for an instant index.

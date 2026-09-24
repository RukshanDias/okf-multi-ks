---
name: okf-ingest
description: Adds knowledge to an Open Knowledge Format (OKF) Knowledge System using the reference_agent Python pipeline (write_concept_doc, regenerate_indexes; fetch_url when a URL is given) with Cursor-authored summaries. Use when the user asks to add, ingest, or store knowledge into OKF. In Multi-KS notebooks, target a KS root, keep See also Intra-KS only, and record Cross-KS peers via `okf associate --source ingest`.
license: Apache-2.0
metadata:
  version: "0.8.0"
  author: Rukshan Dias
  tags: "okf, ingestion, knowledge, documents, conversation, web, reference-agent, multi-ks"
---

# OKF Ingestion

Adds knowledge to an OKF Knowledge System. **Source can be a URL or the current conversation** — the persist step is always the Python pipeline.

| Step      | URL source                                  | Conversation source                          |
| -----------| ---------------------------------------------| ----------------------------------------------|
| Gather    | `fetch_url`                                 | Read chat / user notes                       |
| Summarize | Cursor curates fetched markdown             | Cursor curates what was discussed            |
| Persist   | `ingest_okf_concept.py --url … --body-file` | `ingest_okf_concept.py --body-file` (no URL) |
| Index     | `regenerate_indexes()` (per-KS `index.md`)  | same                                         |

Do **not** hand-edit concept files or `index.md`. Pair with **`okf-reader`** for discovery.

**Clone / register a new KS** (okf.yaml + Seed pack) → use **`okf-onboard`**, not this skill.

## Shared config (read first)

Read `~/.okf/config.json` for `python`, `okf_cli`, `okf_yaml`, and `scripts.ingest_okf_concept`. Resolve KS roots at runtime from `okf_yaml`: each `ks.<label>.path` joins onto `ks_library` (absolute paths win). Never rely on a frozen KS list. Workflow and template files (`workflow-*.md`, `templates.md`) sit in this skill's own folder. The CLI defaults to the notebook at `~/.okf` — no `--workspace` needed.

```powershell
& "<python>" "<scripts.ingest_okf_concept>" --out "<ks_library>/<ks path>" ...
& "<okf_cli>" check
```

## Multi-KS notebooks

When the workspace has `okf.yaml`, each configured root is a **Knowledge System** (ordinary OKF bundle). Labels like `personal` / `work` are not special policy roles.

| Concept type | Typical KS   | `--out`                        | `concept-id` |
| --------------| --------------| -------------------------------| --------------|
| Learning     | personal     | `<ks_library>/<personal path>` | `<slug>`     |
| Document     | work         | `<ks_library>/<work path>`     | `<slug>`     |
| Reference    | work         | `<ks_library>/<work path>`     | `<slug>`     |

**Two layers — keep both current:**

- **Per-KS `index.md`** — `regenerate_indexes()` (progressive disclosure). Never skip.
- **Workspace overlay** — `.okf/` Association store (+ Id overlay). Optional `okf viz` for humans. Not a substitute for markdown.

### Separation (mandatory)

- **See also / body links:** Intra-KS only (same KS root).
- **Cross-KS peers:** do **not** put `../other-ks/...` in markdown. After ingest, record with:

```powershell
& "<okf_cli>" associate SRC_KS SRC_PATH DST_KS DST_PATH --source ingest --note "why"
```

Agents propose pairs (C1); CLI upserts. No Derived index rebuild.

### Required frontmatter

Ingest mints a stable UUID `id`. Check requires `type`, `title`, `description`, `id`.

## When to Use

Load when the user asks to add/store knowledge into OKF (URL, conversation, notes).

## Required inputs (ask if missing)

1. **Knowledge source** — URL, or conversation topic
2. **KS / bundle path** — `--out` must be a **KS root** from `okf.yaml` (not workspace parent)
3. **Concept type / slug** — Learning / Document / Reference

Optionally: title, tags, description; Cross-KS association peers to `okf associate`.

## Choose a workflow

```
Has a URL?
├── Yes → Read [workflow-url.md](workflow-url.md) (Workflow A)
└── No  → Read [workflow-conversation.md](workflow-conversation.md) (Workflow B)
```

Load **only** the matching workflow reference after you know the source type.

## Body standards (both workflows)

Write **body only** to `--body-file` (no YAML frontmatter):

- `# Title` matching `--title`
- Optional **See also** with **Intra-KS** relative links only
- Structured `##` sections — not a raw dump
- **URL source:** end with `## Citations` linking to the page
- **Conversation source:** end with `## Citations` noting provenance

**Frontmatter** (set by script): `type`, `title`, `description`, `id` (minted UUID), `tags`, optional `resource`.

## Anti-patterns

| Don't                           | Do instead                                         |
| ---------------------------------| ----------------------------------------------------|
| Write concept `.md` directly    | `ingest_okf_concept.py --body-file`                |
| Cross-KS paths in See also      | `okf associate --source ingest`                    |
| Ingest to workspace parent      | Use KS root from `okf.yaml`                        |
| Skip `okf check`                | Always check Separation + frontmatter              |
| Treat `.okf` as source of truth | Per-KS `index.md` + concept markdown are canonical |

## References

| Source | File |
| --- | --- |
| URL ingest steps | [workflow-url.md](workflow-url.md) |
| Conversation ingest steps | [workflow-conversation.md](workflow-conversation.md) |
| Body templates | [templates.md](templates.md) |
| KS onboard (clone / seed) | Skill **`okf-onboard`** |

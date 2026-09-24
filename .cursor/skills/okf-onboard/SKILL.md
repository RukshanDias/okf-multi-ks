---
name: okf-onboard
description: >-
  Onboards a cloned Open Knowledge Format (OKF) Knowledge System into a Multi-KS
  notebook: register in okf.yaml, Id overlay for legacy missing ids, Catalog-first
  seed propose, LLM shortlist of valid Cross-KS peers, human approve, then seed
  accept. Use when the user clones/adds a KS, asks to onboard a bundle into the
  workspace, or run seed propose/accept for a newly added KS.
license: Apache-2.0
metadata:
  version: "0.2.0"
  author: Rukshan Dias
  tags: "okf, onboard, multi-ks, seed-pack, associations"
---

# OKF Onboard

Register a **new Knowledge System** (cloned OKF bundle) into the Multi-KS notebook and optionally seed Cross-KS associations. Pair with **`okf-reader`** for discovery after onboard. Concept ingest into an existing KS is **`okf-ingest`**, not this skill.

## Shared config (read first)

Read `~/.okf/config.json` for `python`, `okf_cli`, and `okf_yaml`. The notebook's KS list lives only in `okf_yaml` (`ks_library` + `ks.<label>.path`) — there is no KS map to keep in sync anywhere else. The CLI defaults to the notebook at `~/.okf` — no `--workspace` needed.

```powershell
& "<okf_cli>" seed propose --ks <label>
& "<okf_cli>" seed accept --index N
& "<okf_cli>" check
& "<okf_cli>" viz
```

## When to Use

Load when the user asks to clone, add, or onboard a KS into the Multi-KS notebook, or to review/accept a Seed pack for a newly added KS.

## Required inputs (ask if missing)

1. **KS folder** — path to the cloned bundle (must contain OKF markdown / `index.md`)
2. **KS label** — `okf.yaml` key

## Workflow

### 1. Register the KS

- Ensure the KS is cloned into the KS library (`<ks_library>/<label>/`).
- Add the label + `path` (relative to `ks_library`) to `okf.yaml` (and `link_search_order` if present).

### 2. Id overlay (legacy clones)

If concepts lack frontmatter `id`, mint path→UUID entries in the workspace Id overlay (`.okf/id-overlay.json`). **Do not rewrite** cloned concept markdown just to add `id`.

### 3. Catalog-first Seed propose (rule-based)

```powershell
& "<okf_cli>" seed propose --ks <label>
```

Writes `.okf/seed-pack.json`. Each candidate has `similarity_score` (token-overlap ranker only — **not** proof of a valid Cross-KS peer) and `reason`.

Never treat propose output as ready to accept.

### 4. LLM shortlist (mandatory)

Rule-based propose **generates candidates**. The agent **decides** which are real Cross-KS peers.

1. Read catalog signals: paths, titles, descriptions, tags, types (from indexes / frontmatter).
2. Reject stopword / generic-token noise (`and`, `the`, `for`, …) and unrelated domains.
3. **Body peek only on ties or uncertainty** — open at most the two concept bodies for that pair; do not read the whole pack’s bodies.
4. Build a **shortlist** of valid peers only. Size is agent-chosen (typically ≤5). Do **not** pad to fill a quota.
5. **Zero mapping is better than wrong mapping.** If none are valid, recommend discard; do not invent weak links.

Present to the user:

- Shortlist (1-based indexes from the pack) with a one-line why each is valid, **or**
- Explicit recommend discard

### 5. Human approve → accept

**Do not** run `seed accept` until the user approves specific indexes (or discard).

```powershell
# Approved indexes only (repeat --index)
& "<okf_cli>" seed accept --index 3 --index 7

# Only if the user explicitly asks for every pack row (rare; still after LLM review)
& "<okf_cli>" seed accept --all
```

Never auto-run `seed accept --all` on an unreviewed pack.

### 6. Finish

- `okf check` — Separation + required frontmatter (legacy missing `id` may still fail check; overlay covers associations).
- Optional: `okf viz` for the human graph.

Onboard is complete with **zero** new associations if the shortlist was empty.

## Anti-patterns

| Don't | Do instead |
| --- | --- |
| `seed accept --all` after propose | LLM shortlist → user approve → `--index` |
| Accept stopword `similarity_score` hits | Discard; zero > wrong |
| Read every candidate body | Catalog-first; body peek on ties only |
| Cross-KS paths in cloned markdown | Association store only |
| Rewrite clone frontmatter for `id` | Id overlay |
| Stuff onboard into `okf-ingest` | This skill |

## Seed pack fields

| Field | Meaning |
| --- | --- |
| `similarity_score` | Rule-based catalog overlap rank (higher ≠ valid peer) |
| `reason` | Shared tokens / ranker note — not a semantic justification |
| `a_ks` / `a_path` / `b_ks` / `b_path` | Candidate endpoints |

Packs must use `similarity_score` (not `score`). Re-run `seed propose` if an old pack fails to load.

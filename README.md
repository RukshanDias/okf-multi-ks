# OKF Multi-KS Notebook

**Keep several independent knowledge bases, and map them to each other the way you actually learn.**

This repo lets you keep several **Knowledge Systems (KSs)** in one notebook
and link related ideas *across* them without mixing their files. A KS is just
a folder of markdown files in the [Open Knowledge Format](SPEC.md) (OKF).
Your AI coding agent (Claude Code or Cursor) reads, adds to, and connects
your knowledge through skills that come with this repo. A local viewer shows
it all as one interactive graph, and you can chat with your notebook there.

📖 **The idea behind it:** [A Multi-Knowledge-System Notebook on OKF: map them like you actually learn](https://medium.com/ifs-tech/a-multi-knowledge-system-notebook-on-okf-map-them-like-you-actually-learn-15b449898d83)

---

## Contents

- [Core concepts](#core-concepts)
- [Install](#install)
- [Quick start](#quick-start)
- [How-to guides](#how-to-guides)
- [CLI reference](#cli-reference)
- [Upgrade & uninstall](#upgrade--uninstall)
- [Troubleshooting](#troubleshooting)
- [For contributors](#for-contributors)

## Core concepts

| Term | Meaning |
|------|---------|
| **Knowledge System (KS)** | One OKF bundle: a folder of markdown concepts with YAML frontmatter and an `index.md`. It can be your own notes, a team's docs repo, or anything you clone. |
| **KS library** | The folder where your KSs sit side by side (default `~/okf-knowledge-systems`). |
| **Notebook** | Your personal composition of KSs, stored at `~/.okf/` (`okf.yaml` + a local overlay). |
| **Intra-KS link** | A normal markdown link *inside* one KS. It ships with that KS when you push it. |
| **Cross-KS association** | A link *between* concepts in different KSs. It is stored only in your notebook (`~/.okf/associations.json`) and never written into anyone's markdown. |

The key rule (**Separation**): *concept files only ever link within their own
KS*. Your cross-KS maps are yours alone, so you can clone a colleague's KS,
connect it to your own notes, and still `git pull` their updates without
conflicts. When you push your own KS, you never leak your private mappings.

Full glossary: [`CONTEXT.md`](CONTEXT.md). Format spec: [`SPEC.md`](SPEC.md).

## Install

### Prerequisites

- **Python 3.11+**
- **git**
- **Windows:** [Git Bash](https://git-scm.com/download/win) (comes with Git for Windows)
- **Node.js 18+**: needed for the one-command installer and for Notebook chat with Claude
- An AI coding agent: **[Claude Code](https://claude.com/claude-code)** and/or **[Cursor](https://cursor.com)**

### Option A: one command (recommended)

```bash
npx okf-multi-ks
```

This checks your prerequisites, clones this repo to `~/okf-system`, and runs
the installer. See [`installer/README.md`](installer/README.md) for flags
(`--dir`, `--yes`, …).

### Option B: from a clone

```bash
git clone https://github.com/RukshanDias/okf-multi-ks.git ~/okf-system
cd ~/okf-system
bash install.sh        # on Windows, run this from Git Bash
```

### What the installer does

1. Creates a `.venv` in the repo and installs the `okf` CLI.
2. Copies the `okf-*` skills to `~/.claude/skills/` and `~/.cursor/skills/`.
3. Asks once for your **KS library** path (press Enter for `~/okf-knowledge-systems`).
4. Creates your notebook at `~/.okf/okf.yaml` with a small **football** example KS already in it.
5. Adds an **OKF Viewer** launcher: a Start-menu shortcut on Windows, or `~/Applications/OKF Viewer.command` on macOS.

It is safe to re-run, and it never overwrites an existing `~/.okf/okf.yaml`.

## Quick start

1. **Open the viewer.** Launch **OKF Viewer** from the Start menu or Applications,
   or run:

   ```bash
   ~/okf-system/.venv/bin/okf serve          # Windows: .venv\Scripts\okf.exe serve
   ```

   Your browser opens the notebook graph with the football example: teams,
   players, tactics, and the links between them.

2. **Ask your agent about it.** In Claude Code or Cursor:

   > *"Using my OKF notebook, which tactics does Real Madrid use?"*

   The `okf-reader` skill walks `index.md` files step by step, so the agent only loads what it needs.

3. **Add something.**

   > *"Add a concept about the high press to my football KS."*

## How-to guides

You mostly talk to your agent in plain language, and the matching skill does the work.

| I want to… | Say something like… | Skill |
|------------|---------------------|-------|
| Ask questions across my knowledge | *"What does my notebook say about X?"* | `okf-reader` |
| Save what we just discussed | *"Add this to my `notes` KS."* | `okf-ingest` |
| Save a web page as a concept | *"Ingest https://… into my `notes` KS."* | `okf-ingest` |
| Add a new KS to my notebook | *"Onboard `~/okf-knowledge-systems/team-docs` as `team`."* | `okf-onboard` |

### Create your own Knowledge System

1. Make a folder in your KS library, e.g. `~/okf-knowledge-systems/notes/`, with an `index.md`:

   ```markdown
   # My notes
   ```

2. Ask your agent: *"Onboard `notes` into my OKF notebook."* It registers the KS in `~/.okf/okf.yaml`.
3. Optional: `git init` the folder and push it anywhere. Only your markdown is pushed, never your notebook maps.

### Add someone else's Knowledge System

```bash
cd ~/okf-knowledge-systems
git clone <their-ks-repo> team-docs
```

Then ask: *"Onboard `team-docs` as `team`."* The agent will:

1. register it in `okf.yaml`,
2. run `okf seed propose` to find likely links to your other KSs,
3. shortlist only the ones that really make sense and **ask you to approve them**,
4. save the approved links with `okf seed accept`.

Having no links at all is better than having wrong ones, so the agent won't make up weak connections.

### Link two concepts across KSs by hand

```bash
okf associate notes tracing.md team observability/index.md --note "same idea, team view"
okf associations notes:tracing.md      # list a concept's cross-KS neighbours
```

### Use the viewer and Notebook chat

`okf serve` starts a small local server on `127.0.0.1` and opens the viewer. From there you can:

- see every KS as one graph: intra-KS links and cross-KS associations are drawn as different edge types,
- filter by KS, search, and open any concept's rendered markdown,
- switch between **2D** and **3D** view modes,
- click **Regenerate** after editing markdown, or **off-board** a KS,
- open **Notebook chat** to talk to an agent that can read your whole notebook.

Chat uses Claude by default (through `npx @agentclientprotocol/claude-agent-acp`, with your existing Claude login). Use `okf serve --agent opencode` to run it with [opencode](https://opencode.ai) instead.

If you only want a static HTML file, run `okf viz`. It writes `~/.okf/viz.html`.

### Keep things tidy

```bash
okf check        # frontmatter + Separation rule (no cross-KS links in markdown)
okf viz          # rebuild the graph after edits
```

### Remove a KS from the notebook

```bash
okf offboard team          # shows what will be removed
okf offboard team --yes    # does it
```

This removes the KS from `okf.yaml` and deletes its associations. **The KS folder stays on disk**, so offboarding never deletes knowledge.

## CLI reference

The `okf` CLI lives in the repo's venv (`.venv/bin/okf`, or `.venv\Scripts\okf.exe` on Windows). It uses the notebook at `~/.okf` unless you pass `--workspace <dir>`.

| Command | What it does |
|---------|--------------|
| `okf serve [--agent NAME]` | Start OKF Server: regenerate the graph, serve the viewer, and relay Notebook chat |
| `okf viz [--out PATH]` | Write the notebook graph as a standalone HTML file |
| `okf check` | Check required frontmatter and the Separation rule |
| `okf associations <uuid\|ks:path>` | List a concept's cross-KS neighbours |
| `okf associate A_KS A_PATH B_KS B_PATH [--note …]` | Add or update a cross-KS association |
| `okf seed propose --ks LABEL` | Suggest candidate associations for a newly added KS |
| `okf seed accept --index N` | Save approved candidates (repeat `--index`, or use `--all`) |
| `okf offboard LABEL [--yes]` | Remove a KS from the notebook (its files stay) |

## Upgrade & uninstall

**Upgrade:** re-run the installer. This is safe, and your notebook is kept.

```bash
npx okf-multi-ks --dir ~/okf-system --yes
# or
cd ~/okf-system && git pull && bash install.sh
```

**Uninstall:** delete the repo folder, `~/.okf/`, and the `okf-*` folders in
`~/.claude/skills/` and `~/.cursor/skills/`. Your KS library is untouched.

## Troubleshooting

- **`no working python 3.11+ found`**: install Python 3.11+ or point the installer at it: `PYTHON=/path/to/python bash install.sh`.
- **Windows: `bash` builds a Linux venv**: you ran WSL's `bash.exe`. Use Git Bash (the `npx` installer checks for this).
- **The viewer opens but chat doesn't connect**: check that Node is on `PATH` and that you're signed in to Claude Code, or try `--agent opencode`. Server logs are written to `~/.okf/serve.log`.
- **An edit doesn't show up in the graph**: click **Regenerate** in the viewer or run `okf viz`.

## For contributors

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

| Path | What's there |
|------|--------------|
| `src/okf/` | Multi-KS notebook: CLI, config, association store, seeding, OKF Server, viewer |
| `src/reference_agent/` | OKF bundle pipeline + BigQuery/web producer |
| `.cursor/skills/` | The `okf-*` agent skills (the installer copies them to Claude Code and Cursor) |
| `examples/football/` | The example KS created in new notebooks |
| `installer/` | The `npx okf-multi-ks` bootstrapper |
| `SPEC.md` · `CONTEXT.md` · `PRD.md` | Format spec · glossary · product requirements |

## Credits & license

The Open Knowledge Format specification and the original reference agent come
from the upstream [open-knowledge-format](https://github.com/amirhormati/open-knowledge-format)
project. The Multi-KS notebook, skills, OKF Server, and viewer are built on top of them.

Licensed under the [Apache License 2.0](LICENSE.md).

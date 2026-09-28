# okf-multi-ks

One-command setup for the [OKF Multi-KS](https://github.com/RukshanDias/okf-multi-ks)
system: a local notebook of markdown Knowledge Systems (KS) with a graph viewer
and an agent chat that can read and extend it.

## Prerequisites

- Node 18+ (to run `npx`)
- Python 3.11+
- `git` (on Windows this also provides Git Bash, which the installer uses)

The installer checks these before touching the disk and prints an OS-specific
fix if anything is missing.

## How to set up

1. **Install.** In a terminal run:

   ```
   npx okf-multi-ks
   ```

   It clones the repo to `~/okf-system`, creates a Python venv, installs the
   `okf` CLI and the three OKF skills, and creates your notebook with an example
   KS already in it.

2. **Open the viewer.** The installer creates an **OKF Viewer** shortcut.
   On Windows, search *OKF Viewer* in the Start menu and open it. On macOS it
   is `~/Applications/OKF Viewer.command`. Your browser opens the notebook graph.

3. **Remove the example KS (optional).** A pre-loaded KS named **football** is
   there so the graph is not empty. To remove it, open **Actions** and click
   **Off-board now** next to *football*. The folder stays on disk; only the
   notebook entry and its cross-KS links are removed.

4. **Add your own knowledge.** Open the **Chat** panel and pick **okf-ingest**
   from the skill dropdown, then type something like:

   > Add this knowledge: `<web-url>` to `<my-ks>` knowledge system

   You can list several URLs in one message. If `<my-ks>` does not exist yet
   it is created in your KS library. Confluence pages need the Atlassian MCP
   server configured in your agent first.

5. **Refresh the graph.** When ingestion finishes, open **Actions** and click
   **Regenerate now**. The new concepts and their links appear in the graph.

6. **Ask questions.** In the Chat panel pick **okf-reader** and ask anything
   about the knowledge you added. The agent walks the KS indexes step by step
   and answers from your notebook.

## The three skills

The installer copies these into `~/.claude/skills/` and `~/.cursor/skills/`,
so they work from the viewer chat, Claude Code and Cursor alike.

| Skill | Use it when you want to… | Example |
| --- | --- | --- |
| `okf-reader` | Ask questions across your notebook. Reads `index.md` files progressively so only the relevant concepts are loaded. | *"What does my notebook say about X?"* |
| `okf-ingest` | Add knowledge: a web page, a Confluence page, a file, or the conversation you just had. Writes a concept doc into a KS and regenerates its indexes. | *"Add this knowledge: https://… to `notes` knowledge system"* |
| `okf-onboard` | Register an existing KS folder (yours or a cloned one) into the notebook, then propose and approve cross-KS links. | *"Onboard `~/okf-knowledge-systems/team-docs` as `team`."* |

## Upgrading

Re-running the installer is the upgrade path. It pulls the latest repo and
re-runs the setup, and it never overwrites your existing notebook.

```
npx okf-multi-ks@latest --yes
```

## Options

| Flag | Meaning |
| --- | --- |
| `-d, --dir <path>` | where to install (default `~/okf-system`) |
| `-y, --yes` | accept defaults, no prompts |
| `-b, --branch <name>` | branch to check out |
| `--repo <url>` | install from a fork |
| `-h, --help` / `-v, --version` | usage / bootstrapper version |

| Environment | Meaning |
| --- | --- |
| `KS_LIBRARY=<path>` | where your KS folders live, skips the prompt (default `~/okf-knowledge-systems`) |
| `PYTHON=<path>` | use a specific Python |
| `OKF_ASCII=1` | plain-ASCII banner for non-UTF-8 consoles |
| `NO_COLOR=1` | disable colour |


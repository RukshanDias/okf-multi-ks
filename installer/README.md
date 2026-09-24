# okf-multi-ks

One-command setup for the [OKF Multi-KS](https://github.com/RukshanDias/okf-multi-ks) system.

```
npx okf-multi-ks
```

It checks your prerequisites, clones the repo, and runs the project's own
`install.sh` — the same two steps the README documents, with the failure modes
explained instead of dumped as raw shell output.

## What it does

1. Prints the banner.
2. **Preflights everything before touching the disk** — Python 3.11+, `git`, and
   a usable `bash`. If anything is missing it prints an OS-specific fix and
   exits, so a missing prerequisite can never leave a half-installed state.
3. Clones the repo to your chosen directory (default `~/okf-system`), or
   `git pull`s if an OKF clone is already there.
4. Hands over to `bash install.sh` with stdio inherited, so its interactive
   "KS library path" prompt and pip's output work exactly as they do today.

## Options

| Flag | Meaning |
| --- | --- |
| `-d, --dir <path>` | where to clone OKF (default `~/okf-system`) |
| `-b, --branch <name>` | branch to check out |
| `--repo <url>` | clone from a fork |
| `-y, --yes` | accept defaults, no prompts |
| `-h, --help` / `-v, --version` | usage / bootstrapper version |

| Environment | Meaning |
| --- | --- |
| `PYTHON=<path>` | use a specific Python (also honoured by `install.sh`) |
| `KS_LIBRARY=<path>` | skip `install.sh`'s KS library prompt (default `~/okf-knowledge-systems`) |
| `OKF_ASCII=1` | plain-ASCII banner for non-UTF-8 consoles |
| `NO_COLOR=1` | disable colour |

## What it does *not* remove

Python 3.11+, `git`, and (on Windows) Git Bash are still genuine
prerequisites — this detects and explains them, it does not install them.
Node becomes a new prerequisite, so this is aimed at people who already have
it, not a strictly lower bar for everyone.

## Upgrading

`install.sh` is idempotent by design (ADR-0005), so re-running is the supported
upgrade path:

```
npx okf-multi-ks --dir ~/okf-system --yes
```

## Notes for maintainers

- **Zero runtime dependencies.** Every dependency is a download the user waits
  through before anything happens, plus supply-chain surface on a script that
  goes on to execute a shell installer. The banner, colours and spinner are
  hand-rolled; the figlet art is baked in as a literal.
- **No copy of the Python source ships here.** The update model is
  git-pull-based, so a separately-versioned npm snapshot would drift.
- **This package versions independently** of `pyproject.toml` — its version
  tracks bootstrapper changes, not OKF features.
- On Windows the bootstrapper resolves Git Bash from git's own install
  location and **rejects `C:\Windows\System32\bash.exe`** (the WSL launcher),
  which would otherwise build the venv inside WSL against a Linux Python and
  write unusable paths into `~/.okf/config.json`.

## Releasing

Staged by `.github/workflows/publish-installer.yml` on a version tag. There
is no npm token in this repo — the workflow authenticates with npm **Trusted
Publishing** (OIDC) and runs `npm stage publish`. A maintainer then approves
the staged package with 2FA on npmjs.com or via `npm stage approve`.

```
# 1. bump the version here (patch for bootstrapper fixes)
npm version patch --no-git-tag-version

# 2. commit it
git commit -am "installer: v$(node -p "require('./package.json').version")"

# 3. tag with the SAME version, prefixed installer-v
git tag "installer-v$(node -p "require('./package.json').version")"
git push origin master --tags
```

The workflow refuses to stage if the tag does not match `package.json`, or if
that version already exists on the registry — a bad tag fails the run rather
than shipping something unintended. `workflow_dispatch` runs every check and
`npm pack --dry-run`, but never stages, so you can rehearse a release.

**One-time npm setup** (already done if the badge on npmjs.com says
"provenance"): on the package's npmjs.com page, *Settings → Trusted
publisher → GitHub Actions*, set organisation `RukshanDias`, repository `okf-multi-ks`,
workflow `publish-installer.yml`, and leave Environment blank. Leave **publish
directly** unchecked so this publisher can only `npm stage publish`.

#!/usr/bin/env node
'use strict';

// Thin bootstrapper for the OKF Multi-KS system (see
// docs/superpowers/specs/2026-09-20-npx-installer-prd.md).
//
// It does not replace install.sh and it does not carry a copy of the Python
// source: it preflights the prerequisites, clones (or pulls) the real repo,
// and hands over to `bash install.sh` inside it. The update model stays
// git-pull-based, per ADR-0005.

const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const ui = require('../lib/ui');
const { printBanner } = require('../lib/banner');
const { preflight } = require('../lib/preflight');

const PKG = require('../package.json');
const DEFAULT_REPO = 'https://github.com/RukshanDias/okf-multi-ks.git';
const DEFAULT_DIR = path.join(os.homedir(), 'okf-system');

function parseArgs(argv) {
  const opts = { dir: null, repo: DEFAULT_REPO, branch: null, yes: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      const v = argv[++i];
      if (v === undefined) throw new Error(`${a} needs a value`);
      return v;
    };
    if (a === '--dir' || a === '-d') opts.dir = value();
    else if (a.startsWith('--dir=')) opts.dir = a.slice(6);
    else if (a === '--repo') opts.repo = value();
    else if (a.startsWith('--repo=')) opts.repo = a.slice(7);
    else if (a === '--branch' || a === '-b') opts.branch = value();
    else if (a.startsWith('--branch=')) opts.branch = a.slice(9);
    else if (a === '--yes' || a === '-y') opts.yes = true;
    else if (a === '--help' || a === '-h') opts.help = true;
    else if (a === '--version' || a === '-v') opts.version = true;
    else throw new Error(`unknown option: ${a}`);
  }
  return opts;
}

function usage() {
  console.log(`
${ui.bold('okf-multi-ks')} — set up the OKF Multi-KS system

  ${ui.cyan('npx okf-multi-ks')} [options]

${ui.bold('Options')}
  -d, --dir <path>     where to clone OKF        ${ui.dim(`(default: ${DEFAULT_DIR})`)}
  -b, --branch <name>  branch to check out       ${ui.dim('(default: the repo default)')}
      --repo <url>     clone from a fork         ${ui.dim(`(default: ${DEFAULT_REPO})`)}
  -y, --yes            accept defaults, no prompts
  -h, --help           show this
  -v, --version        show the bootstrapper version

${ui.bold('Environment')}
  PYTHON=<path>        use a specific Python (also honoured by install.sh)
  KS_LIBRARY=<path>    KS library location      ${ui.dim('(default: ~/okf-knowledge-systems, prompted)')}
  OKF_ASCII=1          plain-ASCII banner for non-UTF-8 consoles
  NO_COLOR=1           disable colour
`);
}

/** Expand a leading ~ and make the path absolute. */
function resolveDir(p) {
  const expanded = p.startsWith('~') ? path.join(os.homedir(), p.slice(1)) : p;
  return path.resolve(expanded);
}

/** Run a command with stdio inherited, so its prompts and progress reach the user. */
function run(cmd, args, cwd, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { cwd, stdio: 'inherit', windowsHide: true, env });
    child.on('error', reject);
    child.on('close', (code, signal) => {
      if (signal) reject(new Error(`${path.basename(cmd)} killed by ${signal}`));
      else if (code !== 0) reject(new Error(`${path.basename(cmd)} exited with code ${code}`));
      else resolve();
    });
  });
}

/** True when `dir` is a git worktree whose origin points at the OKF repo. */
function isOkfClone(dir) {
  if (!fs.existsSync(path.join(dir, '.git'))) return false;
  return fs.existsSync(path.join(dir, 'install.sh')) && fs.existsSync(path.join(dir, 'pyproject.toml'));
}

async function chooseTarget(opts) {
  if (opts.dir) return resolveDir(opts.dir);
  if (opts.yes) return DEFAULT_DIR;
  const answer = await ui.ask('Install OKF to:', DEFAULT_DIR);
  return resolveDir(answer);
}

/**
 * Clone, or update in place if the target is already an OKF clone.
 * Anything else already sitting at the target is left strictly alone.
 */
async function fetchRepo(target, opts) {
  if (isOkfClone(target)) {
    ui.step(`Updating existing clone at ${target}`);
    // Both git pull and install.sh are idempotent (ADR-0005), so re-running
    // over an existing install is the supported upgrade path, not an error.
    await run('git', ['-C', target, 'pull', '--ff-only']);
    if (opts.branch) await run('git', ['-C', target, 'checkout', opts.branch]);
    return;
  }

  if (fs.existsSync(target) && fs.readdirSync(target).length > 0) {
    throw new Error(
      `${target} already exists and is not an OKF clone.\n` +
        `  Pick another location with --dir <path>, or remove that directory yourself.`
    );
  }

  ui.step(`Cloning ${opts.repo}`);
  const args = ['clone'];
  if (opts.branch) args.push('--branch', opts.branch);
  args.push(opts.repo, target);
  await run('git', args);
}

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    printBanner();
    ui.fail(err.message);
    usage();
    process.exitCode = 2;
    return;
  }

  if (opts.version) {
    console.log(PKG.version);
    return;
  }

  printBanner();

  if (opts.help) {
    usage();
    return;
  }

  // 1. Preflight everything before touching the disk, so a missing
  //    prerequisite can never leave a half-cloned, half-installed state.
  const spin = ui.spinner('Checking prerequisites');
  const checks = preflight();
  spin.stop();

  if (!checks.ok) {
    ui.fail('Missing prerequisites — nothing has been installed.\n');
    for (const p of checks.problems) {
      console.error(`  ${ui.red('✗')} ${ui.bold(p.name)}: ${p.error}`);
      if (p.fix) console.error(`    ${ui.dim('→')} ${p.fix}`);
    }
    console.error(`\n  ${ui.dim('Re-run')} ${ui.cyan('npx okf-multi-ks')} ${ui.dim('once these are installed.')}\n`);
    process.exitCode = 1;
    return;
  }

  ui.ok(`Python ${checks.python.version} ${ui.dim(checks.python.exe)}`);
  ui.ok(`${checks.git.version}`);
  ui.ok(`bash ${ui.dim(checks.bash.exe)}`);

  // 2. Target directory.
  const target = await chooseTarget(opts);

  // 3. Clone or update.
  await fetchRepo(target, opts);

  // 4. Hand over to the real installer. stdio is inherited so its interactive
  //    "KS library path" prompt still works and pip's output stays visible.
  //
  //    PYTHON is forwarded so install.sh uses the interpreter preflight just
  //    verified, instead of searching again and finding something different.
  //    Its own search is `command -v python3`, which on Windows matches the
  //    Microsoft Store alias stub in %LOCALAPPDATA%\Microsoft\WindowsApps —
  //    that stub is on PATH by default and answers `python3 -m venv` with
  //    "Python was not found" instead of running. Forward slashes because the
  //    value is handed to bash.
  ui.step('Running install.sh');
  ui.info(ui.dim('this creates the venv and pip-installs OKF — it can take a few minutes'));
  const env = { ...process.env, PYTHON: checks.python.exe.replace(/\\/g, '/') };
  await run(checks.bash.exe, ['install.sh'], target, env);

  console.log('');
  ui.ok(ui.bold('OKF Multi-KS is installed.'));
  console.log(`
  ${ui.dim('Repo:')}    ${target}
  ${ui.dim('Notebook:')} ${path.join(os.homedir(), '.okf', 'okf.yaml')}

  ${ui.bold('Next:')}
    ${ui.cyan('okf serve')}   ${ui.dim('start the OKF server (or use the desktop shortcut)')}
    ${ui.dim('New notebooks include the football example in the configured KS library.')}
    ${ui.dim('Onboard additional KSs by cloning them into that library and running the okf-onboard skill.')}

  ${ui.dim('To upgrade later:')} ${ui.cyan(`npx okf-multi-ks --dir ${target} --yes`)}
`);
}

main().catch((err) => {
  console.error('');
  ui.fail(err.message);
  process.exitCode = 1;
});

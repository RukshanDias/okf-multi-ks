'use strict';

const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const MIN_PYTHON = [3, 11]; // pyproject.toml: requires-python = ">=3.11"

/** Run a command for its stdout; null if it can't be run at all. */
function tryExec(cmd, args) {
  try {
    return execFileSync(cmd, args, {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 15000,
      windowsHide: true,
    }).trim();
  } catch {
    return null;
  }
}

function remediation(what) {
  const mac = process.platform === 'darwin';
  const win = process.platform === 'win32';
  if (what === 'python') {
    if (win) return 'winget install Python.Python.3.13   (or download from https://python.org/downloads)';
    if (mac) return 'brew install python@3.13   (or download from https://python.org/downloads)';
    return 'sudo apt install python3.13 python3.13-venv   (or your distro equivalent)';
  }
  if (what === 'git') {
    if (win) return 'winget install Git.Git   (or download from https://git-scm.com/download/win)';
    if (mac) return 'brew install git   (or run: xcode-select --install)';
    return 'sudo apt install git   (or your distro equivalent)';
  }
  if (what === 'bash') {
    return 'Git for Windows ships Git Bash — install it from https://git-scm.com/download/win';
  }
  return '';
}

/**
 * Locate a Python >= 3.11. Returns { exe, version } or { error }.
 * Honours PYTHON= the same way install.sh does, so an explicit choice here
 * carries through to the installer.
 */
function findPython() {
  const override = process.env.PYTHON;
  const candidates = override
    ? [override]
    : process.platform === 'win32'
      ? ['py', 'python', 'python3']
      : ['python3.14', 'python3.13', 'python3.12', 'python3.11', 'python3', 'python'];

  let best = null;
  for (const cand of candidates) {
    // `py` is the Windows launcher: ask it for the newest 3.x it knows about.
    const args = cand === 'py' ? ['-3', '-c', 'import sys;print(sys.executable);print(*sys.version_info[:3])'] : ['-c', 'import sys;print(sys.executable);print(*sys.version_info[:3])'];
    const out = tryExec(cand, args);
    if (!out) continue;
    const [exe, ver] = out.split(/\r?\n/);
    const parts = (ver || '').split(' ').map(Number);
    if (parts.length < 2 || Number.isNaN(parts[0])) continue;
    const meets = parts[0] > MIN_PYTHON[0] || (parts[0] === MIN_PYTHON[0] && parts[1] >= MIN_PYTHON[1]);
    const found = { exe: exe || cand, version: parts.join('.'), meets };
    if (meets) return found;
    if (!best) best = found; // remember a too-old one for a better error message
  }

  if (best) {
    return {
      error: `Python ${best.version} found at ${best.exe}, but OKF needs ${MIN_PYTHON.join('.')}+`,
      fix: remediation('python'),
    };
  }
  return {
    error: override
      ? `PYTHON is set to "${override}" but that is not a runnable Python`
      : 'Python 3.11+ not found on PATH',
    fix: remediation('python'),
  };
}

/**
 * Locate a bash that can actually run install.sh on Windows.
 *
 * Bare `bash` on PATH is a trap on Win11: C:\Windows\System32\bash.exe is the
 * WSL launcher, and running install.sh there builds the venv inside the Linux
 * filesystem against a Linux Python, so the Windows-side `okf` CLI and the
 * generated ~/.okf/config.json paths are all wrong. Resolve Git Bash from
 * git's own install location first, and reject the System32 shim outright.
 */
function findBash(gitExe) {
  if (process.platform !== 'win32') {
    const out = tryExec('bash', ['--version']);
    return out ? { exe: 'bash' } : { error: 'bash not found on PATH', fix: remediation('bash') };
  }

  if (gitExe) {
    // git.exe turns up at …/Git/cmd, …/Git/bin or …/Git/mingw64/bin depending on how PATH was set up
    let dir = path.dirname(gitExe);
    for (let up = 0; up < 3; up++) {
      dir = path.dirname(dir);
      for (const rel of ['bin/bash.exe', 'usr/bin/bash.exe']) {
        const candidate = path.join(dir, rel);
        if (fs.existsSync(candidate)) return { exe: candidate };
      }
    }
  }

  const onPath = tryExec('where', ['bash']);
  const first = onPath ? onPath.split(/\r?\n/)[0].trim() : null;
  if (first && !/system32/i.test(first)) return { exe: first };

  return {
    error: first
      ? `the only bash on PATH is ${first} (the WSL launcher), which cannot run the Windows installer`
      : 'bash not found — install.sh needs Git Bash on Windows',
    fix: remediation('bash'),
  };
}

/** Returns { ok: true, python, git, bash } or { ok: false, problems: [...] }. */
function preflight() {
  const problems = [];

  const gitVersion = tryExec('git', ['--version']);
  let gitExe = null;
  if (!gitVersion) {
    problems.push({ name: 'git', error: 'git not found on PATH', fix: remediation('git') });
  } else {
    const which = tryExec(process.platform === 'win32' ? 'where' : 'which', ['git']);
    gitExe = which ? which.split(/\r?\n/)[0].trim() : null;
  }

  const python = findPython();
  if (python.error) problems.push({ name: 'python', ...python });

  const bash = findBash(gitExe);
  if (bash.error) problems.push({ name: 'bash', ...bash });

  if (problems.length) return { ok: false, problems };
  return { ok: true, python, git: { version: gitVersion, exe: gitExe }, bash };
}

module.exports = { preflight, tryExec, MIN_PYTHON };

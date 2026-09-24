'use strict';

// Terminal output helpers. Deliberately dependency-free: this package is a
// bootstrapper that runs via `npx`, so every dependency is a download the user
// waits through before anything happens, plus supply-chain surface on a script
// that then executes a shell installer. Colours, gradient and spinner are all
// short enough to hand-roll.

const tty = process.stdout.isTTY === true;
// https://no-color.org/ — any non-empty value disables colour.
const colorOn = tty && !process.env.NO_COLOR && process.env.TERM !== 'dumb';

const wrap = (open, close) => (s) => (colorOn ? `\u001b[${open}m${s}\u001b[${close}m` : s);

const bold = wrap(1, 22);
const dim = wrap(2, 22);
const red = wrap(31, 39);
const green = wrap(32, 39);
const yellow = wrap(33, 39);
const cyan = wrap(36, 39);

function rgb(r, g, b, s) {
  return colorOn ? `\u001b[38;2;${r};${g};${b}m${s}\u001b[39m` : s;
}

/** Linear blend between two [r,g,b] stops, t in [0,1]. */
function lerp(a, b, t) {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

module.exports = {
  tty,
  colorOn,
  bold,
  dim,
  red,
  green,
  yellow,
  cyan,
  rgb,
  lerp,

  info: (msg) => console.log(`${dim('·')} ${msg}`),
  step: (msg) => console.log(`\n${cyan('▸')} ${bold(msg)}`),
  ok: (msg) => console.log(`${green('✓')} ${msg}`),
  warn: (msg) => console.log(`${yellow('!')} ${msg}`),
  fail: (msg) => console.error(`${red('✗')} ${msg}`),

  /**
   * Minimal spinner. Only animates on a TTY; elsewhere it prints one line up
   * front so CI logs stay readable. Never used around a child process that
   * inherits stdio — the two would fight over the cursor.
   */
  spinner(label) {
    if (!tty) {
      console.log(`${dim('·')} ${label}…`);
      return { stop() {} };
    }
    const frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
    let i = 0;
    process.stdout.write('\u001b[?25l'); // hide cursor
    const tick = () => {
      process.stdout.write(`\r${cyan(frames[i++ % frames.length])} ${label}`);
    };
    tick();
    const timer = setInterval(tick, 80);
    return {
      stop(finalLine) {
        clearInterval(timer);
        process.stdout.write(`\r\u001b[2K\u001b[?25h`); // clear line, show cursor
        if (finalLine) console.log(finalLine);
      },
    };
  },

  /** Prompt with a default. Resolves to the default immediately when not a TTY. */
  ask(question, fallback) {
    if (!tty || !process.stdin.isTTY) return Promise.resolve(fallback);
    const readline = require('node:readline');
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    return new Promise((resolve) => {
      rl.question(`${cyan('?')} ${question} ${dim(`[${fallback}]`)} `, (answer) => {
        rl.close();
        resolve(answer.trim() || fallback);
      });
    });
  },
};

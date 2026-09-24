'use strict';

const { bold, dim, rgb, lerp } = require('./ui');

const ART = [
                                                                       
' ██████╗ ██╗  ██╗███████╗',
'██╔═══██╗██║ ██╔╝██╔════╝   ██▄  ▄██ ▄▄ ▄▄ ▄▄   ▄▄▄▄▄▄ ▄▄     ██ ▄█▀ ▄█████ ',                                                                       
'██║   ██║█████╔╝ █████╗     ██ ▀▀ ██ ██ ██ ██     ██   ██ ▄▄▄ ████   ▀▀▀▄▄▄ ',
'╚██████╔╝██║  ██╗██║        ██    ██ ▀███▀ ██▄▄▄  ██   ██     ██ ▀█▄ █████▀ ',
' ╚═════╝ ╚═╝  ╚═╝╚═╝        ',
                                                                       
];

const ASCII_ART = [
  '   ___  _  _______ ',
  '  / _ \\| |/ /  ___|',
  " | | | | ' /| |_   ",
  ' | |_| | . \\|  _|  ',
  '  \\___/|_|\\_\\_|    ',
  '  __  __ _   _ _  _____ ___    _  _____ ',
  ' |  \\/  | | | | ||_   _|_ _|__| |/ / __|',
  " | |\\/| | |_| | |__| |  | |___| ' <\\__ \\",
  ' |_|  |_|\\___/|____|_| |___|  |_|\\_\\___/',
];

const FROM = [0, 200, 255]; // cyan
const TO = [140, 82, 255]; // violet

function printBanner() {
  const art = process.env.OKF_ASCII ? ASCII_ART : ASCII_ART; // for now follow ascii version

  console.log('');
  art.forEach((line, i) => {
    const [r, g, b] = lerp(FROM, TO, art.length > 1 ? i / (art.length - 1) : 0);
    console.log('  ' + rgb(r, g, b, line));
  });
  console.log('  ' + dim('by ') + bold(rgb(TO[0], TO[1], TO[2], 'RUDI')));
  console.log('');
}

module.exports = { printBanner };

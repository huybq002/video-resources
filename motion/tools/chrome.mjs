// where the headless browser lives: CHROMIUM_PATH, the Playwright cache, or the system package
import fs from 'fs'; import path from 'path';
export function chromePath() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const home = process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'ms-playwright') : path.join(process.env.HOME || '', '.cache', 'ms-playwright');
  // prefer the headless shell (smaller, made for this), then full Chromium
  if (fs.existsSync(home)) for (const pre of ['chromium_headless_shell-', 'chromium-']) for (const d of fs.readdirSync(home).filter(d => d.startsWith(pre)).sort().reverse()) {
    for (const exe of ['chrome-headless-shell-win64/chrome-headless-shell.exe', 'chrome-headless-shell-linux64/chrome-headless-shell', 'chrome-win64/chrome.exe', 'chrome-win/chrome.exe', 'chrome-linux/chrome', 'chrome-linux64/chrome']) { const p = path.join(home, d, exe); if (fs.existsSync(p)) return p; }
  }
  for (const p of ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome']) if (fs.existsSync(p)) return p;
  throw new Error('no Chromium found: set CHROMIUM_PATH');
}


// no-third-party-loads.spec.js
//
// GDPR / Datenschutz watchdog: walks every HTML page in public/, navigates
// to it with a real browser, captures every network request, and asserts
// that no request resolves to a host outside the local server. Any
// jsdelivr / cdnjs / fonts.googleapis / unpkg / etc. drift will fail the
// test before merge.
//
// One test per page. The list is built at import time from the public/
// tree, so this file does not need updating when new pages are added —
// just re-run after `zola build`.
//
// Allowed hosts (treated as "first-party"):
//   - 127.0.0.1, localhost, 0.0.0.0  (the Playwright webServer)
//   - pulseengine.eu, www.pulseengine.eu  (Zola's get_url emits absolute
//     URLs against config.base_url, so the local build's HTML references
//     these — they are rewritten to the local server below to keep the
//     test self-contained and CI-compatible without outbound internet)
//   - data:, blob:, about: schemes (in-memory, no network)
//
// Adding a deliberate external load? Add it to ALLOWED_EXTERNAL with a
// reason comment — that turns the watchdog into a positive policy
// statement rather than an undocumented escape hatch.

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const PUBLIC_DIR = path.resolve(__dirname, '..', '..', 'public');
const PORT = 8888;
const LOCAL_ORIGIN = `http://127.0.0.1:${PORT}`;

const FIRST_PARTY_HOSTS = new Set([
  '127.0.0.1',
  'localhost',
  '0.0.0.0',
  'pulseengine.eu',
  'www.pulseengine.eu',
]);

// Explicit allowlist for any external load that is intentionally permitted.
// Empty by default — every entry should have a comment explaining why.
const ALLOWED_EXTERNAL = new Set([
  // (none — site is fully self-hosted as of GDPR audit)
]);

function findHtmlFiles(dir, base = dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...findHtmlFiles(full, base));
    } else if (entry.name.endsWith('.html')) {
      const rel = '/' + path.relative(base, full).replace(/\\/g, '/');
      out.push(rel);
    }
  }
  return out;
}

const PAGES = findHtmlFiles(PUBLIC_DIR);

test.describe('no third-party network loads', () => {
  test('public/ contains HTML files to test', () => {
    expect(PAGES.length).toBeGreaterThan(0);
  });

  for (const url of PAGES) {
    test(url, async ({ page }) => {
      const externalRequests = [];

      // Rewrite first-party absolute URLs (pulseengine.eu) to the local
      // test server. We can't use `route.continue({url})` because that
      // rejects the https→http protocol downgrade; `route.fetch()` +
      // `route.fulfill({response})` is the canonical Playwright pattern
      // for cross-origin proxying. The original request URL is still
      // what `page.on('request', ...)` sees, so allowlist logic below
      // remains correct.
      await page.route('**/*', async (route) => {
        const reqUrl = route.request().url();
        let parsed;
        try {
          parsed = new URL(reqUrl);
        } catch {
          return route.continue();
        }
        if (parsed.hostname === 'pulseengine.eu' || parsed.hostname === 'www.pulseengine.eu') {
          const local = LOCAL_ORIGIN + parsed.pathname + parsed.search;
          try {
            const response = await route.fetch({ url: local });
            return route.fulfill({ response });
          } catch (err) {
            return route.abort();
          }
        }
        return route.continue();
      });

      page.on('request', (req) => {
        const reqUrl = req.url();

        // Schemes that don't hit the network — ignore.
        if (reqUrl.startsWith('data:') || reqUrl.startsWith('blob:') || reqUrl.startsWith('about:')) {
          return;
        }

        let host;
        try {
          host = new URL(reqUrl).hostname;
        } catch {
          return; // unparseable URL — skip
        }

        if (FIRST_PARTY_HOSTS.has(host)) return;
        if (ALLOWED_EXTERNAL.has(host)) return;

        externalRequests.push(reqUrl);
      });

      // networkidle waits 500ms after the last network request — good
      // enough for static pages with one or two deferred scripts.
      await page.goto(url, { waitUntil: 'networkidle' });

      if (externalRequests.length > 0) {
        const list = externalRequests.map((u) => `  - ${u}`).join('\n');
        throw new Error(
          `Page ${url} triggered ${externalRequests.length} external request(s):\n${list}\n\n` +
            `Either self-host the resource or add the host to ALLOWED_EXTERNAL ` +
            `in tests/playwright/no-third-party-loads.spec.js with a justification.`
        );
      }
    });
  }
});

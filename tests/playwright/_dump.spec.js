const { test } = require('@playwright/test');
const fs = require('fs');

test('dump mermaid SVG', async ({ page }) => {
  const html = `<!DOCTYPE html><html><body>
<pre class="mermaid">
flowchart TB
    A[Node A]:::tool --> B[Node B]:::good
    classDef tool fill:#1a1d27,stroke:#6c8cff,color:#e1e4ed;
    classDef good fill:#1a1d27,stroke:#4ade80,color:#e1e4ed;
</pre>
<script src="${'file://' + require('path').resolve('static/mermaid.min.js')}"></script>
<script>
  window.__esbuild_esm_mermaid_nm.mermaid.initialize({startOnLoad: true});
</script>
</body></html>`;
  await page.setContent(html);
  await page.waitForTimeout(1500);
  const svg = await page.locator('.mermaid svg').innerHTML();
  fs.writeFileSync('/tmp/mermaid-rendered.html', svg);
});

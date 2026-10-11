// Local typography preview only: no GitHub service, Mermaid or MathJax renderer.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const modules = process.argv[2];
const executablePath = process.argv[3];
const { marked } = await import(pathToFileURL(path.join(modules, 'marked/lib/marked.esm.js')));
const { chromium } = await import(pathToFileURL(path.join(modules, 'playwright/index.mjs')));
const out = path.resolve('run/run_003/artifacts');
const context = await chromium.launchPersistentContext(path.join(out, 'private/browser-profile'), {
  executablePath, headless: true, viewport: { width: 1120, height: 1080 },
});
await context.route('**/*', route => route.abort());
try {
  const svg = (await fs.readFile('docs/figures/spt_setup.svg')).toString('base64');
  for (const [file, lang] of [['README.md', 'en'], ['README.zh-CN.md', 'zh']]) {
    const markdown = await fs.readFile(file, 'utf8');
    const body = marked.parse(markdown).replaceAll('src="docs/figures/spt_setup.svg"', `src="data:image/svg+xml;base64,${svg}"`);
    const page = await context.newPage();
    await page.setContent(`<!doctype html><html><meta charset="utf-8"><style>
      body { margin:0; color:#1f2328; background:#fff; font:16px/1.55 Arial,sans-serif; }
      article { max-width:960px; margin:30px auto; padding:0 28px; }
      h1 { font-size:36px; } h2 { font-size:24px; border-bottom:1px solid #d1d9e0; padding-bottom:8px; }
      a { color:#0969da; } img { max-width:100%; } table { border-collapse:collapse; }
      th,td { border:1px solid #d1d9e0; padding:6px 12px; } pre { padding:16px; background:#f6f8fa; overflow:auto; }
    </style><article>${body}</article></html>`);
    await page.screenshot({ path:path.join(out, `readme_${lang}_preview.png`) });
    await page.close();
  }
  await fs.writeFile(path.join(out, 'preview_scope.json'), JSON.stringify({
    status:'PASS', method:'Existing Edge headless + marked; local inline SVG, network requests blocked',
    scope:'First-screen typography only. Not GitHub, Mermaid or MathJax rendering.',
    previews:['run/run_003/artifacts/readme_en_preview.png','run/run_003/artifacts/readme_zh_preview.png'],
  },null,2)+'\n');
} finally { await context.close(); }

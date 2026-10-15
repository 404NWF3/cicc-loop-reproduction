// Research deck adapted from guizang-ppt-skill, AGPL-3.0.
// Copyright (c) 2026 op7418; modifications: Loop Research.
import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { ArrowRight, ArrowUpRight, ArrowDown, RotateCcw } from 'lucide-react';
import { renderSlides } from './content.mjs';

const dir = new URL('./', import.meta.url);
const output = new URL('../public/presentation/', dir);
const read = (path) => readFile(new URL(path, dir), 'utf8');
const slides = JSON.parse(await read('../src/presentation/slides.json'));
const results = JSON.parse(await read('../src/presentation/local-results.json'));
const plan = JSON.parse(await read('plan.json'));
const escape = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
const pad = (n) => String(n).padStart(2, '0');
const icon = (component, size = 22) =>
  renderToStaticMarkup(createElement(component, { size, 'aria-hidden': true, strokeWidth: 1.4 }));
const content = renderSlides({
  slides,
  results,
  plan,
  escape,
  pad,
  icons: {
    right: icon(ArrowRight),
    upRight: icon(ArrowUpRight, 24),
    down: icon(ArrowDown),
    loop: icon(RotateCcw),
    wide: icon(ArrowRight, 42),
  },
});
if (slides.length !== 14 || plan.length !== slides.length || content.length !== slides.length) {
  throw new Error('Content, layout plan and notes must have fourteen matching pages.');
}
const sections = slides
  .map(
    (
      s,
      i,
    ) => `<section class='slide ${plan[i].theme}' data-theme='${plan[i].theme.includes('light') ? 'light' : 'dark'}' data-slide-id='${s.visual}' data-layout='${plan[i].layout}' aria-label='第 ${i + 1} 页：${plan[i].title}' aria-roledescription='幻灯片'>
  <div class='chrome'><span>LOOP RESEARCH / 研究札记</span><span>${s.section} · ${pad(i + 1)} / ${slides.length}</span></div>
  ${content[i]}
  <div class='foot'><span>${escape(s.source)}</span><span>${pad(i + 1)} / ${slides.length}</span></div>
</section>`,
  )
  .join('\n');
const noteSupplements = {
  cover: '现场实验使用历史开发快照，实时指现场计算，并非实时行情。',
  fsa: '冻结骨架能够改变搜索方向，不能单独保证不同公式的经济机制彼此独立。',
  concentration: '结构多样性仍需在收益、持仓与容量层面继续检验。',
  crowding: '执行端监管与发现端的同质化是两个不同层次的问题。',
};
const notes = slides.map((s, i) => ({
  id: s.visual,
  title: `${plan[i].title} · ${s.title.replace('\n', '')}`,
  section: s.section,
  purpose: plan[i].purpose,
  talk: [
    ...(s.notes
      .match(/[^。]+。?/g)
      ?.map((t) => t.trim())
      .filter(Boolean) ?? [s.notes]),
    ...(noteSupplements[s.visual] ? [noteSupplements[s.visual]] : []),
  ],
  transition: plan[i].transition,
  ...(s.visual === 'demo'
    ? { fallback: '网络不可用时，返回「样本外」页查看已归档的本地结果。' }
    : {}),
}));
let html = await read('template.html');
html = html.replace(
  '<html lang="zh-CN">',
  '<html lang="zh-CN">\n<!-- Adapted from guizang-ppt-skill by op7418, commit c91369c449d34755d320a8b81d0734000d99d1ab. AGPL-3.0; modified for Loop Research. Corresponding source and license: ./source/index.html -->',
);
html = html.replace('[必填] 替换为 PPT 标题 · Deck Title', '因子工厂 · 中金 AI 因子挖掘研究');
html = html.replace(/<link[^>]+(?:fonts\.googleapis|fonts\.gstatic)[^>]*>/g, '');
html = html.replace(
  '<!-- SLIDES_HERE -->',
  sections.replace(/<section [^>]+>/g, (tag) => tag.replaceAll("'", '"')),
);
html = html.replace(
  /const SPEAKER_NOTES = \[[\s\S]*?\n\];/,
  `const SPEAKER_NOTES = ${JSON.stringify(notes, null, 2).replaceAll('<', '\\u003c')};`,
);
html = html.replace("stored === '1' || (stored === null && reduced)", "stored !== '0' || reduced");
// Keep the template navigation and presenter runtime; use static backgrounds,
// local fonts and inline Lucide icons. No WebGL or CDN requests are needed.
const glStart = html.indexOf('/* =============== WebGL 双背景');
const navStart = html.indexOf('// =============== 导航');
if (glStart < 0 || navStart < glStart) throw new Error('Upstream template markers changed.');
html = html.slice(0, glStart) + html.slice(navStart);
html = html.replace(/<canvas[^>]+class="bg"[^>]*><\/canvas>/g, '');
html = html.replace(/<script src="https:\/\/unpkg\.com\/lucide[^"]*"><\/script>/, '');
html = html.replace('<script>lucide.createIcons();</script>', '');
html = html.replace(
  /<!-- ============ Motion One 动效引擎[\s\S]*?<script type="module">[\s\S]*?<\/script>/,
  '',
);
html = html.replace('</head>', `<style>\n${await read('style-a.css')}\n</style>\n</head>`);
html = html.replace('</body>', `<script>\n${await read('bridge.js')}\n</script>\n</body>`);
// Inactive pages must not enter the keyboard focus order or accessibility tree.
html = html.replace(
  'if(lock&&!opts.force)return;',
  'if(lock&&!opts.force&&!window.__lowPowerMode)return;',
);
html = html.replace(
  'window.__currentSlideIndex = idx;',
  `window.__currentSlideIndex = idx;
  slides.forEach((s,i)=>{s.inert=i!==idx;s.setAttribute('aria-hidden',String(i!==idx));});
  window.dispatchEvent(new CustomEvent('research-slide-change',{detail:{index:idx}}));`,
);
html = html.replace(
  'wheelAcc+=e.deltaY+e.deltaX;',
  `if(document.body.classList.contains('ppt-presenter') || overviewOn || matchMedia('(max-width:700px)').matches || e.target.closest('aside,dialog,input,textarea')) return;
  wheelAcc+=e.deltaY+e.deltaX;`,
);
html = html.replace(
  'const dx=(e.changedTouches[0].clientX-tx);',
  `if(document.body.classList.contains('ppt-presenter') || overviewOn) return;
  const dx=(e.changedTouches[0].clientX-tx);`,
);
html = html.replace(
  'if(window.__pptPresenter?.handleKey(e))return;',
  `if(window.__pptPresenter?.handleKey(e))return;
  if(e.target.closest('input,textarea,select,[contenteditable]') || e.metaKey || e.ctrlKey || e.altKey) return;
  if(e.key === ' ' && e.target.closest('button,a')) return;
  if(['ArrowRight','ArrowLeft','ArrowDown','ArrowUp','PageDown','PageUp','Home','End',' '].includes(e.key)) e.preventDefault();`,
);
html = html.replace(
  "b.setAttribute('aria-label','Page '+(i+1));",
  "b.setAttribute('aria-label','第 '+(i+1)+' 页：'+SPEAKER_NOTES[i].title);",
);
html = html.replace(
  'clone.style.cssText=',
  "clone.inert=true;clone.removeAttribute('aria-hidden');clone.style.cssText=",
);
html = html.replace(
  'card.onclick=()=>{toggleOverview();go(i)};',
  `card.tabIndex=0;card.setAttribute('role','button');card.setAttribute('aria-label','前往第 '+(i+1)+' 页：'+SPEAKER_NOTES[i].title);
    card.onclick=()=>{toggleOverview();go(i,{force:true});};
    card.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.stopPropagation();card.click();}};`,
);
html = html.replaceAll("},'*');", '},location.origin);');
html = html.replaceAll("postMessage(message,'*')", 'postMessage(message,location.origin)');
html = html.replace(
  "addEventListener('message',e=>receive(e.data));",
  "addEventListener('message',e=>{if(e.origin===location.origin)receive(e.data);});",
);
// Preview the complete desktop composition rather than triggering mobile layout
// inside a small iframe. Annotation coordinates still use the rendered bounds.
html = html.replace(
  'frame.style.width=`${width}px`;frame.style.height=`${height}px`;',
  'frame.style.width="1440px";frame.style.height="810px";frame.style.transform=`translate(-50%,-50%) scale(${width/1440})`;',
);
await mkdir(output, { recursive: true });
await writeFile(new URL('deck.html', output), html);
const sourceDir = new URL('source/', output);
await mkdir(sourceDir, { recursive: true });
const sourceFiles = [
  ['template.html', 'template.html.txt'],
  ['build.mjs', 'build.mjs.txt'],
  ['content.mjs', 'content.mjs.txt'],
  ['plan.json', 'plan.json.txt'],
  ['style-a.css', 'style-a.css.txt'],
  ['bridge.js', 'bridge.js.txt'],
  ['../src/presentation/slides.json', 'slides.json.txt'],
  ['../src/presentation/local-results.json', 'local-results.json.txt'],
];
for (const [from, to] of sourceFiles) await copyFile(new URL(from, dir), new URL(to, sourceDir));
await writeFile(new URL('deck.html.txt', sourceDir), html);
await writeFile(
  new URL('index.html', sourceDir),
  `<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>演示源码与许可</title><style>body{font:17px/1.8 system-ui;max-width:760px;margin:60px auto;padding:0 24px;color:#0a1f3d;background:#f1f3f5}a{color:inherit}</style><h1>演示源码与许可</h1><p>网页演示基于 <a href='https://github.com/op7418/guizang-ppt-skill/tree/c91369c449d34755d320a8b81d0734000d99d1ab'>guizang-ppt-skill</a>。Copyright © 2026 op7418；Loop Research 适配修改。本演示模板及衍生代码遵循 <a href='../licenses/AGPL-3.0.txt'>AGPL-3.0</a>，不提供担保，可以按许可复制、修改和传播。照片与字体沿用各自许可。</p><p>下列文本为当前部署版本的完整源码。构建文件位于 web/presentation/，研究 JSON 位于 web/src/presentation/；安装项目锁定的 npm 依赖后运行 node web/presentation/build.mjs。独立 HTML 也可直接编辑并与同目录图片及字体一起使用。</p><ul>${['deck.html.txt', ...sourceFiles.map(([, to]) => to)].map((f) => `<li><a href='${f}'>${f.replace('.txt', '')}</a></li>`).join('')}</ul><p><a href='https://github.com/404NWF3/cicc-loop-reproduction'>完整项目、依赖版本与构建说明</a> · <a href='../FONT-LICENSE.txt'>字体许可</a> · <a href='../sources.json'>图像来源</a></p><a href='/presentation' target='_top'>返回研究演示</a></html>`,
);
console.log(`Built ${slides.length} Style A slides (${Buffer.byteLength(html)} bytes).`);

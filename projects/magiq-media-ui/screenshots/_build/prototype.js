/* Generates prototype/index.html — single self-contained file:
 *  - left nav through all screens (isolated via <iframe srcdoc>)
 *  - click-through FLOW: in-screen actions navigate between screens
 *  - live design-system page
 *  - FULLY OFFLINE: Tabler (subset, 116 icons) + Manrope embedded as data-URI woff2
 * Opens directly in a browser (file://) — no server, no internet. Run: node prototype.js
 */
const fs = require('fs');
const path = require('path');

const SCREENS = path.join(__dirname, 'screens');
const TOKENS = fs.readFileSync(path.resolve(__dirname, '../../design-system/tokens.css'), 'utf8');
const FONTS = fs.readFileSync(path.join(__dirname, 'fonts-inline.css'), 'utf8'); // data-URI @font-face, once
const OUT_DIR = path.resolve(__dirname, '../../prototype');
fs.mkdirSync(OUT_DIR, { recursive: true });

// Screen srcdoc: NO fonts here (parent injects them post-load to avoid 28x duplication)
const SCREEN_HEAD = `<!doctype html><html><head><meta charset="utf-8">
<style>${TOKENS}*{box-sizing:border-box}body{margin:0;background:var(--surface-0);font-family:var(--font-sans);color:var(--text-primary);line-height:1.5}h1,h2,h3{color:var(--text-primary);font-weight:500;margin:0}button{font-family:inherit}input,textarea,select{font-family:inherit;border:0.5px solid var(--border-strong);border-radius:8px;background:var(--surface-2);color:var(--text-primary);padding:0 10px;font-size:13px}textarea{padding:8px 10px}.page{width:100%;max-width:960px;margin:0 auto;padding:20px}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden}code{font-family:var(--font-mono)}</style>
<script>function sendPrompt(){}function openLink(){}window.__nav=function(t){parent.postMessage({pn:t},'*')}</script></head><body><div class="page">`;
const SCREEN_FOOT = `</div></body></html>`;

const files = fs.readdirSync(SCREENS).filter(f => f.endsWith('.html')).sort();
const title = f => f.replace(/\.wide/, '').replace(/\.html$/, '').replace(/^\d+-/, '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const num = f => f.match(/^(\d+)/)[1];

const groups = [
  { label: 'Frame & auth', range: ['01','02','05','13','14','19'] },
  { label: 'Library', range: ['03','06','16','20','21','22','24'] },
  { label: 'Workflows', range: ['04','07','09','10','17','23','25','26','27','28'] },
  { label: 'Discovery', range: ['08'] },
  { label: 'Admin', range: ['11','12','18'] },
];

const screens = files.map(f => ({
  id: 's' + num(f), n: num(f), title: title(f),
  srcdoc: (SCREEN_HEAD + fs.readFileSync(path.join(SCREENS, f), 'utf8') + SCREEN_FOOT).replace(/"/g, '&quot;'),
}));
const byNum = Object.fromEntries(screens.map(s => [s.n, s]));

let nav = '';
for (const g of groups) {
  nav += `<div class="nav-group">${g.label}</div>`;
  for (const n of g.range) { const s = byNum[n]; if (s) nav += `<button class="nav-item" data-target="${s.id}"><span class="num">${s.n}</span><span class="lbl">${s.title}</span></button>`; }
}
const iframes = screens.map(s => `<iframe id="${s.id}" class="screen" srcdoc="${s.srcdoc}" title="${s.title}"></iframe>`).join('\n');

// ---- FLOW: in-screen click → navigate. Rules: {text|sel, target, contains?} ----
const NAV = { 'Library':'s03','Search':'s08','Uploads':'s04','Change requests':'s07','Registrations':'s09','Signing':'s10','Record types':'s11','Media profiles':'s12','Audit':'s18' };
const navRules = Object.entries(NAV).map(([text, target]) => ({ text, target }));
const back = t => ({ sel: '.ti-arrow-left', target: t });
const FLOW = {
  s01: [...navRules, { text:'Upload', target:'s04' }, { sel:'#grid > div', target:'s06' }],
  s03: [{ text:'Upload', target:'s04' }, { sel:'#rows > div', target:'s06' }],
  s05: [...navRules, { text:'Reviews', target:'s07' }, { sel:'#mlist > div', target:'s06' }],
  s06: [back('s03'), { text:'View change request', target:'s07' }, { text:'Open CR →', target:'s07', contains:true },
        { text:'CR-118', target:'s07', contains:true }, { text:'Signing session', target:'s10', contains:true },
        { text:'Registrations', target:'s09', contains:true }, { sel:'#versions button', target:'s21' }],
  s07: [back('s03'), { text:'Consent DA-2024-0392', target:'s06', contains:true }, { text:'v3 draft vs v2', target:'s21', contains:true }],
  s08: [{ sel:'#results > div', target:'s06' }],
  s11: [{ text:'Media profiles', target:'s12' }],
  s12: [{ text:'Record types', target:'s11' }],
  s16: [{ text:'New folder', target:'s24' }],
  s20: [back('s03'), { text:'Create item', target:'s06' }, { text:'Cancel', target:'s03' }],
  s21: [back('s06')],
  s22: [{ text:'Move here', target:'s06' }, { text:'Cancel', target:'s06' }],
  s23: [{ text:'Send for review', target:'s07' }, { text:'Cancel', target:'s06' }],
  s24: [back('s16'), { text:'Create collection', target:'s16' }, { text:'Cancel', target:'s16' }],
  s26: [back('s03')],
  s28: [back('s09'), { text:'Resubmit', target:'s09' }],
};

const dsColors = [
  ['chrome-bg','navy chrome'],['accent','primary'],['brand-cyan','cyan'],['brand-green','green'],['brand-teal','teal'],['brand-red','red'],
  ['surface-0','page'],['surface-1','card'],['surface-2','raised'],['text-primary',''],['text-secondary',''],['text-muted',''],
  ['bg-success','published'],['bg-warning','in review'],['bg-danger','failed'],['bg-info','revising'],['bg-purple','admin'],
].map(([n,l]) => `<div class="sw"><span class="chip" style="background:var(--${n})"></span><code>--${n}</code><span class="sl">${l}</span></div>`).join('');

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAGIQ Media — prototype</title>
<style id="fonts">${FONTS}</style>
<style>
${TOKENS}
*{box-sizing:border-box}
body{margin:0;font-family:var(--font-sans);background:var(--surface-0);color:var(--text-primary)}
.app{display:flex;min-height:100vh}
.side{width:250px;background:var(--surface-2);border-right:0.5px solid var(--border);flex-shrink:0;height:100vh;overflow-y:auto;position:sticky;top:0}
.brand{display:flex;align-items:center;gap:9px;padding:16px;background:var(--chrome-bg);color:#fff}
.brand .logo{width:26px;height:26px;border-radius:6px;background:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:500;font-size:13px}
.brand b{font-weight:500;font-size:15px}.brand span{font-size:11px;opacity:.6;margin-left:auto}
.nav-group{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;padding:14px 16px 5px}
.nav-item{display:flex;align-items:center;gap:9px;width:100%;text-align:left;border:none;background:transparent;color:var(--text-secondary);padding:8px 16px;font-size:13px;cursor:pointer}
.nav-item:hover{background:var(--surface-1)}
.nav-item.active{background:var(--bg-accent);color:var(--text-accent);font-weight:500}
.nav-item .num{font-size:10px;color:var(--text-muted);font-family:var(--font-mono);width:18px;flex-shrink:0}
.nav-item.active .num{color:var(--text-accent)}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.bar{display:flex;align-items:center;gap:10px;padding:12px 20px;border-bottom:0.5px solid var(--border);background:var(--surface-1);position:sticky;top:0;z-index:2}
.bar h1{font-size:15px}.bar .meta{font-size:12px;color:var(--text-muted);margin-left:auto}
.bar .hint{font-size:11px;color:var(--text-muted);display:flex;align-items:center;gap:5px}
.stage{flex:1;padding:24px;overflow:auto}
.screen{width:100%;border:0.5px solid var(--border);border-radius:12px;background:var(--surface-2);display:none}
.screen.active{display:block}
#ds{display:none;max-width:900px}#ds.active{display:block}
#ds h2{font-size:18px;margin:0 0 4px}#ds h3{font-size:14px;color:var(--text-secondary);margin:26px 0 10px}
.swgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}
.sw{display:flex;align-items:center;gap:9px;background:var(--surface-2);border:0.5px solid var(--border);border-radius:10px;padding:9px 11px}
.sw .chip{width:26px;height:26px;border-radius:7px;border:0.5px solid var(--border);flex-shrink:0}.sw code{font-size:11px}.sw .sl{font-size:10px;color:var(--text-muted);margin-left:auto}
.typerow{display:flex;align-items:baseline;gap:14px;padding:7px 0;border-bottom:0.5px solid var(--border)}.typerow .k{font-size:11px;color:var(--text-muted);width:120px;font-family:var(--font-mono)}
</style></head>
<body>
<div class="app">
  <aside class="side">
    <div class="brand"><div class="logo">M</div><b>MAGIQ Media</b><span>prototype</span></div>
    <button class="nav-item ds-link" data-target="ds"><span class="num"><i class="ti ti-palette"></i></span><span class="lbl">Design system</span></button>
    ${nav}
  </aside>
  <div class="main">
    <div class="bar"><h1 id="crumb">Design system</h1><span class="hint"><i class="ti ti-pointer"></i> in-screen buttons navigate</span><span class="meta" id="meta">Offline · Manrope · navy #1D3455</span></div>
    <div class="stage">
      <div id="ds">
        <h2>Design system</h2>
        <p style="font-size:13px;color:var(--text-secondary);margin:0">Live tokens from <code>design-system/tokens.css</code>. Brand from springbrooksoftware.com. Fully offline — fonts embedded.</p>
        <h3>Colour</h3><div class="swgrid">${dsColors}</div>
        <h3>Type scale — Manrope</h3>
        <div class="typerow"><span class="k">--fs-h1 / 22</span><span style="font-size:22px;font-weight:500">Page title</span></div>
        <div class="typerow"><span class="k">--fs-h2 / 18</span><span style="font-size:18px;font-weight:500">Section header</span></div>
        <div class="typerow"><span class="k">--fs-h3 / 14</span><span style="font-size:14px;font-weight:500">Sub-section</span></div>
        <div class="typerow"><span class="k">--fs-body / 13</span><span style="font-size:13px">Body / UI default</span></div>
        <div class="typerow"><span class="k">--fs-cap / 11</span><span style="font-size:11px;color:var(--text-secondary)">Caption / badge</span></div>
        <h3>Radii &amp; elevation</h3>
        <div style="display:flex;gap:12px;flex-wrap:wrap">
          <div style="width:90px;height:60px;background:var(--surface-2);border:0.5px solid var(--border);border-radius:var(--radius)"></div>
          <div style="width:90px;height:60px;background:var(--surface-2);border:0.5px solid var(--border);border-radius:var(--radius-card)"></div>
          <div style="width:90px;height:60px;background:var(--surface-2);border:0.5px solid var(--border);border-radius:var(--radius-card);box-shadow:var(--shadow-popover)"></div>
        </div>
        <p style="font-size:12px;color:var(--text-muted);margin-top:26px">Reference: <code>components.md</code>, <code>tokens.json</code>, <code>tailwind.tokens.cjs</code>, <code>build-sheets.md</code>.</p>
      </div>
      ${iframes}
    </div>
  </div>
</div>
<script>
const FLOW = ${JSON.stringify(FLOW)};
(function(){
  var items=[].slice.call(document.querySelectorAll('.nav-item'));
  var frames=[].slice.call(document.querySelectorAll('.screen'));
  var ds=document.getElementById('ds');
  var fontStyle=document.getElementById('fonts');
  function resize(f){try{f.style.height=(f.contentWindow.document.body.scrollHeight+2)+'px';}catch(e){}}
  function bindFlow(f){
    var rules=FLOW[f.id]; if(!rules) return;
    var doc; try{doc=f.contentWindow.document;}catch(e){return;}
    rules.forEach(function(r){
      var els=[];
      if(r.sel){ els=[].slice.call(doc.querySelectorAll(r.sel)); }
      else if(r.text){
        els=[].slice.call(doc.querySelectorAll('button,a,div,span,label,li,p,i')).filter(function(e){
          var t=(e.textContent||'').trim();
          return r.contains ? (t.indexOf(r.text)>=0 && e.children.length<=4) : t===r.text;
        });
      }
      els.forEach(function(e){ e.style.cursor='pointer'; e.addEventListener('click',function(ev){ ev.stopPropagation(); show(r.target); }); });
    });
  }
  function injectFonts(f){ try{ f.contentWindow.document.head.appendChild(fontStyle.cloneNode(true)); }catch(e){} }
  frames.forEach(function(f){ f.addEventListener('load',function(){ injectFonts(f); bindFlow(f); resize(f); }); });
  window.addEventListener('message',function(ev){ if(ev.data&&ev.data.pn) show(ev.data.pn); });

  function labelFor(target){ var it=items.filter(function(i){return i.getAttribute('data-target')===target;})[0]; if(!it)return {label:target,n:''}; return {label:(it.querySelector('.lbl')||it).textContent.trim(), n:(it.querySelector('.num')?it.querySelector('.num').textContent.trim():'')}; }
  function show(target){
    items.forEach(function(i){ i.classList.toggle('active', i.getAttribute('data-target')===target); });
    ds.classList.toggle('active', target==='ds');
    frames.forEach(function(f){ var on=f.id===target; f.classList.toggle('active',on); if(on)resize(f); });
    var L=labelFor(target);
    document.getElementById('crumb').textContent = target==='ds' ? 'Design system' : L.label;
    document.getElementById('meta').textContent = (target==='ds') ? 'Offline · Manrope · navy #1D3455' : ('Screen '+L.n+' of ${screens.length} · offline');
    if(location.hash!=='#'+target) history.replaceState(null,'','#'+target);
    window.scrollTo(0,0); var st=document.querySelector('.stage'); if(st)st.scrollTo(0,0);
  }
  items.forEach(function(i){ i.addEventListener('click',function(){ show(i.getAttribute('data-target')); }); });
  window.addEventListener('hashchange',function(){ show((location.hash||'#ds').slice(1)); });
  show((location.hash||'#ds').slice(1));
})();
</script>
</body></html>`;

fs.writeFileSync(path.join(OUT_DIR, 'index.html'), html);
console.log('wrote prototype/index.html · ' + screens.length + ' screens · offline · flow-linked · ' + Math.round(html.length/1024) + ' KB');

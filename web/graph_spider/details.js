(() => {
const ui = {
  title: document.getElementById('pTitle'),
  sub: document.getElementById('pSub'),
  bc: document.getElementById('pBC'),
  kids: document.getElementById('pKids'),
  meta: document.getElementById('pMeta'),
  btnOpen: document.getElementById('btnOpen'),
  btnFocus: document.getElementById('btnFocus'),
  btnBack: document.getElementById('btnBack'),
  btnForward: document.getElementById('btnForward'),
  btnUp: document.getElementById('btnUp'),
  btnFit: document.getElementById('btnFit'),
  btnToggleExpand: document.getElementById('btnToggleExpand'),
  btnDrillDown: document.getElementById('btnDrillDown'),
  btnPin: document.getElementById('btnPin'),
};

let bridge = null;
let nodes = [], links = [], by = new Map(), adj = new Map(), out = new Map(), inn = new Map(), deg = new Map();
let selected = null;

const ep = (z) => {
  if (z == null) return '';
  if (typeof z === 'string' || typeof z === 'number') return String(z);
  if (typeof z === 'object') {
    if (z.id != null) return String(z.id);
    if (z.key != null) return String(z.key);
    if (z.name != null) return String(z.name);
    if (z.path != null) return String(z.path);
  }
  return String(z);
};

function normalize(g) {
  const ns = (g.nodes || []).map((n, i) => ({
    id: String(n.id ?? n.key ?? i),
    label: String(n.label ?? n.name ?? n.title ?? n.path ?? n.id ?? i),
    path: String(n.path ?? n.file ?? ''),
    group: String(n.group ?? n.type ?? ''),
    meta: n.meta ?? n,
  }));
  const ls = (g.links || g.edges || []).map((e) => ({
    source: ep(e.source ?? e.from),
    target: ep(e.target ?? e.to),
  })).filter((e) => e.source && e.target);
  return { nodes: ns, links: ls };
}

function buildAdj() {
  by = new Map(nodes.map((n) => [n.id, n]));
  deg = new Map(nodes.map((n) => [n.id, 0]));
  adj = new Map(nodes.map((n) => [n.id, new Set()]));
  out = new Map(nodes.map((n) => [n.id, new Set()]));
  inn = new Map(nodes.map((n) => [n.id, new Set()]));
  for (const e of links) {
    const s = e.source, t = e.target;
    if (!by.has(s) || !by.has(t)) continue;
    deg.set(s, (deg.get(s) || 0) + 1);
    deg.set(t, (deg.get(t) || 0) + 1);
    adj.get(s).add(t); adj.get(t).add(s);
    out.get(s).add(t); inn.get(t).add(s);
  }
}

function setGraph(g) {
  const norm = normalize(g);
  nodes = norm.nodes;
  links = norm.links;
  buildAdj();
  render(selected);
}

function send(cmd, arg = '') {
  if (bridge && typeof bridge.sendCommand === 'function') {
    bridge.sendCommand(String(cmd || ''), String(arg || ''));
  }
}

function requestDetail(id) {
  if (!bridge || typeof bridge.requestNodeDetailJson !== 'function') return null;
  try {
    const s = bridge.requestNodeDetailJson(String(id));
    if (!s) return null;
    return JSON.parse(s);
  } catch (e) {
    return null;
  }
}

function render(nodeId) {
  selected = nodeId || selected;
  const n = by.get(String(selected));
  if (!n) {
    ui.title.textContent = 'No selection';
    ui.sub.textContent = '';
    ui.bc.innerHTML = '';
    ui.kids.innerHTML = '<div class="panel-item">(select a node)</div>';
    ui.meta.textContent = '';
    return;
  }
  ui.title.textContent = n.label || n.id;
  ui.sub.textContent = `${n.path || n.group || n.id}`;

  ui.bc.innerHTML = '';
  const parent = Array.from(inn.get(n.id) || []).find((id) => String(id).startsWith('dir:'));
  if (parent) {
    const el = document.createElement('div');
    el.className = 'bc-item';
    el.textContent = by.get(parent)?.label || parent;
    el.onclick = () => send('focus', parent);
    ui.bc.appendChild(el);
  } else {
    const root = document.createElement('div');
    root.className = 'bc-item';
    root.textContent = 'overview';
    root.onclick = () => send('overview', '');
    ui.bc.appendChild(root);
  }

  ui.kids.innerHTML = '';
  const neigh = adj.get(n.id) || new Set();
  const items = [...neigh].map((id) => by.get(id)).filter(Boolean).slice(0, 80);
  if (!items.length) {
    const el = document.createElement('div');
    el.className = 'panel-item';
    el.textContent = '(no neighbors)';
    ui.kids.appendChild(el);
  } else {
    for (const m of items) {
      const el = document.createElement('div');
      el.className = 'panel-item';
      const t = document.createElement('div');
      t.className = 'panel-item-title';
      t.textContent = m.label || m.id;
      const s = document.createElement('div');
      s.className = 'panel-item-sub';
      s.textContent = m.path || m.group || m.id;
      el.appendChild(t);
      el.appendChild(s);
      el.onclick = () => send('focus', m.id);
      ui.kids.appendChild(el);
    }
  }

  const detail = requestDetail(n.id);
  try {
    const meta = detail || n.meta || {};
    const slim = {};
    for (const k of Object.keys(meta).slice(0, 80)) {
      const v = meta[k];
      slim[k] = typeof v === 'string' && v.length > 320 ? `${v.slice(0, 320)}…` : v;
    }
    ui.meta.textContent = JSON.stringify({
      id: n.id,
      label: n.label,
      path: n.path,
      group: n.group,
      degree: deg.get(n.id) || 0,
      meta: slim,
    }, null, 2);
  } catch (e) {
    ui.meta.textContent = '';
  }
}

function bindButtons() {
  if (ui.btnOpen) ui.btnOpen.onclick = () => { if (!selected) return; if (bridge && typeof bridge.openNode === 'function') { bridge.openNode(String(selected)); } else { send('focus', selected); } };
  if (ui.btnFocus) ui.btnFocus.onclick = () => send('focus', selected || '');
  if (ui.btnBack) ui.btnBack.onclick = () => send('back', '');
  if (ui.btnForward) ui.btnForward.onclick = () => send('forward', '');
  if (ui.btnUp) ui.btnUp.onclick = () => send('up', '');
  if (ui.btnFit) ui.btnFit.onclick = () => send('fit', '');
  if (ui.btnToggleExpand) ui.btnToggleExpand.onclick = () => send('toggleExpand', selected || '');
  if (ui.btnDrillDown) ui.btnDrillDown.onclick = () => send('drillDown', selected || '');
  if (ui.btnPin) ui.btnPin.onclick = () => send('pinToggle', selected || '');
}

function attachBridge(obj) {
  bridge = obj;
  bindButtons();
  if (bridge.graphChanged && typeof bridge.graphChanged.connect === 'function') {
    bridge.graphChanged.connect((g) => {
      try {
        if (typeof g === 'string') g = JSON.parse(g);
        setGraph(g);
      } catch (e) { console.error(e); }
    });
  }
  if (bridge.selectedNodeChanged && typeof bridge.selectedNodeChanged.connect === 'function') {
    bridge.selectedNodeChanged.connect((id) => { render(id); });
  }
  if (bridge.toast && typeof bridge.toast.connect === 'function') {
    bridge.toast.connect((msg) => { console.log('[details] toast', msg); });
  }
  if (typeof bridge.getGraphJson === 'function') {
    try {
      const js = bridge.getGraphJson();
      if (js) {
        const g = typeof js === 'string' ? JSON.parse(js) : js;
        setGraph(g);
      }
    } catch (e) { console.warn('getGraphJson failed', e); }
  }
  if (typeof bridge.requestGraph === 'function') {
    try {
      bridge.requestGraph('Pipeline', '', (js) => {
        if (!js) return;
        try { setGraph(typeof js === 'string' ? JSON.parse(js) : js); } catch (e) { console.error(e); }
      });
    } catch (e) {}
  }
}

function init() {
  if (!window.qt || !window.qt.webChannelTransport) {
    setGraph({ nodes: [], links: [] });
    return;
  }
  new QWebChannel(window.qt.webChannelTransport, (ch) => {
    const b = ch.objects.bridge || ch.objects.GraphBridge || ch.objects.sddai || ch.objects.app || null;
    if (!b) { console.warn('bridge missing'); return; }
    attachBridge(b);
  });
}

init();
})();

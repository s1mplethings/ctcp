/* SDDAI Spider Graph (Canvas) — no external deps
   - Obsidian-ish feel: glow nodes, thin edges, zoom/pan, drag nodes, search, focus
   - Qt integration (optional): QWebChannel object named `bridge` with:
        - optional slot: getGraphJson() -> QString (JSON)
        - optional slot: openNode(QString id)
        - optional signal: graphJson(QString json) OR graphJsonChanged(QString json)
     Fallback: loads ./demo_graph.json
*/
(() => {
  const canvas = document.getElementById('c');
  const ctx = canvas.getContext('2d', { alpha: false });

  const ui = {
    search: document.getElementById('search'),
    results: document.getElementById('results'),
    btnFit: document.getElementById('btnFit'),
    btnPause: document.getElementById('btnPause'),
    btnReheat: document.getElementById('btnReheat'),
    panel: document.getElementById('panel'),
    pTitle: document.getElementById('pTitle'),
    pSub: document.getElementById('pSub'),
    pMeta: document.getElementById('pMeta'),
    btnOpen: document.getElementById('btnOpen'),
    btnPin: document.getElementById('btnPin'),
    btnClose: document.getElementById('btnClose'),
    toast: document.getElementById('toast'),
  };

  const DPR = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
  function resize() {
    const r = canvas.getBoundingClientRect();
    canvas.width = Math.floor(r.width * DPR);
    canvas.height = Math.floor(r.height * DPR);
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  // View transform
  const view = { x: 0, y: 0, k: 1 };
  function screenToWorld(sx, sy) {
    return { x: (sx * DPR - view.x) / view.k, y: (sy * DPR - view.y) / view.k };
  }
  function worldToScreen(wx, wy) {
    return { x: wx * view.k + view.x, y: wy * view.k + view.y };
  }

  // Graph data
  let nodes = [];
  let links = [];
  let nodeById = new Map();
  let running = true;
  let tickEnergy = 1.0;

  // Interaction
  let draggingCanvas = false;
  let dragNode = null;
  let dragStart = { x: 0, y: 0 };
  let viewStart = { x: 0, y: 0 };
  let lastPointer = { x: 0, y: 0 };
  let moved = false;

  let hoverId = null;
  let selectedId = null;

  function toast(msg) {
    ui.toast.textContent = msg;
    ui.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => ui.toast.classList.add('hidden'), 1400);
  }

  function normalizeGraph(g) {
    const ns = (g.nodes || []).map((n, i) => ({
      id: String(n.id ?? i),
      label: String(n.label ?? n.name ?? n.path ?? n.id ?? i),
      path: n.path ?? n.file ?? n.label ?? '',
      group: n.group ?? n.type ?? '',
      meta: n.meta ?? n,
      x: (n.x ?? (Math.random() - 0.5) * 800),
      y: (n.y ?? (Math.random() - 0.5) * 600),
      vx: 0, vy: 0,
      fx: null, fy: null,
      r: n.r ?? 4,
      color: n.color ?? null,
    }));

    const ls = (g.links || g.edges || []).map((e) => ({
      source: String(e.source ?? e.from),
      target: String(e.target ?? e.to),
      w: Number(e.w ?? e.weight ?? 1),
    }));

    // ensure nodes exist
    const ids = new Set(ns.map(n => n.id));
    for (const e of ls) {
      if (!ids.has(e.source)) {
        ns.push({ id: e.source, label: e.source, path: '', group: '', meta: {}, x:(Math.random()-0.5)*800, y:(Math.random()-0.5)*600, vx:0, vy:0, fx:null, fy:null, r:4, color:null });
        ids.add(e.source);
      }
      if (!ids.has(e.target)) {
        ns.push({ id: e.target, label: e.target, path: '', group: '', meta: {}, x:(Math.random()-0.5)*800, y:(Math.random()-0.5)*600, vx:0, vy:0, fx:null, fy:null, r:4, color:null });
        ids.add(e.target);
      }
    }

    return { nodes: ns, links: ls };
  }

  function setGraph(g) {
    const norm = normalizeGraph(g);
    nodes = norm.nodes;
    links = norm.links;
    nodeById = new Map(nodes.map(n => [n.id, n]));

    // center: pick best hub as seed
    const deg = new Map(nodes.map(n => [n.id, 0]));
    for (const e of links) {
      deg.set(e.source, (deg.get(e.source) || 0) + 1);
      deg.set(e.target, (deg.get(e.target) || 0) + 1);
    }
    let hub = nodes[0];
    for (const n of nodes) if ((deg.get(n.id) || 0) > (deg.get(hub.id) || 0)) hub = n;

    if (hub) {
      hub.x = 0; hub.y = 0;
      hub.fx = 0; hub.fy = 0;
      setTimeout(() => { hub.fx = null; hub.fy = null; }, 650);
    }

    selectedId = null;
    hoverId = null;
    tickEnergy = 1.0;
    fitToScreen();
    toast(`Loaded: ${nodes.length} nodes / ${links.length} links`);
  }

  // Physics parameters
  const params = {
    linkDist: 55,
    linkK: 0.010,
    repulsion: 1800,     // higher = more spread
    repulsionMax: 8,     // clamp
    centerK: 0.0020,
    damping: 0.86,
    collide: 6.5,
    step: 1.0,
  };

  function buildGrid(cellSize) {
    const grid = new Map();
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      const cx = Math.floor(n.x / cellSize);
      const cy = Math.floor(n.y / cellSize);
      const key = cx + ',' + cy;
      let arr = grid.get(key);
      if (!arr) grid.set(key, arr = []);
      arr.push(i);
    }
    return { grid, cellSize };
  }

  function applyForces() {
    if (!running) return;

    const cellSize = 110;
    const { grid } = buildGrid(cellSize);

    // repulsion + collision in local neighborhood
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      if (a.fx != null) { a.x = a.fx; a.vx = 0; }
      if (a.fy != null) { a.y = a.fy; a.vy = 0; }

      const cx = Math.floor(a.x / cellSize);
      const cy = Math.floor(a.y / cellSize);

      for (let ox = -1; ox <= 1; ox++) {
        for (let oy = -1; oy <= 1; oy++) {
          const key = (cx + ox) + ',' + (cy + oy);
          const arr = grid.get(key);
          if (!arr) continue;
          for (const j of arr) {
            if (j <= i) continue;
            const b = nodes[j];
            let dx = a.x - b.x;
            let dy = a.y - b.y;
            let d2 = dx*dx + dy*dy + 0.01;
            let d = Math.sqrt(d2);

            // collision
            const minD = params.collide + a.r + b.r;
            if (d < minD) {
              const push = (minD - d) * 0.05;
              const nx = dx / d, ny = dy / d;
              a.vx += nx * push;
              a.vy += ny * push;
              b.vx -= nx * push;
              b.vy -= ny * push;
            }

            // repulsion
            const f = Math.min(params.repulsionMax, params.repulsion / d2);
            const nx = dx / d, ny = dy / d;
            a.vx += nx * f;
            a.vy += ny * f;
            b.vx -= nx * f;
            b.vy -= ny * f;
          }
        }
      }
    }

    // link springs
    for (const e of links) {
      const a = nodeById.get(e.source);
      const b = nodeById.get(e.target);
      if (!a || !b) continue;
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let d = Math.sqrt(dx*dx + dy*dy) + 1e-6;
      const desired = params.linkDist;
      const k = params.linkK * (e.w || 1);
      const f = (d - desired) * k;
      const nx = dx / d, ny = dy / d;
      a.vx += nx * f;
      a.vy += ny * f;
      b.vx -= nx * f;
      b.vy -= ny * f;
    }

    // center + damping + integrate
    for (const n of nodes) {
      n.vx += (-n.x) * params.centerK;
      n.vy += (-n.y) * params.centerK;

      n.vx *= params.damping;
      n.vy *= params.damping;

      n.x += n.vx * params.step * (0.25 + tickEnergy);
      n.y += n.vy * params.step * (0.25 + tickEnergy);
    }

    tickEnergy *= 0.985;
    if (tickEnergy < 0.02) tickEnergy = 0.02;
  }

  function pickNode(sx, sy) {
    const p = screenToWorld(sx, sy);
    const r = 10 / view.k;
    let best = null, bestD2 = Infinity;
    for (const n of nodes) {
      const dx = n.x - p.x;
      const dy = n.y - p.y;
      const d2 = dx*dx + dy*dy;
      const rr = (n.r + r);
      if (d2 < rr*rr && d2 < bestD2) {
        best = n; bestD2 = d2;
      }
    }
    return best;
  }

  function fitToScreen(pad = 70) {
    if (!nodes.length) return;
    let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    for (const n of nodes) {
      minx = Math.min(minx, n.x);
      miny = Math.min(miny, n.y);
      maxx = Math.max(maxx, n.x);
      maxy = Math.max(maxy, n.y);
    }
    const w = canvas.width, h = canvas.height;
    const gw = Math.max(1, (maxx - minx));
    const gh = Math.max(1, (maxy - miny));
    const k = Math.min((w - pad*DPR) / gw, (h - pad*DPR) / gh);
    view.k = Math.max(0.25*DPR, Math.min(2.4*DPR, k));
    const cx = (minx + maxx) * 0.5;
    const cy = (miny + maxy) * 0.5;
    view.x = w*0.5 - cx*view.k;
    view.y = h*0.5 - cy*view.k;
  }

  function focusNode(id) {
    const n = nodeById.get(String(id));
    if (!n) return;
    selectedId = n.id;
    tickEnergy = 1.0;
    const w = canvas.width, h = canvas.height;
    const targetX = w*0.5 - n.x*view.k;
    const targetY = h*0.5 - n.y*view.k;
    const steps = 16;
    const sx0 = view.x, sy0 = view.y;
    let t = 0;
    const anim = () => {
      t++;
      const a = t/steps;
      const ease = a<1 ? (1 - Math.pow(1-a, 3)) : 1;
      view.x = sx0 + (targetX - sx0) * ease;
      view.y = sy0 + (targetY - sy0) * ease;
      if (t < steps) requestAnimationFrame(anim);
    };
    requestAnimationFrame(anim);
    showPanel(n);
  }

  function showPanel(n) {
    ui.panel.classList.remove('hidden');
    ui.pTitle.textContent = n.label;
    ui.pSub.textContent = n.path || n.group || n.id;
    ui.pMeta.textContent = '';
    try {
      ui.pMeta.textContent = JSON.stringify(n.meta, null, 2);
    } catch {
      ui.pMeta.textContent = String(n.meta || '');
    }
    ui.btnPin.textContent = (n.fx != null || n.fy != null) ? 'Unpin' : 'Pin';
  }

  function hidePanel() {
    ui.panel.classList.add('hidden');
  }

  function draw() {
    applyForces();

    const w = canvas.width, h = canvas.height;

    ctx.save();
    ctx.fillStyle = '#0b0f14';
    ctx.fillRect(0,0,w,h);

    const g = ctx.createRadialGradient(w*0.35, h*0.25, 40, w*0.35, h*0.25, Math.max(w,h));
    g.addColorStop(0, '#101a27');
    g.addColorStop(1, '#0b0f14');
    ctx.fillStyle = g;
    ctx.fillRect(0,0,w,h);

    ctx.translate(view.x, view.y);
    ctx.scale(view.k, view.k);

    ctx.lineWidth = 1 / view.k;
    ctx.globalCompositeOperation = 'lighter';
    for (const e of links) {
      const a = nodeById.get(e.source);
      const b = nodeById.get(e.target);
      if (!a || !b) continue;
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx*dx + dy*dy);
      const alpha = Math.max(0.02, Math.min(0.22, 140 / (d + 40) * 0.18));
      ctx.strokeStyle = `rgba(190,255,235,${alpha})`;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    for (const n of nodes) {
      const isHover = (n.id === hoverId);
      const isSel = (n.id === selectedId);

      const baseR = n.r + (isSel ? 3 : isHover ? 2 : 0);
      const glow = isSel ? 14 : isHover ? 10 : 8;

      ctx.save();
      ctx.shadowColor = isSel ? 'rgba(112,255,210,.45)' : 'rgba(112,255,210,.25)';
      ctx.shadowBlur = glow;
      ctx.fillStyle = n.color || (n.group ? 'rgba(150,200,255,.90)' : 'rgba(112,255,210,.92)');
      ctx.beginPath();
      ctx.arc(n.x, n.y, baseR, 0, Math.PI*2);
      ctx.fill();
      ctx.restore();

      if (isSel) {
        ctx.strokeStyle = 'rgba(112,255,210,.45)';
        ctx.lineWidth = 1.2 / view.k;
        ctx.beginPath();
        ctx.arc(n.x, n.y, baseR + 6, 0, Math.PI*2);
        ctx.stroke();
      }
    }

    const showLabels = view.k > 1.25 * DPR;
    ctx.globalCompositeOperation = 'source-over';
    ctx.font = `${12 / view.k}px ui-sans-serif, system-ui`;
    ctx.textBaseline = 'middle';
    for (const n of nodes) {
      if (!showLabels && n.id !== hoverId && n.id !== selectedId) continue;
      const label = n.label;
      if (!label) continue;
      const x = n.x + (n.r + 8) / view.k;
      const y = n.y;
      ctx.fillStyle = (n.id === selectedId) ? 'rgba(220,245,255,.95)' : 'rgba(210,230,250,.82)';
      ctx.fillText(label, x, y);
    }

    ctx.restore();
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);

  function onPointerDown(ev) {
    const rect = canvas.getBoundingClientRect();
    const sx = ev.clientX - rect.left;
    const sy = ev.clientY - rect.top;
    lastPointer = { x: sx, y: sy };
    moved = false;

    const n = pickNode(sx, sy);
    if (n) {
      dragNode = n;
      dragNode.fx = dragNode.x;
      dragNode.fy = dragNode.y;
      dragStart = { x: sx, y: sy };
      tickEnergy = 1.0;
    } else {
      draggingCanvas = true;
      dragStart = { x: sx, y: sy };
      viewStart = { x: view.x, y: view.y };
    }
    canvas.setPointerCapture(ev.pointerId);
  }

  function onPointerMove(ev) {
    const rect = canvas.getBoundingClientRect();
    const sx = ev.clientX - rect.left;
    const sy = ev.clientY - rect.top;

    const dx = sx - lastPointer.x;
    const dy = sy - lastPointer.y;
    if (Math.abs(dx) + Math.abs(dy) > 1) moved = true;
    lastPointer = { x: sx, y: sy };

    if (dragNode) {
      const p = screenToWorld(sx, sy);
      dragNode.fx = p.x;
      dragNode.fy = p.y;
      hoverId = dragNode.id;
      return;
    }

    if (draggingCanvas) {
      view.x = viewStart.x + (sx - dragStart.x) * DPR;
      view.y = viewStart.y + (sy - dragStart.y) * DPR;
      return;
    }

    const n = pickNode(sx, sy);
    hoverId = n ? n.id : null;
  }

  function onPointerUp(ev) {
    const rect = canvas.getBoundingClientRect();
    const sx = ev.clientX - rect.left;
    const sy = ev.clientY - rect.top;

    if (dragNode) {
      if (!moved) {
        selectNode(dragNode.id);
      }
      dragNode.fx = null;
      dragNode.fy = null;
      dragNode = null;
    } else if (!moved) {
      const n = pickNode(sx, sy);
      if (n) selectNode(n.id);
      else { selectedId = null; hidePanel(); }
    }

    draggingCanvas = false;
    canvas.releasePointerCapture(ev.pointerId);
  }

  function onWheel(ev) {
    ev.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const sx = ev.clientX - rect.left;
    const sy = ev.clientY - rect.top;
    const p0 = screenToWorld(sx, sy);

    const delta = Math.sign(ev.deltaY);
    const factor = Math.pow(1.12, -delta);
    const k1 = Math.max(0.20*DPR, Math.min(5.0*DPR, view.k * factor));
    view.k = k1;

    const p1 = worldToScreen(p0.x, p0.y);
    view.x += (sx * DPR - p1.x);
    view.y += (sy * DPR - p1.y);
  }

  canvas.addEventListener('pointerdown', onPointerDown);
  canvas.addEventListener('pointermove', onPointerMove);
  canvas.addEventListener('pointerup', onPointerUp);
  canvas.addEventListener('wheel', onWheel, { passive: false });

  function selectNode(id) {
    const n = nodeById.get(String(id));
    if (!n) return;
    selectedId = n.id;
    showPanel(n);
    tickEnergy = 1.0;
  }

  ui.btnFit.addEventListener('click', () => { fitToScreen(); toast('Fit'); });
  ui.btnPause.addEventListener('click', () => {
    running = !running;
    ui.btnPause.textContent = running ? 'Pause' : 'Resume';
    toast(running ? 'Running' : 'Paused');
  });
  ui.btnReheat.addEventListener('click', () => { tickEnergy = 1.0; toast('Reheat'); });

  ui.btnClose.addEventListener('click', hidePanel);
  ui.btnOpen.addEventListener('click', () => {
    if (!selectedId) return;
    openNode(selectedId);
  });
  ui.btnPin.addEventListener('click', () => {
    if (!selectedId) return;
    const n = nodeById.get(selectedId);
    if (!n) return;
    if (n.fx != null || n.fy != null) { n.fx = null; n.fy = null; ui.btnPin.textContent='Pin'; toast('Unpinned'); }
    else { n.fx = n.x; n.fy = n.y; ui.btnPin.textContent='Unpin'; toast('Pinned'); }
  });

  function renderResults(items) {
    if (!items.length) { ui.results.classList.add('hidden'); ui.results.innerHTML=''; return; }
    ui.results.classList.remove('hidden');
    ui.results.innerHTML = items.slice(0, 50).map(n => {
      const sub = (n.path || n.group || '').replace(/</g,'&lt;');
      return `<div class="result-item" data-id="${n.id}">
        <div class="result-title">${escapeHtml(n.label)}</div>
        <div class="result-sub">${escapeHtml(sub)}</div>
      </div>`;
    }).join('');
    for (const el of ui.results.querySelectorAll('.result-item')) {
      el.addEventListener('click', () => {
        ui.results.classList.add('hidden');
        focusNode(el.getAttribute('data-id'));
      });
    }
  }
  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

  ui.search.addEventListener('input', () => {
    const q = ui.search.value.trim().toLowerCase();
    if (!q) { renderResults([]); return; }
    const hits = [];
    for (const n of nodes) {
      const hay = (n.label + ' ' + (n.path||'')).toLowerCase();
      if (hay.includes(q)) hits.push(n);
      if (hits.length >= 80) break;
    }
    renderResults(hits);
  });
  document.addEventListener('pointerdown', (e) => {
    if (e.target === ui.search || ui.results.contains(e.target)) return;
    ui.results.classList.add('hidden');
  });

  // Qt bridge
  let qtBridge = null;
  function openNode(id) {
    const n = nodeById.get(String(id));
    if (!n) return;
    if (qtBridge && typeof qtBridge.openNode === 'function') {
      qtBridge.openNode(String(id));
      return;
    }
    if (qtBridge && typeof qtBridge.openPath === 'function' && n.path) {
      qtBridge.openPath(String(n.path));
      return;
    }
    toast('No bridge: open disabled');
    console.log('[SDDAI] openNode:', id, n);
  }

  function tryLoadFromBridge() {
    if (!window.qt || !window.qt.webChannelTransport) return false;
    try {
      new QWebChannel(window.qt.webChannelTransport, (channel) => {
        qtBridge = channel.objects.bridge || channel.objects.sddai || channel.objects.app || null;
        if (!qtBridge) {
          toast('QWebChannel ok, but no bridge object');
          return;
        }

        if (typeof qtBridge.getGraphJson === 'function') {
          const jsonStr = qtBridge.getGraphJson();
          if (jsonStr) {
            setGraph(JSON.parse(jsonStr));
            return;
          }
        }

        const sigs = ['graphJson', 'graphJsonChanged', 'graphReady', 'graphUpdated'];
        for (const s of sigs) {
          if (qtBridge[s] && typeof qtBridge[s].connect === 'function') {
            qtBridge[s].connect((jsonStr) => {
              try { setGraph(JSON.parse(jsonStr)); } catch (e) { console.error(e); }
            });
          }
        }

        if (typeof qtBridge.requestGraph === 'function') qtBridge.requestGraph();
        toast('Bridge connected');
      });
      return true;
    } catch (e) {
      console.warn('[SDDAI] QWebChannel init failed', e);
      return false;
    }
  }

  async function loadDemo() {
    try {
      const r = await fetch('./demo_graph.json', { cache: 'no-store' });
      const g = await r.json();
      setGraph(g);
    } catch (e) {
      console.error(e);
      setGraph({
        nodes: [{id:'A',label:'Demo A'},{id:'B',label:'Demo B'},{id:'C',label:'Demo C'}],
        links: [{source:'A',target:'B'},{source:'A',target:'C'}]
      });
    }
  }

  window.SDDAI_GRAPH = {
    setData: (g) => setGraph(g),
    setJson: (jsonStr) => setGraph(JSON.parse(jsonStr)),
    focus: (id) => focusNode(id),
    fit: () => fitToScreen(),
  };

  if (!tryLoadFromBridge()) loadDemo();
})();

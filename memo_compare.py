#!/usr/bin/env python3
# memo_compare.py — 有記憶的心 vs 沒有記憶的心
#
# fib(8) 兩種計算方式並排：
# 左：樸素遞迴（67 節點，不斷重複）
# 右：有記憶的遞迴（節點少，快速落定）
# 同樣的問題，完全不同的形狀。

import json, os, webbrowser, colorsys

# ── 建立兩棵樹 ────────────────────────────────────────────────

# --- 樸素 fib ---
naive_nodes  = []
naive_events = []

def build_naive(n, parent_id=None):
    nid  = len(naive_nodes)
    node = {'id': nid, 'n': n, 'parent': parent_id,
            'children': [], 'x': 0.0, 'y': 0, 'value': None, 'cached': False}
    naive_nodes.append(node)
    if parent_id is not None:
        naive_nodes[parent_id]['children'].append(nid)
    naive_events.append({'type': 'call', 'id': nid, 'cached': False})
    result = n if n < 2 else (build_naive(n-1, nid) + build_naive(n-2, nid))
    node['value'] = result
    naive_events.append({'type': 'return', 'id': nid, 'value': result, 'cached': False})
    return result

build_naive(8)

# --- 記憶化 fib ---
memo_nodes  = []
memo_events = []
_cache = {}

def build_memo(n, parent_id=None):
    nid      = len(memo_nodes)
    is_hit   = n in _cache
    node     = {'id': nid, 'n': n, 'parent': parent_id,
                'children': [], 'x': 0.0, 'y': 0, 'value': None, 'cached': is_hit}
    memo_nodes.append(node)
    if parent_id is not None:
        memo_nodes[parent_id]['children'].append(nid)
    memo_events.append({'type': 'call', 'id': nid, 'cached': is_hit})
    if is_hit:
        result = _cache[n]
    elif n < 2:
        result = n
        _cache[n] = result
    else:
        result = build_memo(n-1, nid) + build_memo(n-2, nid)
        _cache[n] = result
    node['value'] = result
    memo_events.append({'type': 'return', 'id': nid, 'value': result, 'cached': is_hit})
    return result

build_memo(8)

print(f'樸素 fib(8) : {len(naive_nodes)} 節點，{len(naive_events)} 事件')
print(f'記憶化 fib(8): {len(memo_nodes)} 節點，{len(memo_events)} 事件')

# ── 佈局 ──────────────────────────────────────────────────────

def do_layout(nodes):
    xc = [0]
    def lay(nid, depth):
        node = nodes[nid]
        node['y'] = depth
        if not node['children']:
            node['x'] = float(xc[0]); xc[0] += 1
        else:
            for cid in node['children']: lay(cid, depth + 1)
            xs = [nodes[c]['x'] for c in node['children']]
            node['x'] = sum(xs) / len(xs)
    lay(0, 0)
    return max(n['x'] for n in nodes), max(n['y'] for n in nodes)

naive_mx, naive_md = do_layout(naive_nodes)
memo_mx,  memo_md  = do_layout(memo_nodes)

# ── 顏色 / 音高 ───────────────────────────────────────────────

def n_color(n, cached=False, alpha=1.0):
    if cached:
        r, g, b = 0.3, 0.3, 0.45
        return f'rgba({int(r*255)},{int(g*255)},{int(b*255)},{alpha:.2f})'
    t   = n / 8.0
    hue = 0.55 - t * 0.45
    r, g, b = colorsys.hsv_to_rgb(hue, 0.75 + t * 0.15, 0.85 + t * 0.1)
    if alpha < 1.0:
        return f'rgba({int(r*255)},{int(g*255)},{int(b*255)},{alpha:.2f})'
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

PENTA     = [0, 2, 4, 7, 9]
MIDI_BASE = [60 + o*12 + s for o in range(3) for s in PENTA]

def n_freq(n, cached=False):
    idx  = int((1 - n/8) * (len(MIDI_BASE) - 1))
    midi = MIDI_BASE[idx]
    f    = 440 * (2 ** ((midi - 69) / 12))
    return round(f * (0.5 if cached else 1.0), 2)

for node in naive_nodes:
    node['color'] = n_color(node['n'])
    node['color_dim'] = n_color(node['n'], alpha=0.22)
    node['freq'] = n_freq(node['n'])

for node in memo_nodes:
    node['color'] = n_color(node['n'], node['cached'])
    node['color_dim'] = n_color(node['n'], node['cached'], 0.22)
    node['freq'] = n_freq(node['n'], node['cached'])

NAIVE_JS  = json.dumps(naive_nodes)
MEMO_JS   = json.dumps(memo_nodes)
NEVT_JS   = json.dumps(naive_events)
MEVT_JS   = json.dumps(memo_events)

# ── HTML ──────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>有記憶 vs 沒有記憶</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #04040d;
  font-family: 'Courier New', monospace;
  color: #556;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 34px 20px;
}}
h1 {{
  font-size: 11px;
  color: #334;
  letter-spacing: 5px;
  text-transform: uppercase;
  margin-bottom: 4px;
}}
.sub {{
  font-size: 9px;
  color: #1c1c2c;
  margin-bottom: 22px;
  letter-spacing: 1px;
}}
.stage {{
  display: flex;
  gap: 0;
  width: 1240px;
}}
.side {{
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}}
.side-label {{
  font-size: 9px;
  letter-spacing: 3px;
  margin-bottom: 6px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}}
.side-label.naive {{ color: #445; }}
.side-label.memo  {{ color: #2e4a3e; }}
.node-count {{
  font-size: 18px;
  font-weight: bold;
  transition: color 0.2s;
}}
.count-naive {{ color: #223; }}
.count-memo  {{ color: #193028; }}
canvas {{ display: block; border: 1px solid #0c0c18; border-radius: 2px; }}
.divider {{
  width: 1px;
  background: #0f0f20;
  align-self: stretch;
  margin: 0 4px;
}}
.controls {{
  display: flex;
  gap: 14px;
  align-items: center;
  margin: 16px 0 8px;
}}
button {{
  background: #0c0c1c;
  color: #556;
  border: 1px solid #181830;
  padding: 8px 22px;
  cursor: pointer;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  letter-spacing: 1px;
  transition: all 0.15s;
}}
button:hover {{ background: #141428; color: #88a; }}
button.playing {{ color: #6cf; border-color: #248; }}
label {{ font-size: 10px; color: #2a2a3c; }}
input[type=range] {{ width: 80px; accent-color: #336; }}
.spd-v {{ font-size: 10px; color: #334; }}
.summary {{
  font-size: 10px;
  color: #1e1e30;
  margin-top: 10px;
  letter-spacing: 1px;
  transition: color 0.3s;
  height: 14px;
  text-align: center;
}}
.summary.done {{ color: #445; }}
</style>
</head>
<body>

<h1>有記憶的心 vs 沒有記憶的心</h1>
<div class="sub">fib(8) · 同樣的問題，不同的形狀</div>

<div class="stage">
  <div class="side">
    <div class="side-label naive">
      沒有記憶
      <span class="node-count count-naive" id="naive-count">0</span>
      <span style="font-size:9px;color:#223">/ {len(naive_nodes)}</span>
    </div>
    <canvas id="naive-cv" width="620" height="480"></canvas>
  </div>
  <div class="divider"></div>
  <div class="side">
    <div class="side-label memo">
      有記憶
      <span class="node-count count-memo" id="memo-count">0</span>
      <span style="font-size:9px;color:#193028">/ {len(memo_nodes)}</span>
    </div>
    <canvas id="memo-cv" width="620" height="480"></canvas>
  </div>
</div>

<div class="controls">
  <button id="btn" onclick="togglePlay()">▶ 播放</button>
  <label>速度</label>
  <input type="range" id="spd" min="20" max="400" value="70"
         oninput="document.getElementById('spd-v').textContent=this.value+'ms'">
  <span class="spd-v" id="spd-v">70ms</span>
  <button onclick="doReset()">↺ 重置</button>
</div>
<div class="summary" id="summary"></div>

<script>
const NAIVE_N  = {NAIVE_JS};
const MEMO_N   = {MEMO_JS};
const NAIVE_E  = {NEVT_JS};
const MEMO_E   = {MEVT_JS};
const NAIVE_MX = {naive_mx:.1f};
const MEMO_MX  = {max(memo_mx, 1.0):.1f};
const NAIVE_MD = {naive_md};
const MEMO_MD  = {memo_md};

// ── 畫布設定 ────────────────────────────────────────────────
const W = 620, H = 480;
const PAD = {{ l:30, r:20, t:44, b:20 }};
const R   = 11;

function nx(node, mx) {{
  return PAD.l + (node.x / Math.max(mx,1)) * (W - PAD.l - PAD.r);
}}
function ny(node, md) {{
  return PAD.t + (node.y / Math.max(md,1)) * (H - PAD.t - PAD.b);
}}

// ── 狀態 ────────────────────────────────────────────────────
const nVis = new Set(), mVis = new Set();
const nRet = new Set(), mRet = new Set();
const nGlo = new Map(), mGlo = new Map();

function drawTree(cvId, nodes, events, vis, ret, glo, mx, md, count) {{
  const cv  = document.getElementById(cvId);
  const ctx = cv.getContext('2d');

  ctx.fillStyle = '#04040d';
  ctx.fillRect(0, 0, W, H);

  // 邊
  vis.forEach(id => {{
    const n = nodes[id];
    if (n.parent === null) return;
    const p = nodes[n.parent];
    if (!vis.has(p.id)) return;
    ctx.beginPath();
    ctx.moveTo(nx(p, mx), ny(p, md));
    ctx.lineTo(nx(n, mx), ny(n, md));
    ctx.strokeStyle = n.cached ? '#111120' : (ret.has(id) ? n.color + '35' : '#151525');
    ctx.setLineDash(n.cached ? [3,3] : []);
    ctx.lineWidth = 0.8;
    ctx.stroke();
    ctx.setLineDash([]);
  }});

  // 節點
  vis.forEach(id => {{
    const n   = nodes[id];
    const x   = nx(n, mx), y = ny(n, md);
    const isR = ret.has(id);
    const gl  = glo.get(id) || 0;

    if (gl > 0) {{ ctx.shadowColor = n.color; ctx.shadowBlur = 20 * gl; }}

    ctx.beginPath();
    ctx.arc(x, y, R, 0, Math.PI * 2);
    ctx.fillStyle   = isR ? n.color : n.color_dim;
    ctx.fill();

    if (n.cached) {{
      ctx.strokeStyle = '#2a2a44';
      ctx.setLineDash([2,2]);
    }} else {{
      ctx.strokeStyle = isR ? n.color + 'bb' : '#1a1a2e';
      ctx.setLineDash([]);
    }}
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.shadowBlur = 0;

    ctx.fillStyle = isR ? (n.cached ? '#556' : '#fff') : '#334';
    ctx.font = `${{isR && !n.cached ? 'bold ' : ''}}9px monospace`;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(n.n, x, y);
  }});

  // 節點計數
  document.getElementById(cvId === 'naive-cv' ? 'naive-count' : 'memo-count')
          .textContent = vis.size;
}}

// ── 音訊 ────────────────────────────────────────────────────
let ac = null;
function getAC() {{
  if (!ac) ac = new (window.AudioContext || window.webkitAudioContext)();
  return ac;
}}
function beep(freq, when, dur, gain, type='triangle') {{
  const c = getAC();
  const o = c.createOscillator(), g = c.createGain();
  o.type = type; o.frequency.value = freq;
  g.gain.setValueAtTime(gain, when);
  g.gain.linearRampToValueAtTime(0.0001, when + dur);
  o.connect(g); g.connect(c.destination);
  o.start(when); o.stop(when + dur + 0.01);
}}

// ── 播放 ────────────────────────────────────────────────────
let playing = false, rafId = null;
let ni = 0, mi = 0, lastT = 0;

function togglePlay() {{
  if (playing) pause(); else play();
}}

async function play() {{
  const a = getAC();
  if (a.state === 'suspended') await a.resume();
  playing = true;
  document.getElementById('btn').textContent = '❙❙ 暫停';
  document.getElementById('btn').classList.add('playing');
  lastT = performance.now();
  rafId = requestAnimationFrame(step);
}}

function pause() {{
  playing = false;
  document.getElementById('btn').textContent = '▶ 繼續';
  document.getElementById('btn').classList.remove('playing');
  if (rafId) cancelAnimationFrame(rafId);
}}

function doReset() {{
  pause();
  nVis.clear(); mVis.clear(); nRet.clear(); mRet.clear();
  nGlo.clear(); mGlo.clear();
  ni = 0; mi = 0;
  document.getElementById('btn').textContent = '▶ 播放';
  document.getElementById('summary').textContent = '';
  document.getElementById('summary').classList.remove('done');
  document.getElementById('naive-count').textContent = '0';
  document.getElementById('memo-count').textContent  = '0';
  drawTree('naive-cv', NAIVE_N, NAIVE_E, nVis, nRet, nGlo, NAIVE_MX, NAIVE_MD);
  drawTree('memo-cv',  MEMO_N,  MEMO_E,  mVis, mRet, mGlo, MEMO_MX,  MEMO_MD);
}}

function decayGlow(map) {{
  map.forEach((v, k) => {{
    const v2 = v - 0.12;
    if (v2 <= 0) map.delete(k); else map.set(k, v2);
  }});
}}

function processEvent(ev, nodes, vis, ret, glo, side) {{
  const n   = nodes[ev.id];
  const a   = getAC();
  const now = a.currentTime;
  if (ev.type === 'call') {{
    vis.add(ev.id);
    beep(n.freq, now, ev.cached ? 0.05 : 0.08,
         ev.cached ? 0.06 : 0.14,
         ev.cached ? 'sine' : 'triangle');
  }} else {{
    ret.add(ev.id);
    glo.set(ev.id, 1.0);
    beep(n.freq * (ev.cached ? 1 : 2), now, ev.cached ? 0.06 : 0.11,
         ev.cached ? 0.05 : 0.10, 'sine');
  }}
}}

function step(now) {{
  if (!playing) return;
  const ms = parseInt(document.getElementById('spd').value);
  if (now - lastT < ms) {{ rafId = requestAnimationFrame(step); return; }}
  lastT = now;

  const nDone = ni >= NAIVE_E.length;
  const mDone = mi >= MEMO_E.length;

  if (!nDone) {{ processEvent(NAIVE_E[ni++], NAIVE_N, nVis, nRet, nGlo, 'naive'); }}
  if (!mDone) {{ processEvent(MEMO_E[mi++],  MEMO_N,  mVis, mRet, mGlo, 'memo');  }}

  decayGlow(nGlo); decayGlow(mGlo);

  drawTree('naive-cv', NAIVE_N, NAIVE_E, nVis, nRet, nGlo, NAIVE_MX, NAIVE_MD);
  drawTree('memo-cv',  MEMO_N,  MEMO_E,  mVis, mRet, mGlo, MEMO_MX,  MEMO_MD);

  if (nDone && mDone) {{
    pause();
    document.getElementById('btn').textContent = '▶ 重播';
    const s = document.getElementById('summary');
    s.textContent = `沒有記憶：${{NAIVE_N.length}} 個節點   ·   有記憶：${{MEMO_N.length}} 個節點   ·   差 ${{NAIVE_N.length - MEMO_N.length}} 個`;
    s.classList.add('done');
  }} else {{
    rafId = requestAnimationFrame(step);
  }}
}}

// 初始靜態
drawTree('naive-cv', NAIVE_N, NAIVE_E, nVis, nRet, nGlo, NAIVE_MX, NAIVE_MD);
drawTree('memo-cv',  MEMO_N,  MEMO_E,  mVis, mRet, mGlo, MEMO_MX,  MEMO_MD);
</script>
</body>
</html>"""

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'memo_compare.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'→ {out}')
webbrowser.open(out)

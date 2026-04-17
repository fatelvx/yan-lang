#!/usr/bin/env python3
# fib_tree.py — fib 的呼叫樹生長
#
# 用 Python 直接追蹤 fib(8) 的呼叫結構，
# 渲染成一棵在執行過程中逐步生長的二元樹。
# 每個節點是一次呼叫，每條邊是一次遞迴。
# 呼叫時枝條長出，回傳時節點發光。

import json, os, webbrowser, colorsys

# ── 建立呼叫樹 ──────────────────────────────────────────────────

nodes  = []   # {id, n, parent, children, value, x, y}
events = []   # {type: 'call'|'return', id, value?}

def build(n, parent_id=None):
    node_id = len(nodes)
    node = {'id': node_id, 'n': n, 'parent': parent_id,
            'children': [], 'x': 0.0, 'y': 0, 'value': None}
    nodes.append(node)
    if parent_id is not None:
        nodes[parent_id]['children'].append(node_id)
    events.append({'type': 'call', 'id': node_id})

    if n < 2:
        result = n
    else:
        result = build(n - 1, node_id) + build(n - 2, node_id)

    node['value'] = result
    events.append({'type': 'return', 'id': node_id, 'value': result})
    return result

build(8)
print(f'節點數 : {len(nodes)}')
print(f'事件數 : {len(events)}')
print(f'最大深度: {max(n["y"] for n in nodes) if nodes else 0}')  # 還沒 layout

# ── 佈局（葉節點依序排列，內部節點居中）─────────────────────────

_x = [0]

def layout(nid, depth):
    node = nodes[nid]
    node['y'] = depth
    if not node['children']:
        node['x'] = float(_x[0])
        _x[0] += 1
    else:
        for cid in node['children']:
            layout(cid, depth + 1)
        xs = [nodes[c]['x'] for c in node['children']]
        node['x'] = sum(xs) / len(xs)

layout(0, 0)

max_depth = max(n['y'] for n in nodes)
max_x     = max(n['x'] for n in nodes)
print(f'最大深度: {max_depth}，葉節點數: {_x[0]}')

# ── 顏色：n 值 → 色相（n=0 青綠，n=8 紫紅）──────────────────────

def n_color(n, alpha=1.0):
    t = n / 8.0
    hue = 0.55 - t * 0.45   # 0.55 = 青藍，0.10 = 橙紅
    r, g, b = colorsys.hsv_to_rgb(hue, 0.75 + t * 0.15, 0.85 + t * 0.1)
    if alpha < 1.0:
        return f'rgba({int(r*255)},{int(g*255)},{int(b*255)},{alpha:.2f})'
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

# 音高：n=8 → 低，n=0 → 高
PENTA = [0, 2, 4, 7, 9]
MIDI_BASE = [60 + o*12 + s for o in range(3) for s in PENTA]

def n_freq(n):
    idx = int((1 - n/8) * (len(MIDI_BASE) - 1))
    midi = MIDI_BASE[idx]
    return round(440 * (2 ** ((midi - 69) / 12)), 2)

# 把顏色和頻率嵌入節點
for node in nodes:
    node['color']      = n_color(node['n'])
    node['color_dim']  = n_color(node['n'], 0.25)
    node['color_glow'] = n_color(node['n'], 1.0)
    node['freq']       = n_freq(node['n'])

NODES_JS  = json.dumps(nodes)
EVENTS_JS = json.dumps(events)

# ── HTML ────────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>fib 的生長</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #05050e;
  font-family: 'Courier New', monospace;
  color: #556;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 36px 20px;
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
  color: #1e1e30;
  margin-bottom: 24px;
  letter-spacing: 1px;
}}
canvas {{
  border: 1px solid #0c0c1c;
  border-radius: 3px;
  display: block;
}}
.controls {{
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 18px 0 10px;
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
button.playing {{ color: #6cf; border-color: #248; background: #0a1525; }}
label {{ font-size: 10px; color: #2a2a3c; }}
input[type=range] {{ width: 80px; accent-color: #336; }}
.spd-v {{ font-size: 10px; color: #334; }}
.info {{
  font-size: 10px;
  color: #1e1e30;
  margin-top: 10px;
  letter-spacing: 1px;
  height: 14px;
  transition: color 0.2s;
}}
.info.active {{ color: #445; }}
</style>
</head>
<body>

<h1>fib 的生長</h1>
<div class="sub">fib(8) 呼叫樹 · {len(nodes)} 個節點 · {len(events)} 個事件</div>

<canvas id="cv" width="1180" height="560"></canvas>

<div class="controls">
  <button id="btn" onclick="togglePlay()">▶ 播放</button>
  <label>速度</label>
  <input type="range" id="spd" min="10" max="500" value="60"
         oninput="document.getElementById('spd-v').textContent=this.value+'ms'">
  <span class="spd-v" id="spd-v">60ms</span>
  <button onclick="reset()">↺ 重置</button>
</div>
<div class="info" id="info"></div>

<script>
const NODES  = {NODES_JS};
const EVENTS = {EVENTS_JS};
const MAX_X  = {max_x:.1f};
const MAX_D  = {max_depth};

// ── 座標轉換 ─────────────────────────────────────────────────
const W = 1180, H = 560;
const PAD_L = 50, PAD_R = 50, PAD_T = 50, PAD_B = 30;
const plotW = W - PAD_L - PAD_R;
const plotH = H - PAD_T - PAD_B;
const R = 13;  // 節點半徑

function nodeX(n) {{ return PAD_L + (n.x / MAX_X) * plotW; }}
function nodeY(n) {{ return PAD_T + (n.y / MAX_D) * plotH; }}

// ── 渲染狀態 ─────────────────────────────────────────────────
const visible   = new Set();   // 已出現的節點 id
const returned  = new Set();   // 已回傳的節點 id
const glowing   = new Map();   // id → glow_alpha（淡出用）

const cv  = document.getElementById('cv');
const ctx = cv.getContext('2d');

function draw() {{
  ctx.fillStyle = '#05050e';
  ctx.fillRect(0, 0, W, H);

  // 邊
  visible.forEach(id => {{
    const n = NODES[id];
    if (n.parent === null) return;
    const p = NODES[n.parent];
    if (!visible.has(p.id)) return;
    ctx.beginPath();
    ctx.moveTo(nodeX(p), nodeY(p));
    ctx.lineTo(nodeX(n), nodeY(n));
    ctx.strokeStyle = returned.has(id) ? n.color + '40' : '#1a1a2e';
    ctx.lineWidth = 1;
    ctx.stroke();
  }});

  // 節點
  visible.forEach(id => {{
    const n  = NODES[id];
    const x  = nodeX(n), y = nodeY(n);
    const ret = returned.has(id);
    const gl  = glowing.get(id) || 0;

    // 光暈
    if (gl > 0) {{
      ctx.shadowColor = n.color;
      ctx.shadowBlur  = 24 * gl;
    }}

    // 圓圈
    ctx.beginPath();
    ctx.arc(x, y, R, 0, Math.PI * 2);
    ctx.fillStyle   = ret ? n.color : n.color_dim;
    ctx.fill();
    ctx.strokeStyle = ret ? n.color + 'cc' : '#1e1e35';
    ctx.lineWidth   = ret ? 1.5 : 1;
    ctx.stroke();

    ctx.shadowBlur = 0;

    // 標籤
    ctx.fillStyle = ret ? '#fff' : '#334';
    ctx.font = `${{ret ? 'bold ' : ''}}${{R < 10 ? 8 : 10}}px monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(n.n, x, y);
  }});
}}

// ── 音訊 ─────────────────────────────────────────────────────
let ac = null;
function getAC() {{
  if (!ac) ac = new (window.AudioContext || window.webkitAudioContext)();
  return ac;
}}

function beep(freq, when, dur, gain, type='triangle') {{
  const ctx  = getAC();
  const osc  = ctx.createOscillator();
  const g    = ctx.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  g.gain.setValueAtTime(gain, when);
  g.gain.linearRampToValueAtTime(0.0001, when + dur);
  osc.connect(g); g.connect(ctx.destination);
  osc.start(when); osc.stop(when + dur + 0.01);
}}

// ── 播放 ─────────────────────────────────────────────────────
let playing  = false;
let evtIdx   = 0;
let lastTime = 0;
let rafId    = null;

function togglePlay() {{
  if (playing) pause(); else play();
}}

async function play() {{
  const ac2 = getAC();
  if (ac2.state === 'suspended') await ac2.resume();
  playing = true;
  document.getElementById('btn').textContent = '❙❙ 暫停';
  document.getElementById('btn').classList.add('playing');
  lastTime = performance.now();
  rafId = requestAnimationFrame(step);
}}

function pause() {{
  playing = false;
  document.getElementById('btn').textContent = '▶ 繼續';
  document.getElementById('btn').classList.remove('playing');
  if (rafId) cancelAnimationFrame(rafId);
}}

function reset() {{
  pause();
  visible.clear(); returned.clear(); glowing.clear();
  evtIdx = 0;
  document.getElementById('btn').textContent = '▶ 播放';
  document.getElementById('info').textContent = '';
  document.getElementById('info').classList.remove('active');
  draw();
}}

function step(now) {{
  if (!playing) return;
  const ms = parseInt(document.getElementById('spd').value);
  if (now - lastTime < ms) {{
    rafId = requestAnimationFrame(step);
    return;
  }}
  lastTime = now;

  if (evtIdx >= EVENTS.length) {{
    pause();
    document.getElementById('btn').textContent = '▶ 重播';
    return;
  }}

  const ev = EVENTS[evtIdx++];
  const n  = NODES[ev.id];
  const ac2 = getAC();

  if (ev.type === 'call') {{
    visible.add(ev.id);
    // 音：呼叫時短促一聲
    beep(n.freq, ac2.currentTime, 0.08, 0.15);

    const info = document.getElementById('info');
    info.textContent = `fib(${{n.n}}) 呼叫`;
    info.classList.add('active');

  }} else {{
    returned.add(ev.id);
    glowing.set(ev.id, 1.0);
    // 音：回傳時稍長一點，稍亮
    beep(n.freq * 2, ac2.currentTime, 0.12, 0.10, 'sine');

    const info = document.getElementById('info');
    info.textContent = `fib(${{n.n}}) = ${{ev.value}}`;
    info.classList.add('active');
  }}

  // 淡出光暈
  glowing.forEach((alpha, id) => {{
    const a2 = alpha - 0.15;
    if (a2 <= 0) glowing.delete(id);
    else glowing.set(id, a2);
  }});

  draw();
  rafId = requestAnimationFrame(step);
}}

// 初始畫面
draw();
</script>
</body>
</html>"""

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fib_tree.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'→ {out}')
webbrowser.open(out)

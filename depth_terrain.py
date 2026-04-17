#!/usr/bin/env python3
# depth_terrain.py — 遞迴的地形
#
# 把計算的呼叫堆疊深度畫成地形：
# X 軸 = 時間（每個求值步驟）
# Y 軸 = 當下的呼叫深度
# 顏色 = 函式名稱
#
# factorial 是線性遞迴 → 一個完整的山
# fib 是二元遞迴 → 鋸齒狀的山脈

import sys, hashlib, colorsys, json, os, webbrowser
sys.path.insert(0, 'yan')
import yan

# ── 捕捉（名稱, 深度）序列 ───────────────────────────────────────

_trace = []

def _hook(expr):
    if isinstance(expr, list) and expr and isinstance(expr[0], yan.Symbol):
        _trace.append((str(expr[0]), yan._eval_depth))

yan._eval_hook = _hook
env = yan._make_global_env()

def run(src):
    global _trace; _trace = []
    for e in yan.parse_all(src): yan.eval_yn(e, env)
    return list(_trace)

run('(define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1)))))')
fac_trace = run('(factorial 10)')

run('(define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))')
fib_trace = run('(fib 8)')

print(f'factorial 10 : {len(fac_trace)} 步, 最大深度 {max(d for _,d in fac_trace)}')
print(f'fib 8        : {len(fib_trace)} 步, 最大深度 {max(d for _,d in fib_trace)}')

# ── 音高 / 顏色 ─────────────────────────────────────────────────

PENTA = [0, 2, 4, 7, 9]
SCALE_MIDI = [36 + o * 12 + s for o in range(5) for s in PENTA]

def to_freq(midi): return round(440 * (2 ** ((midi - 69) / 12)), 3)

def depth_freq(depth, max_depth):
    # 深度越大 → 音高越低
    ratio = 1.0 - (depth - 1) / max(max_depth - 1, 1)
    idx = int(ratio * (len(SCALE_MIDI) - 1))
    return to_freq(SCALE_MIDI[idx])

def name_color(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.72, 0.90)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def build_notes(trace):
    max_d = max(d for _, d in trace)
    return [{'name': n, 'depth': d,
             'freq': depth_freq(d, max_d),
             'color': name_color(n)} for n, d in trace]

fac_notes = build_notes(fac_trace)
fib_notes  = build_notes(fib_trace)

FAC_JS     = json.dumps(fac_notes)
FIB_JS     = json.dumps(fib_notes)
FAC_MAX_D  = max(d for _, d in fac_trace)
FIB_MAX_D  = max(d for _, d in fib_trace)

# ── HTML ────────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>遞迴的地形</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #050510;
  color: #667;
  font-family: 'Courier New', monospace;
  padding: 44px 52px;
}}
h1 {{
  font-size: 12px;
  color: #445;
  letter-spacing: 5px;
  text-transform: uppercase;
  margin-bottom: 5px;
}}
.sub {{
  font-size: 10px;
  color: #2a2a3a;
  margin-bottom: 34px;
  letter-spacing: 1px;
}}
.track-name {{
  font-size: 10px;
  color: #334;
  letter-spacing: 3px;
  margin-bottom: 5px;
  display: flex;
  align-items: baseline;
  gap: 10px;
}}
.track-stat {{ color: #222233; font-size: 9px; }}
canvas {{
  display: block;
  border: 1px solid #0d0d1a;
  border-radius: 2px;
  margin-bottom: 4px;
}}
.gap {{ height: 22px; }}

/* 當前狀態列 */
.status {{
  display: flex;
  gap: 40px;
  margin: 18px 0 22px;
  align-items: center;
}}
.stat-block {{
  min-width: 160px;
}}
.stat-label {{
  font-size: 9px;
  color: #223;
  letter-spacing: 2px;
  margin-bottom: 4px;
}}
.stat-fn {{
  font-size: 20px;
  font-weight: bold;
  color: #1a1a28;
  transition: color 0.1s, text-shadow 0.1s;
  min-height: 26px;
}}
.stat-depth {{
  font-size: 10px;
  color: #222;
  margin-top: 2px;
  transition: color 0.15s;
}}
/* 深度計 */
.depth-meter {{
  flex: 1;
  position: relative;
}}
.depth-bar-bg {{
  height: 6px;
  background: #0a0a18;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 4px;
}}
.depth-bar {{
  height: 100%;
  border-radius: 3px;
  transition: width 0.08s, background 0.08s;
  width: 0%;
}}
.depth-num {{
  font-size: 9px;
  color: #2a2a3a;
  letter-spacing: 1px;
}}

/* 控制 */
.controls {{
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 26px;
}}
button {{
  background: #0c0c1c;
  color: #556;
  border: 1px solid #181828;
  padding: 8px 22px;
  cursor: pointer;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  letter-spacing: 1px;
  transition: all 0.15s;
}}
button:hover {{ background: #141430; color: #88a; }}
button.playing {{ color: #6cf; border-color: #369; background: #0a1525; }}
label {{ font-size: 10px; color: #2a2a3a; }}
input[type=range] {{ width: 90px; accent-color: #335; }}
.spd-v {{ font-size: 10px; color: #334; }}
</style>
</head>
<body>

<h1>遞迴的地形</h1>
<div class="sub">factorial 10 — fib 8 · 堆疊深度作為地形</div>

<div class="controls">
  <button id="btn" onclick="togglePlay()">▶ 播放</button>
  <label>速度</label>
  <input type="range" id="spd" min="20" max="300" value="80"
         oninput="document.getElementById('spd-v').textContent=this.value+'ms'">
  <span class="spd-v" id="spd-v">80ms</span>
</div>

<div class="track-name">
  FACTORIAL 10
  <span class="track-stat" id="fac-stat">{len(fac_notes)} 步 · 最大深度 {FAC_MAX_D}</span>
</div>
<canvas id="fac-cv" width="1280" height="160"></canvas>

<div class="gap"></div>

<div class="track-name">
  FIB 8
  <span class="track-stat" id="fib-stat">{len(fib_notes)} 步 · 最大深度 {FIB_MAX_D}</span>
</div>
<canvas id="fib-cv" width="1280" height="160"></canvas>

<div class="status">
  <div class="stat-block">
    <div class="stat-label">FACTORIAL</div>
    <div class="stat-fn" id="fac-fn">—</div>
    <div class="stat-depth" id="fac-d"></div>
  </div>

  <div class="depth-meter">
    <div class="stat-label" style="margin-bottom:8px;">深度對比</div>
    <div class="stat-label">factorial</div>
    <div class="depth-bar-bg"><div class="depth-bar" id="fac-bar"></div></div>
    <div class="stat-label" style="margin-top:8px;">fib</div>
    <div class="depth-bar-bg"><div class="depth-bar" id="fib-bar"></div></div>
  </div>

  <div class="stat-block" style="text-align:right">
    <div class="stat-label">FIB</div>
    <div class="stat-fn" id="fib-fn">—</div>
    <div class="stat-depth" id="fib-d"></div>
  </div>
</div>

<script>
const FAC = {FAC_JS};
const FIB = {FIB_JS};
const FAC_MAX = {FAC_MAX_D};
const FIB_MAX = {FIB_MAX_D};

// ── 畫靜態地形 ───────────────────────────────────────────────────
function drawTerrain(canvasId, notes, maxD, headIdx) {{
  const cv  = document.getElementById(canvasId);
  const ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  const PAD_L = 8, PAD_R = 8, PAD_T = 10, PAD_B = 20;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;
  const n = notes.length;

  ctx.fillStyle = '#050510';
  ctx.fillRect(0, 0, W, H);

  // 深度格線
  for (let d = 1; d <= maxD; d++) {{
    const y = PAD_T + plotH - (d / maxD) * plotH;
    ctx.strokeStyle = d % 5 === 0 ? '#0f0f20' : '#090914';
    ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(PAD_L, y); ctx.lineTo(W - PAD_R, y); ctx.stroke();
    if (d % 5 === 0) {{
      ctx.fillStyle = '#1a1a28';
      ctx.font = '8px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(d, 2, y + 3);
    }}
  }}

  // 地形填充（每個音符一段）
  const colW = plotW / n;
  notes.forEach((note, i) => {{
    const x   = PAD_L + i * colW;
    const h   = (note.depth / maxD) * plotH;
    const y   = PAD_T + plotH - h;
    const dim = headIdx < 0 ? 1.0 :
                (i < headIdx ? 0.18 : (i === headIdx ? 1.0 : 0.42));
    ctx.globalAlpha = dim;
    ctx.fillStyle = note.color;
    ctx.fillRect(x, y, Math.max(colW, 0.8), h);
  }});

  ctx.globalAlpha = 1;

  // 地形輪廓線
  ctx.beginPath();
  ctx.strokeStyle = 'rgba(160,180,220,0.12)';
  ctx.lineWidth = 1;
  notes.forEach((note, i) => {{
    const x = PAD_L + (i + 0.5) * colW;
    const y = PAD_T + plotH - (note.depth / maxD) * plotH;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }});
  ctx.stroke();

  // 播放頭
  if (headIdx >= 0) {{
    const px = PAD_L + (headIdx + 0.5) * colW;
    ctx.strokeStyle = 'rgba(180,210,255,0.55)';
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(px, PAD_T); ctx.lineTo(px, H - PAD_B); ctx.stroke();

    // 當前音符的光暈
    const cur = notes[headIdx];
    const cy  = PAD_T + plotH - (cur.depth / maxD) * plotH;
    ctx.shadowColor = cur.color;
    ctx.shadowBlur  = 18;
    ctx.fillStyle   = cur.color;
    ctx.beginPath();
    ctx.arc(px, cy, 3.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }}

  // X 軸
  ctx.fillStyle = '#0d0d1a';
  ctx.fillRect(PAD_L, PAD_T + plotH, plotW, 1);
}}

// ── 音訊 ────────────────────────────────────────────────────────
let ac = null;
function getAC() {{
  if (!ac) ac = new (window.AudioContext || window.webkitAudioContext)();
  return ac;
}}

function playNote(freq, when, dur, color) {{
  const ctx  = getAC();
  const osc  = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'triangle';
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.18, when);
  gain.gain.setValueAtTime(0.18, when + dur * 0.6);
  gain.gain.linearRampToValueAtTime(0.0001, when + dur);
  osc.connect(gain); gain.connect(ctx.destination);
  osc.start(when); osc.stop(when + dur + 0.02);
}}

// ── 播放 ────────────────────────────────────────────────────────
let playing = false, raf = null, wallStart = 0;
const MAX_NOTES = Math.max(FAC.length, FIB.length);

function togglePlay() {{
  if (playing) stopPlay(); else startPlay();
}}

async function startPlay() {{
  const ctx = getAC();
  if (ctx.state === 'suspended') await ctx.resume();

  const ms  = parseInt(document.getElementById('spd').value);
  const sec = ms / 1000;
  const now = ctx.currentTime + 0.12;

  // 排程音符（兩軌，不同時長）
  FAC.forEach((n, i) => {{ playNote(n.freq, now + i * sec, sec * 1.4, n.color); }});
  FIB.forEach((n, i) => {{
    const t = now + (i / FIB.length) * (FAC.length * sec);
    playNote(n.freq * 0.5, t, (FAC.length * sec / FIB.length) * 1.3, n.color);
  }});

  playing   = true;
  wallStart = performance.now();
  document.getElementById('btn').textContent = '■ 停止';
  document.getElementById('btn').classList.add('playing');

  function animate() {{
    if (!playing) return;
    const elapsed = performance.now() - wallStart;
    const total   = FAC.length * ms;

    const facIdx = Math.min(Math.floor(elapsed / ms), FAC.length - 1);
    const fibIdx = Math.min(Math.floor((elapsed / total) * FIB.length), FIB.length - 1);

    drawTerrain('fac-cv', FAC, FAC_MAX, facIdx);
    drawTerrain('fib-cv', FIB, FIB_MAX, fibIdx);
    updateStatus(facIdx, fibIdx);

    if (elapsed < total) {{
      raf = requestAnimationFrame(animate);
    }} else {{
      stopPlay(true);
    }}
  }}
  raf = requestAnimationFrame(animate);
}}

function stopPlay(fin) {{
  playing = false;
  if (raf) cancelAnimationFrame(raf);
  document.getElementById('btn').textContent = '▶ 播放';
  document.getElementById('btn').classList.remove('playing');

  // 播完後保持最後狀態
  if (!fin) {{
    drawTerrain('fac-cv', FAC, FAC_MAX, -1);
    drawTerrain('fib-cv', FIB, FIB_MAX, -1);
    ['fac-fn','fib-fn','fac-d','fib-d'].forEach(id => {{
      document.getElementById(id).textContent = id.endsWith('-fn') ? '—' : '';
      document.getElementById(id).style.color = '';
      document.getElementById(id).style.textShadow = '';
    }});
    document.getElementById('fac-bar').style.width = '0%';
    document.getElementById('fib-bar').style.width = '0%';
  }}
}}

function updateStatus(facIdx, fibIdx) {{
  const fn = FAC[facIdx], fi = FIB[fibIdx];

  document.getElementById('fac-fn').textContent = fn.name;
  document.getElementById('fac-fn').style.color = fn.color;
  document.getElementById('fac-fn').style.textShadow = `0 0 16px ${{fn.color}}66`;
  document.getElementById('fac-d').textContent = `depth ${{fn.depth}}`;
  document.getElementById('fac-d').style.color = fn.color + '99';

  document.getElementById('fib-fn').textContent = fi.name;
  document.getElementById('fib-fn').style.color = fi.color;
  document.getElementById('fib-fn').style.textShadow = `0 0 16px ${{fi.color}}66`;
  document.getElementById('fib-d').textContent = `depth ${{fi.depth}}`;
  document.getElementById('fib-d').style.color = fi.color + '99';

  document.getElementById('fac-bar').style.width = `${{(fn.depth / FAC_MAX) * 100}}%`;
  document.getElementById('fac-bar').style.background = fn.color;
  document.getElementById('fib-bar').style.width = `${{(fi.depth / FIB_MAX) * 100}}%`;
  document.getElementById('fib-bar').style.background = fi.color;
}}

// 初始靜態畫面
drawTerrain('fac-cv', FAC, FAC_MAX, -1);
drawTerrain('fib-cv', FIB, FIB_MAX, -1);
</script>
</body>
</html>"""

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'depth_terrain.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'→ {out}')
webbrowser.open(out)

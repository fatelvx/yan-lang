#!/usr/bin/env python3
# roll_audio.py — 讓計算的音樂真正發出聲音
# 生成一個 HTML 檔，用 Web Audio API 播放 Yán 程式的執行序列

import sys, hashlib, colorsys, json, webbrowser
sys.path.insert(0, 'yan')
import yan

# ══════════════════════════════════════════════════════════════
# 音高與顏色
# ══════════════════════════════════════════════════════════════

PENTA = [0, 2, 4, 7, 9]
SCALE = [48 + o * 12 + s for o in range(4) for s in PENTA]   # 20 音

def name_to_midi(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return SCALE[h % len(SCALE)]

def midi_to_freq(midi):
    return 440 * (2 ** ((midi - 69) / 12))

def name_to_color(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.95)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

# ══════════════════════════════════════════════════════════════
# 追蹤執行
# ══════════════════════════════════════════════════════════════

_log = []
def _hook(expr):
    if isinstance(expr, list) and expr and isinstance(expr[0], yan.Symbol):
        _log.append(str(expr[0]))

yan._eval_hook = _hook
env = yan._make_global_env()

def run(src):
    global _log; _log = []
    for e in yan.parse_all(src): yan.eval_yn(e, env)
    return list(_log)

run('(define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1)))))')
fac_log = run('(factorial 10)')

run('(define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))')
fib_log = run('(fib 12)')

def make_notes(log):
    return [{'name': s, 'freq': midi_to_freq(name_to_midi(s)),
             'color': name_to_color(s), 'midi': name_to_midi(s)}
            for s in log]

fac_notes = make_notes(fac_log)
fib_notes  = make_notes(fib_log)

print(f'factorial 10 : {len(fac_notes)} 音符')
print(f'fib 12       : {len(fib_notes)} 音符')

# ══════════════════════════════════════════════════════════════
# HTML
# ══════════════════════════════════════════════════════════════

FAC_JSON = json.dumps(fac_notes)
FIB_JSON  = json.dumps(fib_notes)

SCALE_JSON = json.dumps(SCALE)
MIDI_MIN = min(SCALE)
MIDI_MAX = max(SCALE)

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>計算的音樂</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #080810;
    color: #ccd;
    font-family: 'Courier New', monospace;
    padding: 30px 40px;
  }}
  h1 {{
    font-size: 18px;
    color: #778;
    letter-spacing: 2px;
    margin-bottom: 30px;
  }}
  .section {{
    margin-bottom: 40px;
  }}
  .section h2 {{
    font-size: 14px;
    color: #aab;
    margin-bottom: 10px;
    letter-spacing: 1px;
  }}
  .controls {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }}
  button {{
    background: #1a1a30;
    color: #99f;
    border: 1px solid #334;
    padding: 7px 18px;
    cursor: pointer;
    border-radius: 4px;
    font-family: monospace;
    font-size: 13px;
    transition: background 0.15s;
  }}
  button:hover {{ background: #2a2a50; }}
  button.playing {{ background: #0a2040; color: #6cf; border-color: #469; }}
  label {{ font-size: 12px; color: #556; }}
  input[type=range] {{
    width: 120px;
    accent-color: #448;
  }}
  .speed-val {{ font-size: 12px; color: #778; min-width: 50px; }}
  canvas {{
    display: block;
    border: 1px solid #1a1a28;
    border-radius: 4px;
    cursor: pointer;
  }}
  .info {{
    font-size: 11px;
    color: #445;
    margin-top: 8px;
  }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 8px;
  }}
  .leg-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #778;
  }}
  .leg-dot {{
    width: 10px; height: 10px;
    border-radius: 2px;
    flex-shrink: 0;
  }}
</style>
</head>
<body>

<h1>計算的音樂 — Yán 執行序列</h1>
<div style="margin-bottom:20px;display:flex;align-items:center;gap:16px">
  <button onclick="testBeep()">♪ 測試聲音</button>
  <span id="status" style="font-size:12px;color:#556"></span>
</div>

<div class="section">
  <h2>factorial 10  <span style="color:#445;font-size:12px">{len(fac_notes)} 個呼叫</span></h2>
  <div class="controls">
    <button id="btn-fac" onclick="togglePlay('fac')">▶ 播放</button>
    <label>速度</label>
    <input type="range" id="spd-fac" min="20" max="400" value="100"
           oninput="updateSpeed('fac')">
    <span class="speed-val" id="spd-fac-val">100 ms/音</span>
  </div>
  <canvas id="canvas-fac" width="1300" height="240"></canvas>
  <div class="legend" id="legend-fac"></div>
  <div class="info">稀疏，可以聽到每一步；遞迴下降時用 if / = / factorial，回升時出現 *</div>
</div>

<div class="section">
  <h2>fib 12  <span style="color:#445;font-size:12px">{len(fib_notes)} 個呼叫</span></h2>
  <div class="controls">
    <button id="btn-fib" onclick="togglePlay('fib')">▶ 播放</button>
    <label>速度</label>
    <input type="range" id="spd-fib" min="2" max="100" value="8"
           oninput="updateSpeed('fib')">
    <span class="speed-val" id="spd-fib-val">8 ms/音</span>
  </div>
  <canvas id="canvas-fib" width="1300" height="240"></canvas>
  <div class="legend" id="legend-fib"></div>
  <div class="info">密集，單個音符難以辨認；指數遞迴的質感——越往後越快疊加</div>
</div>

<script>
const FAC_NOTES = {FAC_JSON};
const FIB_NOTES  = {FIB_JSON};
const SCALE = {SCALE_JSON};
const MIDI_MIN = {MIDI_MIN};
const MIDI_MAX = {MIDI_MAX};

const DATASETS = {{
  fac: {{ notes: FAC_NOTES,  canvas: 'canvas-fac', btn: 'btn-fac', spd: 'spd-fac' }},
  fib: {{ notes: FIB_NOTES,  canvas: 'canvas-fib', btn: 'btn-fib', spd: 'spd-fib' }},
}};

// ── 音訊設定 ────────────────────────────────────────────────
let audioCtx = null;
const playState = {{ fac: null, fib: null }};

function getAudioCtx() {{
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  return audioCtx;
}}

// 播放單個音符（最簡潔可靠的版本）
function scheduleNote(ac, freq, startTime, duration, gainVal) {{
  const osc  = ac.createOscillator();
  const gain = ac.createGain();

  osc.type = 'triangle';
  osc.frequency.value = freq;

  gain.gain.setValueAtTime(gainVal, startTime);
  gain.gain.setValueAtTime(gainVal, startTime + duration * 0.7);
  gain.gain.linearRampToValueAtTime(0.0001, startTime + duration);

  osc.connect(gain);
  gain.connect(ac.destination);
  osc.start(startTime);
  osc.stop(startTime + duration + 0.02);
}}

// ── 播放控制 ────────────────────────────────────────────────
function togglePlay(id) {{
  if (playState[id]) {{ stopTrack(id); }} else {{ startTrack(id); }}
}}

async function startTrack(id) {{
  const ds = DATASETS[id];
  const notes = ds.notes;
  const ms = parseInt(document.getElementById(ds.spd).value);
  const secPerNote = ms / 1000;

  const ac = getAudioCtx();
  if (ac.state === 'suspended') {{ await ac.resume(); }}

  setStatus('音訊已啟動，準備播放…');

  const startAudio = ac.currentTime + 0.15;

  notes.forEach((n, i) => {{
    const t   = startAudio + i * secPerNote;
    const dur = Math.max(secPerNote * 1.6, 0.04);
    scheduleNote(ac, n.freq, t, dur, 0.28);
  }});

  const totalMs = notes.length * ms;
  const startWall = performance.now();
  let raf;

  function draw() {{
    const elapsed = performance.now() - startWall;
    const progress = Math.min(elapsed / totalMs, 1);
    drawRoll(id, progress);
    if (progress < 1) {{
      raf = requestAnimationFrame(draw);
      if (playState[id]) playState[id].raf = raf;
    }} else {{
      stopTrack(id);
    }}
  }}

  playState[id] = {{ startWall, totalMs, raf: null }};
  document.getElementById(ds.btn).textContent = '■ 停止';
  document.getElementById(ds.btn).classList.add('playing');
  raf = requestAnimationFrame(draw);
  if (playState[id]) playState[id].raf = raf;
  setStatus('');
}}

function stopTrack(id) {{
  const st = playState[id];
  if (!st) return;
  if (st.sources) st.sources.forEach(s => {{ try {{ s.stop(); }} catch(e) {{}} }});
  cancelAnimationFrame(st.raf);
  playState[id] = null;
  const ds = DATASETS[id];
  document.getElementById(ds.btn).textContent = '▶ 播放';
  document.getElementById(ds.btn).classList.remove('playing');
  drawRoll(id, 0);
}}

function updateSpeed(id) {{
  const ds = DATASETS[id];
  const val = document.getElementById(ds.spd).value;
  document.getElementById(ds.spd + '-val').textContent = val + ' ms/音';
  if (playState[id]) {{ stopTrack(id); startTrack(id); }}
}}

// ── 畫布渲染 ────────────────────────────────────────────────
const ROLL_LEFT  = 80;
const ROLL_RIGHT = 20;
const ROW_H = 10;
const PITCH_COUNT = SCALE.length;

function noteY(midi, canvasH) {{
  const idx = SCALE.indexOf(midi);
  const top = 10, bot = canvasH - 10;
  return bot - (idx / (PITCH_COUNT - 1)) * (bot - top);
}}

function drawRoll(id, progress) {{
  const ds = DATASETS[id];
  const canvas = document.getElementById(ds.canvas);
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const rollW = W - ROLL_LEFT - ROLL_RIGHT;

  ctx.clearRect(0, 0, W, H);

  // 背景
  ctx.fillStyle = '#080810';
  ctx.fillRect(0, 0, W, H);

  // 音高格線
  SCALE.forEach((midi, i) => {{
    const y = noteY(midi, H);
    ctx.strokeStyle = midi % 12 === 0 ? '#1e1e35' : '#111120';
    ctx.lineWidth = midi % 12 === 0 ? 1 : 0.5;
    ctx.beginPath();
    ctx.moveTo(ROLL_LEFT, y);
    ctx.lineTo(W - ROLL_RIGHT, y);
    ctx.stroke();
  }});

  // 音符
  const notes = ds.notes;
  const n = notes.length;
  const noteW = Math.max(0.8, rollW / n);
  const currentIdx = Math.floor(progress * n);

  notes.forEach((note, i) => {{
    const x = ROLL_LEFT + (i / n) * rollW;
    const y = noteY(note.midi, H) - ROW_H / 2;

    const isPast    = i < currentIdx;
    const isCurrent = i === currentIdx;
    const alpha = isPast ? 0.25 : (isCurrent ? 1.0 : 0.65);

    ctx.globalAlpha = alpha;
    if (isCurrent) {{
      ctx.shadowColor = note.color;
      ctx.shadowBlur = 8;
    }} else {{
      ctx.shadowBlur = 0;
    }}
    ctx.fillStyle = note.color;
    ctx.fillRect(x, y, Math.max(noteW, 1), ROW_H - 1);
  }});

  ctx.globalAlpha = 1;
  ctx.shadowBlur = 0;

  // 播放頭
  if (progress > 0 && progress < 1) {{
    const px = ROLL_LEFT + progress * rollW;
    ctx.strokeStyle = 'rgba(200,220,255,0.6)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(px, 0);
    ctx.lineTo(px, H);
    ctx.stroke();
  }}

  // 琴鍵標籤
  ctx.fillStyle = '#334';
  ctx.fillRect(0, 0, ROLL_LEFT, H);
  SCALE.forEach(midi => {{
    if (midi % 12 === 0) {{
      const y = noteY(midi, H);
      const oct = Math.floor(midi / 12) - 1;
      ctx.fillStyle = '#445';
      ctx.font = '9px monospace';
      ctx.textAlign = 'right';
      ctx.fillText('C' + oct, ROLL_LEFT - 4, y + 4);
    }}
  }});
}}

// ── 圖例 ────────────────────────────────────────────────────
function buildLegend(id) {{
  const ds = DATASETS[id];
  const notes = ds.notes;
  const counts = {{}};
  const colors = {{}};
  const midis  = {{}};
  notes.forEach(n => {{
    counts[n.name] = (counts[n.name] || 0) + 1;
    colors[n.name] = n.color;
    midis[n.name]  = n.midi;
  }});
  const syms = Object.keys(counts).sort((a,b) => counts[b] - counts[a]);
  const noteNames = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
  const el = document.getElementById('legend-' + id);
  el.innerHTML = syms.map(s => {{
    const note = noteNames[midis[s] % 12];
    const oct  = Math.floor(midis[s] / 12) - 1;
    return `<div class="leg-item">
      <div class="leg-dot" style="background:${{colors[s]}}"></div>
      <span>${{s}}</span>
      <span style="color:#445">${{note}}${{oct}}  ×${{counts[s]}}</span>
    </div>`;
  }}).join('');
}}

function setStatus(msg) {{
  document.getElementById('status').textContent = msg;
}}

async function testBeep() {{
  const ac = getAudioCtx();
  if (ac.state === 'suspended') await ac.resume();
  scheduleNote(ac, 440, ac.currentTime + 0.05, 0.3, 0.4);
  setStatus('如果聽到 A4（440 Hz），表示音訊正常。');
}}

// ── 初始化 ────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {{
  drawRoll('fac', 0);
  drawRoll('fib',  0);
  buildLegend('fac');
  buildLegend('fib');
}});
</script>
</body>
</html>
"""

out_path = 'roll_audio.html'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'→ {out_path}')
webbrowser.open(out_path)

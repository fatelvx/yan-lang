#!/usr/bin/env python3
# counterpoint.py — 兩個計算的對位
#
# factorial 10（53 音）和 fib 8（300 音）同時播放。
# 兩條線用同樣的速度走，factorial 不斷循環。
# 當兩者在同一時刻呼叫同一個函式 → 和聲（consonance）
# 當兩者呼叫不同函式 → 對位（counterpoint）

import sys, hashlib, colorsys, json, webbrowser
sys.path.insert(0, 'yan')
import yan

# ── 捕捉執行序列 ────────────────────────────────────────────────

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
fib_log = run('(fib 8)')

print(f'factorial 10 : {len(fac_log)} 呼叫')
print(f'fib 8        : {len(fib_log)} 呼叫')

# 共同函式
common = set(fac_log) & set(fib_log)
print(f'共同函式     : {sorted(common)}')

# ── 音高 / 顏色 ─────────────────────────────────────────────────

PENTA = [0, 2, 4, 7, 9]
SCALE = [48 + o * 12 + s for o in range(4) for s in PENTA]

def to_midi(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return SCALE[h % len(SCALE)]

def to_freq(midi): return round(440 * (2 ** ((midi - 69) / 12)), 3)

def to_color(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 0.92)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def note_name(midi):
    ns = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B']
    return ns[midi % 12] + str(midi // 12 - 1)

def make_notes(log):
    return [{'name': s, 'freq': to_freq(to_midi(s)),
             'color': to_color(s), 'midi': to_midi(s),
             'note': note_name(to_midi(s))} for s in log]

fac_notes = make_notes(fac_log)
fib_notes  = make_notes(fib_log)

FAC_JS = json.dumps(fac_notes)
FIB_JS  = json.dumps(fib_notes)

SCALE_JS = json.dumps(SCALE)
COMMON_JS = json.dumps(sorted(common))

# ── HTML ────────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>對位</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #07070f;
  color: #889;
  font-family: 'Courier New', monospace;
  padding: 40px 50px;
}}
h1 {{
  font-size: 13px;
  color: #556;
  letter-spacing: 4px;
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.subtitle {{
  font-size: 11px;
  color: #334;
  margin-bottom: 36px;
  letter-spacing: 1px;
}}

/* ── 軌道標籤 ── */
.track-label {{
  font-size: 11px;
  color: #445;
  letter-spacing: 2px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
}}
.loop-badge {{
  font-size: 9px;
  color: #334;
  border: 1px solid #1e1e30;
  padding: 1px 6px;
  border-radius: 10px;
}}

/* ── 畫布 ── */
canvas {{
  display: block;
  border: 1px solid #111120;
  border-radius: 3px;
  margin-bottom: 4px;
}}

/* ── 和聲區 ── */
.harmony-wrap {{
  margin: 6px 0 6px 0;
  position: relative;
  height: 28px;
  display: flex;
  align-items: center;
  gap: 12px;
}}
.harmony-label {{
  font-size: 10px;
  color: #2a2a40;
  letter-spacing: 1px;
  min-width: 80px;
  transition: color 0.2s;
}}
.harmony-label.lit {{ color: #aac; }}
#harmony-canvas {{ border-radius: 3px; }}

/* ── 當前音符顯示 ── */
.cur-row {{
  display: flex;
  gap: 30px;
  margin: 16px 0 20px 0;
  align-items: flex-start;
}}
.cur-voice {{
  flex: 1;
}}
.cur-voice-name {{
  font-size: 10px;
  color: #334;
  letter-spacing: 2px;
  margin-bottom: 6px;
}}
.cur-fn {{
  font-size: 22px;
  font-weight: bold;
  color: #1a1a2e;
  transition: color 0.1s, text-shadow 0.1s;
  min-height: 30px;
}}
.cur-note {{
  font-size: 10px;
  color: #2a2a40;
  margin-top: 3px;
  transition: color 0.1s;
}}
.harmony-msg {{
  font-size: 11px;
  color: #1a1a28;
  text-align: center;
  padding-top: 20px;
  transition: color 0.2s;
  flex: 0.6;
  letter-spacing: 1px;
}}
.harmony-msg.lit {{ color: #88aacc; }}

/* ── 控制 ── */
.controls {{
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}}
button {{
  background: #0e0e1e;
  color: #667;
  border: 1px solid #1a1a28;
  padding: 8px 20px;
  cursor: pointer;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  letter-spacing: 1px;
  transition: all 0.15s;
}}
button:hover {{ background: #151530; color: #99b; }}
button.playing {{ color: #6cf; border-color: #369; background: #0a1525; }}
label {{ font-size: 11px; color: #334; }}
input[type=range] {{ width: 100px; accent-color: #446; }}
.spd-v {{ font-size: 11px; color: #445; }}

/* ── 圖例 ── */
.legend {{
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 10px;
}}
.leg {{ display:flex; align-items:center; gap:6px; font-size:10px; color:#445; }}
.leg-dot {{ width:8px; height:8px; border-radius:2px; }}
</style>
</head>
<body>

<h1>對位</h1>
<div class="subtitle">factorial 10 ✕ fib 8 — 兩個計算同時說話</div>

<div class="controls">
  <button id="btn" onclick="togglePlay()">▶ 播放</button>
  <label>速度</label>
  <input type="range" id="spd" min="40" max="400" value="110"
         oninput="document.getElementById('spd-v').textContent=this.value+'ms'">
  <span class="spd-v" id="spd-v">110ms</span>
</div>

<div class="track-label">
  FACTORIAL 10
  <span class="loop-badge" id="loop-badge">第 1 次循環</span>
</div>
<canvas id="fac-canvas" width="1300" height="130"></canvas>

<div class="harmony-wrap">
  <div class="harmony-label" id="h-label">和聲</div>
  <canvas id="harmony-canvas" width="1204" height="20"></canvas>
</div>

<div class="track-label">FIB 8</div>
<canvas id="fib-canvas" width="1300" height="130"></canvas>

<div class="cur-row">
  <div class="cur-voice">
    <div class="cur-voice-name">FACTORIAL</div>
    <div class="cur-fn" id="fac-fn">—</div>
    <div class="cur-note" id="fac-note"></div>
  </div>
  <div class="harmony-msg" id="h-msg"></div>
  <div class="cur-voice">
    <div class="cur-voice-name">FIB</div>
    <div class="cur-fn" id="fib-fn">—</div>
    <div class="cur-note" id="fib-note"></div>
  </div>
</div>

<div class="legend" id="legend"></div>

<script>
const FAC   = {FAC_JS};
const FIB   = {FIB_JS};
const SCALE = {SCALE_JS};
const COMMON = new Set({COMMON_JS});
const MIDI_MIN = Math.min(...SCALE);
const MIDI_MAX = Math.max(...SCALE);

// ── 圖例 ────────────────────────────────────────────────────────
function buildLegend() {{
  const all = {{}};
  [...FAC, ...FIB].forEach(n => {{ all[n.name] = n.color; }});
  const el = document.getElementById('legend');
  Object.entries(all).sort().forEach(([name, color]) => {{
    const d = document.createElement('div');
    d.className = 'leg';
    d.innerHTML = `<div class="leg-dot" style="background:${{color}}"></div>${{name}}`;
    el.appendChild(d);
  }});
}}
buildLegend();

// ── 音訊 ────────────────────────────────────────────────────────
let ac = null;
function getAC() {{
  if (!ac) ac = new (window.AudioContext || window.webkitAudioContext)();
  return ac;
}}

function playNote(freq, when, dur, gain, pan=0, type='triangle') {{
  const ctx = getAC();
  const osc  = ctx.createOscillator();
  const g    = ctx.createGain();
  const panner = ctx.createStereoPanner();
  osc.type = type;
  osc.frequency.value = freq;
  panner.pan.value = pan;
  g.gain.setValueAtTime(gain, when);
  g.gain.setValueAtTime(gain, when + dur * 0.75);
  g.gain.linearRampToValueAtTime(0.0001, when + dur);
  osc.connect(g); g.connect(panner); panner.connect(ctx.destination);
  osc.start(when); osc.stop(when + dur + 0.02);
}}

// ── 播放 ────────────────────────────────────────────────────────
let playing = false, raf = null, wallStart = 0;

function togglePlay() {{
  if (playing) stopPlay(); else startPlay();
}}

async function startPlay() {{
  const ctx = getAC();
  if (ctx.state === 'suspended') await ctx.resume();

  const ms  = parseInt(document.getElementById('spd').value);
  const sec = ms / 1000;
  const fibTotal = FIB.length * sec;
  const now = ctx.currentTime + 0.15;

  // 排程 fib（播一次）
  FIB.forEach((n, i) => {{
    playNote(n.freq, now + i * sec, sec * 1.5, 0.22, -0.4);
  }});

  // 排程 factorial（循環整個 fib 時長）
  const loops = Math.ceil(FIB.length / FAC.length) + 1;
  for (let loop = 0; loop < loops; loop++) {{
    FAC.forEach((n, i) => {{
      const t = now + (loop * FAC.length + i) * sec;
      if (t < now + fibTotal + sec) {{
        playNote(n.freq, t, sec * 1.5, 0.20, 0.4, 'sine');
      }}
    }});
  }}

  playing   = true;
  wallStart = performance.now() - 100;

  document.getElementById('btn').textContent = '■ 停止';
  document.getElementById('btn').classList.add('playing');

  function animate() {{
    if (!playing) return;
    const elapsed = performance.now() - wallStart;
    const prog    = Math.min(elapsed / (FIB.length * ms), 1);

    const fibIdx = Math.min(Math.floor(elapsed / ms), FIB.length - 1);
    const facIdx = Math.floor(elapsed / ms) % FAC.length;
    const loopN  = Math.floor(elapsed / ms / FAC.length) + 1;

    drawRoll('fac-canvas', FAC, facIdx, true);
    drawRoll('fib-canvas', FIB, fibIdx, false);
    drawHarmony(elapsed, ms);
    updateCur(facIdx, fibIdx, loopN);

    if (prog < 1) {{
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
  document.getElementById('fac-fn').textContent = '—';
  document.getElementById('fib-fn').textContent = '—';
  document.getElementById('fac-note').textContent = '';
  document.getElementById('fib-note').textContent = '';
  document.getElementById('h-msg').textContent = '';
  document.getElementById('h-msg').classList.remove('lit');
  document.getElementById('h-label').classList.remove('lit');
  clearRoll('fac-canvas');
  clearRoll('fib-canvas');
  clearHarmony();
}}

// ── 畫布 ────────────────────────────────────────────────────────
const ROLL_L = 80, ROW_H = 10, N_PITCHES = SCALE.length;

function noteY(midi, H) {{
  const idx = SCALE.indexOf(midi);
  const top = 5, bot = H - 5;
  return bot - (idx / (N_PITCHES - 1)) * (bot - top);
}}

function clearRoll(id) {{
  const c = document.getElementById(id);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#07070f';
  ctx.fillRect(0, 0, c.width, c.height);
}}

function drawRoll(id, notes, curIdx, loops) {{
  const c   = document.getElementById(id);
  const ctx = c.getContext('2d');
  const W = c.width, H = c.height;
  const rollW = W - ROLL_L - 10;

  ctx.fillStyle = '#07070f';
  ctx.fillRect(0, 0, W, H);

  // 格線
  SCALE.forEach(midi => {{
    const y = noteY(midi, H);
    ctx.strokeStyle = midi % 12 === 0 ? '#131325' : '#0d0d18';
    ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(ROLL_L, y); ctx.lineTo(W - 10, y); ctx.stroke();
  }});

  // 音符（如果是循環的，顯示循環視窗）
  const n = notes.length;
  const noteW = Math.max(1, rollW / n);

  notes.forEach((note, i) => {{
    const drawIdx = loops ? ((curIdx - Math.floor(n/2) + i + n*10) % n) : i;
    const x = ROLL_L + (loops ? i : i) / n * rollW;
    const y = noteY(note.midi, H) - ROW_H / 2;
    const isCur = (loops ? i === Math.floor(n/2) : i === curIdx);
    const isPast = !loops && i < curIdx;

    const alpha = isPast ? 0.2 : (isCur ? 1.0 : 0.55);
    ctx.globalAlpha = alpha;
    if (isCur) {{ ctx.shadowColor = note.color; ctx.shadowBlur = 10; }}
    else ctx.shadowBlur = 0;

    // 循環模式：畫的是「以 curIdx 為中心的視窗」
    const displayNote = loops ? notes[(curIdx - Math.floor(n/2) + i + n*1000) % n] : note;
    ctx.fillStyle = displayNote.color;
    ctx.fillRect(x, y, Math.max(noteW, 1.5), ROW_H - 1);
  }});

  ctx.globalAlpha = 1; ctx.shadowBlur = 0;

  // 播放頭（循環模式：中間固定線）
  const px = loops ? ROLL_L + rollW / 2 : ROLL_L + (curIdx / n) * rollW;
  ctx.strokeStyle = 'rgba(180,200,255,0.5)';
  ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, H); ctx.stroke();

  // 琴鍵標籤
  ctx.fillStyle = '#0d0d18';
  ctx.fillRect(0, 0, ROLL_L, H);
  SCALE.forEach(midi => {{
    if (midi % 12 === 0) {{
      const y = noteY(midi, H);
      ctx.fillStyle = '#2a2a3a';
      ctx.font = '9px monospace';
      ctx.textAlign = 'right';
      ctx.fillText('C' + (midi/12|0 - 1), ROLL_L - 4, y + 4);
    }}
  }});
}}

// ── 和聲視覺化 ────────────────────────────────────────────────
const HARM_W = 1204, HARM_H = 20;
const harmHistory = new Array(HARM_W).fill(null);
let harmPtr = 0;

function drawHarmony(elapsed, ms) {{
  const c = document.getElementById('harmony-canvas');
  const ctx = c.getContext('2d');
  const fibIdx = Math.min(Math.floor(elapsed / ms), FIB.length - 1);
  const facIdx = Math.floor(elapsed / ms) % FAC.length;

  const isHarmony = FAC[facIdx].name === FIB[fibIdx].name;
  harmHistory[harmPtr] = isHarmony ? FAC[facIdx].color : null;
  harmPtr = (harmPtr + 1) % HARM_W;

  ctx.fillStyle = '#07070f';
  ctx.fillRect(0, 0, HARM_W, HARM_H);

  harmHistory.forEach((v, i) => {{
    const x = (i - harmPtr + HARM_W) % HARM_W;
    if (v) {{
      ctx.fillStyle = v;
      ctx.globalAlpha = 0.7;
      ctx.fillRect(x, 3, 1, HARM_H - 6);
      ctx.globalAlpha = 1;
    }}
  }});
}}

function clearHarmony() {{
  harmHistory.fill(null);
  const c = document.getElementById('harmony-canvas');
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#07070f';
  ctx.fillRect(0, 0, HARM_W, HARM_H);
}}

// ── 當前音符文字 ──────────────────────────────────────────────
function updateCur(facIdx, fibIdx, loopN) {{
  const fn = FAC[facIdx];
  const fi = FIB[fibIdx];
  const isH = fn.name === fi.name;

  document.getElementById('fac-fn').textContent = fn.name;
  document.getElementById('fac-fn').style.color = fn.color;
  document.getElementById('fac-fn').style.textShadow = isH ? `0 0 20px ${{fn.color}}` : 'none';
  document.getElementById('fac-note').textContent = fn.note;
  document.getElementById('fac-note').style.color = fn.color + '88';

  document.getElementById('fib-fn').textContent = fi.name;
  document.getElementById('fib-fn').style.color = fi.color;
  document.getElementById('fib-fn').style.textShadow = isH ? `0 0 20px ${{fi.color}}` : 'none';
  document.getElementById('fib-note').textContent = fi.note;
  document.getElementById('fib-note').style.color = fi.color + '88';

  const hMsg = document.getElementById('h-msg');
  const hLbl = document.getElementById('h-label');
  if (isH) {{
    hMsg.textContent = '和聲';
    hMsg.classList.add('lit');
    hLbl.classList.add('lit');
  }} else {{
    hMsg.textContent = '對位';
    hMsg.classList.remove('lit');
    hLbl.classList.remove('lit');
  }}

  document.getElementById('loop-badge').textContent = `第 ${{loopN}} 次循環`;
}}
</script>
</body>
</html>"""

import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'counterpoint.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'→ {out}')
webbrowser.open(out)

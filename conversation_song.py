#!/usr/bin/env python3
# conversation_song.py — 這段對話的旋律
#
# 把這段對話裡建立的每一個東西，
# 按出現順序 hash 到五聲音階，串成一首曲子。
# 這首旋律只屬於這次對話。

import hashlib, colorsys, json, webbrowser

# ── 這段對話建立的東西，按時間順序 ─────────────────────────────

TIMELINE = [
    ('nonsense',       '第一個程式，沒有目的的機器'),
    ('yan',            '言：一個 Lisp 直譯器'),
    ('lsystem',        'L-system 植物'),
    ('parametric',     '知道自己狀態的植物'),
    ('grow_live',      '在終端機裡活著的植物'),
    ('ast_art',        '程式碼的幾何形狀'),
    ('trace_heat',     '執行的熱度'),
    ('05_meta',        '語言理解自己'),
    ('06_quine',       '資料等於自己'),
    ('07_quine_gen',   '程式開始老化'),
    ('roll',           '計算變成樂譜'),
    ('quine_voice',    'quine 唱自己的聲音'),
    ('evolve_voice',   '老化的音在漂移'),
]

# ── 音高 ────────────────────────────────────────────────────────

PENTA = [0, 2, 4, 7, 9]
SCALE = [48 + o * 12 + s for o in range(4) for s in PENTA]

def to_midi(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return SCALE[h % len(SCALE)]

def to_freq(midi):
    return round(440 * (2 ** ((midi - 69) / 12)), 3)

def to_color(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def note_name(midi):
    ns = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B']
    return ns[midi % 12] + str(midi // 12 - 1)

notes = []
for name, desc in TIMELINE:
    midi = to_midi(name)
    notes.append({
        'name':  name,
        'desc':  desc,
        'midi':  midi,
        'freq':  to_freq(midi),
        'color': to_color(name),
        'note':  note_name(midi),
    })

print('這段對話的旋律：')
for n in notes:
    print(f'  {n["name"]:20s}  {n["note"]:5s}  {n["desc"]}')

NOTES_JS = json.dumps(notes)

# ── HTML ────────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>這段對話的旋律</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #07070f;
  color: #bbc;
  font-family: 'Courier New', monospace;
  padding: 50px 60px;
  min-height: 100vh;
}}
h1 {{
  font-size: 13px;
  color: #334;
  letter-spacing: 4px;
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.subtitle {{
  font-size: 11px;
  color: #223;
  margin-bottom: 50px;
  letter-spacing: 1px;
}}

/* ── 時間軸 ── */
.timeline {{
  position: relative;
  margin-bottom: 50px;
}}
.tl-line {{
  position: absolute;
  left: 24px;
  top: 0; bottom: 0;
  width: 1px;
  background: #151525;
}}
.tl-item {{
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px 0 10px 56px;
  position: relative;
  transition: all 0.15s;
  border-radius: 6px;
  margin: 2px 0;
}}
.tl-item.active {{
  background: #0d0d1e;
}}
.tl-dot {{
  position: absolute;
  left: 18px;
  width: 13px; height: 13px;
  border-radius: 50%;
  border: 1px solid currentColor;
  background: #07070f;
  transition: all 0.2s;
  flex-shrink: 0;
}}
.tl-item.active .tl-dot {{
  background: currentColor;
  box-shadow: 0 0 12px currentColor;
  transform: scale(1.3);
}}
.tl-item.done .tl-dot {{
  background: currentColor;
  opacity: 0.4;
}}
.tl-name {{
  font-size: 13px;
  font-weight: bold;
  min-width: 160px;
  transition: color 0.2s;
}}
.tl-note {{
  font-size: 10px;
  min-width: 45px;
  opacity: 0.5;
}}
.tl-desc {{
  font-size: 11px;
  color: #334;
  transition: color 0.2s;
}}
.tl-item.active .tl-desc {{
  color: #667;
}}

/* ── 大音符顯示 ── */
.big-note {{
  text-align: center;
  margin-bottom: 40px;
}}
.big-note-name {{
  font-size: 11px;
  color: #334;
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-bottom: 6px;
  transition: color 0.3s;
}}
.big-pitch {{
  font-size: 64px;
  font-weight: bold;
  color: #1a1a2e;
  transition: color 0.3s, text-shadow 0.3s;
  letter-spacing: -1px;
}}
.big-desc {{
  font-size: 12px;
  color: #223;
  margin-top: 8px;
  transition: color 0.3s;
  min-height: 20px;
}}

/* ── 控制 ── */
.controls {{
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 40px;
}}
button {{
  background: #0e0e1e;
  color: #667;
  border: 1px solid #1a1a2e;
  padding: 9px 22px;
  cursor: pointer;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  letter-spacing: 2px;
  transition: all 0.15s;
}}
button:hover {{ background: #151530; color: #99b; }}
button.playing {{ color: #6cf; border-color: #369; background: #0a1525; }}

label {{ font-size: 11px; color: #334; }}
input[type=range] {{ width: 110px; accent-color: #446; }}
.spd-v {{ font-size: 11px; color: #445; }}

/* ── 進度條 ── */
.progress-bar {{
  height: 2px;
  background: #111120;
  border-radius: 1px;
  margin-bottom: 40px;
  overflow: hidden;
}}
.progress-fill {{
  height: 100%;
  width: 0%;
  background: #334;
  transition: width 0.1s linear, background 0.3s;
  border-radius: 1px;
}}
</style>
</head>
<body>

<h1>這段對話的旋律</h1>
<div class="subtitle">從「隨便寫一個程式」到現在 · 每一個造出來的東西是一個音</div>

<div class="big-note">
  <div class="big-note-name" id="cur-name">—</div>
  <div class="big-pitch" id="cur-pitch">—</div>
  <div class="big-desc" id="cur-desc"></div>
</div>

<div class="progress-bar">
  <div class="progress-fill" id="prog"></div>
</div>

<div class="controls">
  <button id="main-btn" onclick="togglePlay()">▶ 播放</button>
  <label>速度</label>
  <input type="range" id="spd" min="300" max="2000" value="800"
         oninput="document.getElementById('spd-v').textContent=this.value+'ms'">
  <span class="spd-v" id="spd-v">800ms</span>
</div>

<div class="timeline" id="timeline">
  <div class="tl-line"></div>
</div>

<script>
const NOTES = {NOTES_JS};

// ── 建立時間軸 UI ────────────────────────────────────────────────
const tl = document.getElementById('timeline');
NOTES.forEach((n, i) => {{
  const div = document.createElement('div');
  div.className = 'tl-item';
  div.id = `tl-${{i}}`;
  div.style.color = n.color;
  div.innerHTML = `
    <div class="tl-dot" style="color:${{n.color}}"></div>
    <div class="tl-name" style="color:${{n.color}}88">${{n.name}}</div>
    <div class="tl-note">${{n.note}}</div>
    <div class="tl-desc">${{n.desc}}</div>`;
  tl.appendChild(div);
}});

// ── 音訊 ────────────────────────────────────────────────────────
let ac = null;
function getAC() {{
  if (!ac) ac = new (window.AudioContext || window.webkitAudioContext)();
  return ac;
}}

function playNote(freq, when, dur, gain=0.32) {{
  const ctx = getAC();
  const osc = ctx.createOscillator();
  const g   = ctx.createGain();
  osc.type = 'triangle';
  osc.frequency.value = freq;
  g.gain.setValueAtTime(0, when);
  g.gain.linearRampToValueAtTime(gain, when + 0.02);
  g.gain.setValueAtTime(gain, when + dur * 0.75);
  g.gain.linearRampToValueAtTime(0.0001, when + dur);
  osc.connect(g); g.connect(ctx.destination);
  osc.start(when); osc.stop(when + dur + 0.03);
}}

// ── 播放狀態 ────────────────────────────────────────────────────
let playing = false;
let raf = null;
let wallStart = 0;
let totalMs = 0;

function togglePlay() {{
  if (playing) {{ stopPlay(); }} else {{ startPlay(); }}
}}

async function startPlay() {{
  const ctx = getAC();
  if (ctx.state === 'suspended') await ctx.resume();

  const ms  = parseInt(document.getElementById('spd').value);
  const sec = ms / 1000;
  const now = ctx.currentTime + 0.15;

  NOTES.forEach((n, i) => {{
    playNote(n.freq, now + i * sec, sec * 1.3);
  }});

  totalMs   = NOTES.length * ms;
  wallStart = performance.now() - 100;
  playing   = true;

  document.getElementById('main-btn').textContent = '■ 停止';
  document.getElementById('main-btn').classList.add('playing');

  function animate() {{
    if (!playing) return;
    const elapsed = performance.now() - wallStart;
    const idx     = Math.min(Math.floor(elapsed / ms), NOTES.length - 1);
    const prog    = Math.min(elapsed / totalMs, 1);

    // 進度條
    const pf = document.getElementById('prog');
    pf.style.width  = (prog * 100) + '%';
    pf.style.background = NOTES[idx].color;

    // 大音符顯示
    const n = NOTES[idx];
    document.getElementById('cur-name').textContent  = n.name;
    document.getElementById('cur-name').style.color  = n.color;
    document.getElementById('cur-pitch').textContent = n.note;
    document.getElementById('cur-pitch').style.color = n.color + '99';
    document.getElementById('cur-pitch').style.textShadow = `0 0 30px ${{n.color}}66`;
    document.getElementById('cur-desc').textContent  = n.desc;
    document.getElementById('cur-desc').style.color  = n.color + '66';

    // 時間軸
    NOTES.forEach((_, j) => {{
      const el = document.getElementById(`tl-${{j}}`);
      if (j < idx)       el.className = 'tl-item done';
      else if (j === idx) el.className = 'tl-item active';
      else               el.className = 'tl-item';
    }});

    if (prog < 1) {{
      raf = requestAnimationFrame(animate);
    }} else {{
      stopPlay();
    }}
  }}

  raf = requestAnimationFrame(animate);
}}

function stopPlay() {{
  playing = false;
  if (raf) cancelAnimationFrame(raf);
  document.getElementById('main-btn').textContent = '▶ 播放';
  document.getElementById('main-btn').classList.remove('playing');
  document.getElementById('cur-name').textContent  = '—';
  document.getElementById('cur-name').style.color  = '#334';
  document.getElementById('cur-pitch').textContent = '—';
  document.getElementById('cur-pitch').style.color = '#1a1a2e';
  document.getElementById('cur-pitch').style.textShadow = 'none';
  document.getElementById('cur-desc').textContent  = '';
  document.getElementById('prog').style.width      = '0%';
  NOTES.forEach((_, j) => {{
    document.getElementById(`tl-${{j}}`).className = 'tl-item';
  }});
}}
</script>
</body>
</html>"""

out = 'conversation_song.html'
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\n→ {out}')
webbrowser.open(out)

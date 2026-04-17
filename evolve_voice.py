#!/usr/bin/env python3
# evolve_voice.py — quine 的演化旋律
#
# 世代 quine 跑 0–15 代，每代的旋律序列略有不同：
# 第 3 個音是 n 的值，沿著五聲音階緩慢上升。
# 其他音不動。
#
# 結果：16 首旋律串成一首曲子，
# 結構永恆，中間某個音緩慢漂移。

import sys, io, re, hashlib, colorsys, json, webbrowser
sys.path.insert(0, 'yan')
import yan

# ── 音高系統 ────────────────────────────────────────────────────

PENTA = [0, 2, 4, 7, 9]
SCALE = [48 + o * 12 + s for o in range(4) for s in PENTA]

def fn_midi(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return SCALE[h % len(SCALE)]

def num_midi(n):
    return SCALE[int(n) % len(SCALE)]

def midi_freq(midi):
    return round(440 * (2 ** ((midi - 69) / 12)), 3)

def fn_color(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 0.92)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def gen_color(gen, total=16):
    """世代顏色：從冷藍（gen 0）到暖橙（gen total-1）"""
    t = gen / max(total - 1, 1)
    hue = 0.65 - t * 0.55    # 0.65（藍）→ 0.10（橙）
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def note_name(midi):
    ns = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B']
    return ns[midi % 12] + str(midi // 12 - 1)

# ── 捕捉執行序列 ─────────────────────────────────────────────────

base_src = open('yan/examples/07_quine_gen.yn', encoding='utf-8').read()
TOTAL_GENS = 16

def capture_gen(n):
    src = re.sub(r'\d+\)$', f'{n})', base_src)
    log = []
    def hook(expr):
        if isinstance(expr, list) and expr and isinstance(expr[0], yan.Symbol):
            log.append(('fn', str(expr[0])))
        elif isinstance(expr, (int, float)) and not isinstance(expr, bool):
            log.append(('num', int(expr)))
    yan._eval_hook = hook
    env = yan._make_global_env()
    old = sys.stdout; sys.stdout = io.StringIO()
    try:
        for e in yan.parse_all(src): yan.eval_yn(e, env)
    finally:
        sys.stdout = old
        yan._eval_hook = None
    return log

print(f'執行 {TOTAL_GENS} 代...')
all_logs = [capture_gen(n) for n in range(TOTAL_GENS)]
print('完成。')

# ── 把 log 轉成可用的音符資料 ──────────────────────────────────

def log_to_notes(log, gen):
    notes = []
    for kind, val in log:
        if kind == 'fn':
            midi  = fn_midi(val)
            color = fn_color(val)
            label = val
            is_aging = False
        else:   # num
            midi  = num_midi(val)
            # n 的值在每一代不同（val == gen），其他數字固定（val == 1）
            is_aging = (val == gen)
            color = gen_color(gen) if is_aging else '#3a3a5a'
            label = str(val)
        notes.append({
            'kind':     kind,
            'label':    label,
            'freq':     midi_freq(midi),
            'color':    color,
            'note':     note_name(midi),
            'is_aging': is_aging,
        })
    return notes

all_notes = [log_to_notes(all_logs[g], g) for g in range(TOTAL_GENS)]

print('Gen 0 notes:', [(n['label'], n['note']) for n in all_notes[0]])
print('Gen 5 notes:', [(n['label'], n['note']) for n in all_notes[5]])

# ── 生成 HTML ────────────────────────────────────────────────────

all_notes_js = json.dumps(all_notes)

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>演化的旋律</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #07070f;
  color: #bbc;
  font-family: 'Courier New', monospace;
  padding: 40px;
}}
h1 {{
  font-size: 14px;
  color: #445;
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-bottom: 8px;
}}
.subtitle {{
  font-size: 11px;
  color: #333;
  margin-bottom: 40px;
  letter-spacing: 1px;
}}

/* ── 世代計數器 ── */
.gen-display {{
  font-size: 72px;
  font-weight: bold;
  color: #1a1a2e;
  margin-bottom: 4px;
  transition: color 0.3s;
  letter-spacing: -2px;
}}
.gen-label {{
  font-size: 11px;
  color: #334;
  margin-bottom: 30px;
  letter-spacing: 2px;
}}

/* ── 音符列 ── */
.note-row {{
  display: flex;
  gap: 6px;
  margin-bottom: 24px;
  flex-wrap: wrap;
  align-items: flex-end;
}}
.note-block {{
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 10px;
  border-radius: 5px;
  border: 1px solid #111120;
  background: #0b0b16;
  min-width: 60px;
  transition: all 0.1s;
}}
.note-block .nb-label {{
  font-size: 11px;
  margin-bottom: 3px;
  transition: color 0.3s;
}}
.note-block .nb-pitch {{
  font-size: 9px;
  color: #334;
  transition: color 0.2s;
}}
.note-block.active {{
  transform: translateY(-6px) scale(1.1);
  box-shadow: 0 0 20px currentColor;
  border-color: currentColor;
}}
.note-block.aging {{
  border-style: dashed;
}}
.note-block.aging.active {{
  box-shadow: 0 0 30px currentColor, 0 0 60px currentColor;
}}

/* ── 世代歷史條 ── */
.history {{
  display: flex;
  gap: 3px;
  margin-bottom: 30px;
  align-items: flex-end;
}}
.hist-block {{
  width: 18px;
  height: 18px;
  border-radius: 3px;
  opacity: 0.3;
  transition: all 0.3s;
  flex-shrink: 0;
}}
.hist-block.done    {{ opacity: 0.5; }}
.hist-block.current {{ opacity: 1; transform: scale(1.3); box-shadow: 0 0 8px currentColor; }}

/* ── 控制 ── */
.controls {{
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 30px;
}}
button {{
  background: #111126;
  color: #778;
  border: 1px solid #1e1e35;
  padding: 8px 20px;
  cursor: pointer;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  letter-spacing: 1px;
  transition: all 0.15s;
}}
button:hover {{ background: #1a1a35; color: #99b; }}
button.playing {{ color: #6cf; border-color: #369; background: #0a1525; }}

label {{ font-size: 11px; color: #334; }}
input[type=range] {{ width: 100px; accent-color: #446; }}
.spd-val {{ font-size: 11px; color: #445; }}

/* ── 說明 ── */
.legend-row {{
  display: flex;
  gap: 20px;
  margin-top: 20px;
  flex-wrap: wrap;
}}
.leg-item {{
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  color: #334;
}}
.leg-dot {{
  width: 9px; height: 9px;
  border-radius: 2px;
}}
</style>
</head>
<body>

<h1>演化的旋律</h1>
<div class="subtitle">世代 quine 跑 {TOTAL_GENS} 次 · 第三個音隨世代漂移 · 其餘不動</div>

<div class="gen-display" id="gen-num">0</div>
<div class="gen-label" id="gen-sub">第 0 代 / {TOTAL_GENS - 1}</div>

<div class="note-row" id="note-row"></div>

<div class="history" id="hist-row"></div>

<div class="controls">
  <button id="main-btn" onclick="togglePlay()">▶ 播放全部</button>
  <label>每音</label>
  <input type="range" id="spd" min="120" max="800" value="380"
         oninput="document.getElementById('spd-v').textContent=this.value+'ms'">
  <span class="spd-val" id="spd-v">380ms</span>
</div>

<div class="legend-row">
  <div class="leg-item">
    <div class="leg-dot" style="background:#4477cc"></div>
    <span>函式呼叫（固定）</span>
  </div>
  <div class="leg-item">
    <div class="leg-dot"
         style="background:linear-gradient(90deg,#4488ff,#ff8833);border-radius:2px;width:30px;height:9px"></div>
    <span style="margin-left:4px">n 的值（每代上升）</span>
  </div>
  <div class="leg-item">
    <div class="leg-dot" style="background:#3a3a5a"></div>
    <span>常數 1</span>
  </div>
</div>

<script>
const ALL_NOTES = {all_notes_js};
const TOTAL     = ALL_NOTES.length;

// ── 建立 UI ─────────────────────────────────────────────────────
const noteRow = document.getElementById('note-row');
const histRow = document.getElementById('hist-row');

// 歷史條（顏色用第 0 代的 gen_color 演示）
ALL_NOTES.forEach((notes, g) => {{
  const aging = notes.find(n => n.is_aging);
  const color = aging ? aging.color : '#334';
  const div = document.createElement('div');
  div.className = 'hist-block';
  div.id = `hist-${{g}}`;
  div.style.background = color;
  div.title = `第 ${{g}} 代`;
  histRow.appendChild(div);
}});

// ── 音訊 ─────────────────────────────────────────────────────────
let ac = null;
function getAC() {{
  if (!ac) ac = new (window.AudioContext || window.webkitAudioContext)();
  return ac;
}}

function playNote(freq, when, dur, gain=0.30) {{
  const ctx = getAC();
  const osc = ctx.createOscillator();
  const g   = ctx.createGain();
  osc.type = 'triangle';
  osc.frequency.value = freq;
  g.gain.setValueAtTime(gain, when);
  g.gain.setValueAtTime(gain, when + dur * 0.7);
  g.gain.linearRampToValueAtTime(0.0001, when + dur);
  osc.connect(g); g.connect(ctx.destination);
  osc.start(when); osc.stop(when + dur + 0.02);
}}

// ── 播放狀態 ─────────────────────────────────────────────────────
let playing = false;
let rafHandle = null;
let wallStart = 0;

function togglePlay() {{
  if (playing) {{ stopPlay(); }} else {{ startPlay(); }}
}}

async function startPlay() {{
  const ctx = getAC();
  if (ctx.state === 'suspended') await ctx.resume();

  const ms = parseInt(document.getElementById('spd').value);
  const sec = ms / 1000;

  // 計算每代開始時間
  const genOffsets = [];
  let t = ctx.currentTime + 0.15;
  ALL_NOTES.forEach((notes, g) => {{
    genOffsets.push(t);
    notes.forEach((n, i) => {{
      playNote(n.freq, t + i * sec, sec * 1.5, n.is_aging ? 0.40 : 0.26);
    }});
    t += notes.length * sec + sec * 0.5;   // 代與代之間加短停頓
  }});

  const totalMs = (t - ctx.currentTime) * 1000;
  playing = true;
  wallStart = performance.now() - 100;

  document.getElementById('main-btn').textContent = '■ 停止';
  document.getElementById('main-btn').classList.add('playing');

  // 預計算全域時間對應到 (gen, noteIdx)
  const timeline = [];
  ALL_NOTES.forEach((notes, g) => {{
    notes.forEach((n, i) => {{
      timeline.push({{ gen: g, idx: i, tMs: (genOffsets[g] - (ctx.currentTime + 0.15) + i * sec) * 1000 }});
    }});
  }});

  function animate() {{
    if (!playing) return;
    const elapsed = performance.now() - wallStart;

    // 找當前音符
    let cur = null;
    for (let k = timeline.length - 1; k >= 0; k--) {{
      if (elapsed >= timeline[k].tMs) {{ cur = timeline[k]; break; }}
    }}

    if (cur) {{
      const g = cur.gen;
      const i = cur.idx;
      updateDisplay(g, i);
    }}

    if (elapsed < totalMs) {{
      rafHandle = requestAnimationFrame(animate);
    }} else {{
      stopPlay();
    }}
  }}

  rafHandle = requestAnimationFrame(animate);
}}

function stopPlay() {{
  playing = false;
  if (rafHandle) cancelAnimationFrame(rafHandle);
  document.getElementById('main-btn').textContent = '▶ 播放全部';
  document.getElementById('main-btn').classList.remove('playing');
  clearDisplay();
  updateGenNum(0);
}}

// ── 視覺更新 ─────────────────────────────────────────────────────
let lastGen = -1;

function updateDisplay(gen, noteIdx) {{
  // 如果換了世代，重建音符積木
  if (gen !== lastGen) {{
    buildNoteBlocks(gen);
    updateGenNum(gen);
    // 更新歷史條
    for (let g = 0; g < TOTAL; g++) {{
      const hb = document.getElementById(`hist-${{g}}`);
      if (g < gen)  hb.className = 'hist-block done';
      else if (g === gen) hb.className = 'hist-block current';
      else hb.className = 'hist-block';
    }}
    lastGen = gen;
  }}

  // 高亮當前音符
  document.querySelectorAll('.note-block.active')
          .forEach(el => el.classList.remove('active'));
  const nb = document.getElementById(`nb_${{gen}}_${{noteIdx}}`);
  if (nb) nb.classList.add('active');
}}

function buildNoteBlocks(gen) {{
  noteRow.innerHTML = '';
  ALL_NOTES[gen].forEach((n, i) => {{
    const div = document.createElement('div');
    div.className = 'note-block' + (n.is_aging ? ' aging' : '');
    div.id = `nb_${{gen}}_${{i}}`;
    div.style.color = n.color;
    div.style.borderColor = n.color + (n.is_aging ? 'aa' : '33');
    div.innerHTML = `<div class="nb-label" style="color:${{n.color}}">${{n.label}}</div>
                     <div class="nb-pitch">${{n.note}}</div>`;
    noteRow.appendChild(div);
  }});
}}

function updateGenNum(gen) {{
  const d = document.getElementById('gen-num');
  const aging = ALL_NOTES[gen].find(n => n.is_aging);
  d.textContent = String(gen).padStart(2, '0');
  d.style.color = aging ? aging.color + '88' : '#1a1a2e';
  document.getElementById('gen-sub').textContent = `第 ${{gen}} 代 / ${{TOTAL-1}}`;
}}

function clearDisplay() {{
  document.querySelectorAll('.note-block.active').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.hist-block').forEach(el => el.className = 'hist-block');
  buildNoteBlocks(0);
}}

// 初始化
buildNoteBlocks(0);
</script>
</body>
</html>"""

out = 'evolve_voice.html'
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'→ {out}')
webbrowser.open(out)

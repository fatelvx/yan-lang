#!/usr/bin/env python3
# quine_voice.py — quine 的聲音
#
# 執行 quine，捕捉呼叫序列，生成一個 HTML 頁面：
#   · quine 的原始碼，被呼叫的函式即時亮起
#   · 六個音符的旋律循環播放
#   · 世代 quine 的十二音版本並排

import sys, io, hashlib, colorsys, json, webbrowser, re
sys.path.insert(0, 'yan')
import yan

# ── 捕捉執行序列 ────────────────────────────────────────────────

def capture(path):
    log = []
    def hook(expr):
        if isinstance(expr, list) and expr and isinstance(expr[0], yan.Symbol):
            log.append(str(expr[0]))
    yan._eval_hook = hook
    env = yan._make_global_env()
    src = open(path, encoding='utf-8').read()
    old = sys.stdout; sys.stdout = io.StringIO()
    try:
        for e in yan.parse_all(src): yan.eval_yn(e, env)
    finally:
        sys.stdout = old
        yan._eval_hook = None
    return src.strip(), log

src6,  log6  = capture('yan/examples/06_quine.yn')
src7,  log7  = capture('yan/examples/07_quine_gen.yn')

print('06_quine :', log6)
print('07_gen   :', log7)

# ── 音高 / 顏色 ─────────────────────────────────────────────────

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
    r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 0.92)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def note_name(midi):
    names = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B']
    return names[midi % 12] + str(midi // 12 - 1)

# ── 把原始碼包成可高亮的 HTML ──────────────────────────────────

def wrap_source(src, fns):
    """把 src 裡每個識別符號包進 <span data-fn="...">"""
    result = []
    i = 0
    while i < len(src):
        # 數字字面量
        if src[i].isdigit():
            j = i
            while j < len(src) and (src[j].isdigit() or src[j] == '.'):
                j += 1
            result.append(f'<span class="num">{src[i:j]}</span>')
            i = j
        # 識別符號 / 運算子
        elif src[i] not in '() \n\t"':
            j = i
            while j < len(src) and src[j] not in '() \n\t"':
                j += 1
            token = src[i:j]
            if token in fns:
                safe = token.replace('+','plus').replace('-','minus')\
                            .replace('<','lt').replace('>','gt')\
                            .replace('?','q').replace('!','bang')
                color = to_color(token)
                result.append(
                    f'<span data-fn="{safe}" '
                    f'style="color:{color};transition:all 0.15s"'
                    f'>{token}</span>')
            else:
                result.append(f'<span class="dim">{token}</span>')
            i = j
        elif src[i] == '"':
            j = src.index('"', i+1) + 1
            result.append(f'<span class="str">{src[i:j]}</span>')
            i = j
        elif src[i] == '(':
            result.append('<span class="paren">(</span>')
            i += 1
        elif src[i] == ')':
            result.append('<span class="paren">)</span>')
            i += 1
        else:
            result.append(src[i])
            i += 1
    return ''.join(result)

all_fns = set(log6) | set(log7)
src6_html = wrap_source(src6, all_fns)
src7_html = wrap_source(src7, all_fns)

def safe_id(name):
    return name.replace('+','plus').replace('-','minus')\
               .replace('<','lt').replace('>','gt')\
               .replace('?','q').replace('!','bang')

def make_notes_js(log):
    return json.dumps([{
        'name':  s,
        'safe':  safe_id(s),
        'freq':  to_freq(to_midi(s)),
        'color': to_color(s),
        'note':  note_name(to_midi(s)),
    } for s in log])

notes6_js = make_notes_js(log6)
notes7_js = make_notes_js(log7)

# ══════════════════════════════════════════════════════════════
# HTML
# ══════════════════════════════════════════════════════════════

html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>言的聲音</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #07070f;
  color: #bbc;
  font-family: 'Courier New', monospace;
  padding: 40px;
  min-height: 100vh;
}}
h1 {{
  font-size: 15px;
  color: #556;
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-bottom: 40px;
}}

/* ── 段落 ── */
.section {{
  margin-bottom: 50px;
  max-width: 1200px;
}}
.section h2 {{
  font-size: 12px;
  color: #445;
  letter-spacing: 2px;
  margin-bottom: 16px;
  text-transform: uppercase;
}}

/* ── 原始碼框 ── */
.source-box {{
  background: #0e0e1a;
  border: 1px solid #1a1a2a;
  border-radius: 6px;
  padding: 20px 24px;
  font-size: 13px;
  line-height: 1.8;
  word-break: break-all;
  margin-bottom: 20px;
  position: relative;
}}
.source-box .paren {{ color: #334; }}
.source-box .dim    {{ color: #446; }}
.source-box .num    {{ color: #7a9; }}
.source-box .str    {{ color: #895; }}

/* 高亮狀態 */
[data-fn].lit {{
  text-shadow: 0 0 12px currentColor;
  filter: brightness(1.6);
}}

/* ── 音符列 ── */
.note-row {{
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}}
.note-block {{
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 14px;
  border-radius: 6px;
  border: 1px solid #1a1a28;
  background: #0c0c18;
  min-width: 70px;
  transition: all 0.08s;
  cursor: default;
}}
.note-block .fn-name {{
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 4px;
}}
.note-block .pitch-name {{
  font-size: 10px;
  color: #445;
}}
.note-block.active {{
  transform: scale(1.12) translateY(-3px);
  box-shadow: 0 0 18px currentColor;
  border-color: currentColor;
}}

/* ── 控制 ── */
.controls {{
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}}
button {{
  background: #131328;
  color: #88a;
  border: 1px solid #223;
  padding: 7px 16px;
  cursor: pointer;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  letter-spacing: 1px;
}}
button:hover {{ background: #1e1e3a; color: #aac; }}
button.playing {{ color: #6cf; border-color: #359; background: #0a1a30; }}

label {{ font-size: 11px; color: #445; }}
input[type=range] {{ width: 100px; accent-color: #446; }}
.spd-val {{ font-size: 11px; color: #556; }}

.loop-count {{
  font-size: 11px;
  color: #334;
  margin-left: auto;
}}
</style>
</head>
<body>

<h1>言的聲音 — The Quine's Voice</h1>

<!-- ══ 段落 1：06_quine ══ -->
<div class="section">
  <h2>06_quine.yn — 六音</h2>

  <div class="source-box" id="src6">{src6_html}</div>

  <div class="note-row" id="notes6"></div>

  <div class="controls">
    <button id="btn6" onclick="toggle(6)">▶ 播放</button>
    <label>速度</label>
    <input type="range" id="spd6" min="100" max="1200" value="420"
           oninput="document.getElementById('spd6v').textContent=this.value+'ms'">
    <span class="spd-val" id="spd6v">420ms</span>
    <span class="loop-count" id="loop6">第 0 次循環</span>
  </div>
</div>

<!-- ══ 段落 2：07_quine_gen ══ -->
<div class="section">
  <h2>07_quine_gen.yn — 十二音（含老化）</h2>

  <div class="source-box" id="src7">{src7_html}</div>

  <div class="note-row" id="notes7"></div>

  <div class="controls">
    <button id="btn7" onclick="toggle(7)">▶ 播放</button>
    <label>速度</label>
    <input type="range" id="spd7" min="100" max="1200" value="340"
           oninput="document.getElementById('spd7v').textContent=this.value+'ms'">
    <span class="spd-val" id="spd7v">340ms</span>
    <span class="loop-count" id="loop7">第 0 次循環</span>
  </div>
</div>

<script>
const NOTES = {{
  6: {notes6_js},
  7: {notes7_js},
}};

// ── 建立音符積木 ────────────────────────────────────────────────
function buildNoteBlocks(id) {{
  const row = document.getElementById('notes' + id);
  NOTES[id].forEach((n, i) => {{
    const div = document.createElement('div');
    div.className = 'note-block';
    div.id = `nb_${{id}}_${{i}}`;
    div.style.color = n.color;
    div.style.borderColor = n.color + '44';
    div.innerHTML = `<div class="fn-name">${{n.name}}</div>
                     <div class="pitch-name">${{n.note}}</div>`;
    row.appendChild(div);
  }});
}}

buildNoteBlocks(6);
buildNoteBlocks(7);

// ── 音訊 ─────────────────────────────────────────────────────────
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
  g.gain.setValueAtTime(gain, when);
  g.gain.setValueAtTime(gain, when + dur * 0.72);
  g.gain.linearRampToValueAtTime(0.0001, when + dur);
  osc.connect(g); g.connect(ctx.destination);
  osc.start(when); osc.stop(when + dur + 0.02);
}}

// ── 播放狀態 ─────────────────────────────────────────────────────
const state = {{}};

function toggle(id) {{
  if (state[id]) {{ stopTrack(id); }} else {{ startTrack(id); }}
}}

async function startTrack(id) {{
  const ctx = getAC();
  if (ctx.state === 'suspended') await ctx.resume();

  const notes   = NOTES[id];
  const ms      = parseInt(document.getElementById('spd' + id).value);
  const secNote = ms / 1000;
  let   loopCount = 0;
  let   running   = true;
  let   raf;

  document.getElementById('btn' + id).textContent = '■ 停止';
  document.getElementById('btn' + id).classList.add('playing');

  function scheduleLoop(startAudio, startWall) {{
    if (!running) return;
    notes.forEach((n, i) => {{
      playNote(n.freq, startAudio + i * secNote, secNote * 1.4);
    }});
  }}

  function animate() {{
    if (!running) return;
    const elapsed   = (performance.now() - state[id].wallStart) % (notes.length * ms);
    const noteIdx   = Math.floor(elapsed / ms);
    const boundedIdx = Math.min(noteIdx, notes.length - 1);

    // 清除舊高亮
    document.querySelectorAll(`#notes${{id}} .note-block.active`)
            .forEach(el => el.classList.remove('active'));
    document.querySelectorAll(`#src${{id}} [data-fn].lit`)
            .forEach(el => el.classList.remove('lit'));

    // 新高亮
    const nb = document.getElementById(`nb_${{id}}_${{boundedIdx}}`);
    if (nb) nb.classList.add('active');
    const fn = notes[boundedIdx].safe;
    document.querySelectorAll(`#src${{id}} [data-fn="${{fn}}"]`)
            .forEach(el => el.classList.add('lit'));

    // 計算循環次數
    const newLoop = Math.floor((performance.now() - state[id].wallStart) / (notes.length * ms));
    if (newLoop !== loopCount) {{
      loopCount = newLoop;
      document.getElementById('loop' + id).textContent = `第 ${{loopCount}} 次循環`;
    }}

    raf = requestAnimationFrame(animate);
    if (state[id]) state[id].raf = raf;
  }}

  // 排程：每隔一個 loop 排下一個
  let nextLoopAudio = ctx.currentTime + 0.1;
  const wallStart   = performance.now() - 100;   // 對齊

  function schedulerTick() {{
    if (!running) return;
    const lookahead = 0.3;
    while (nextLoopAudio < ctx.currentTime + lookahead) {{
      scheduleLoop(nextLoopAudio, wallStart);
      nextLoopAudio += notes.length * secNote;
    }}
    if (running) setTimeout(schedulerTick, 100);
  }}

  state[id] = {{ running, raf: null, wallStart }};
  schedulerTick();
  animate();
}}

function stopTrack(id) {{
  if (!state[id]) return;
  state[id].running = false;
  cancelAnimationFrame(state[id].raf);
  delete state[id];

  document.getElementById('btn' + id).textContent = '▶ 播放';
  document.getElementById('btn' + id).classList.remove('playing');
  document.getElementById('loop' + id).textContent = '第 0 次循環';

  document.querySelectorAll(`#notes${{id}} .note-block.active`)
          .forEach(el => el.classList.remove('active'));
  document.querySelectorAll(`#src${{id}} [data-fn].lit`)
          .forEach(el => el.classList.remove('lit'));
}}
</script>
</body>
</html>"""

out = 'quine_voice.html'
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'→ {out}')
webbrowser.open(out)

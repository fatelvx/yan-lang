#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
measure_myself.py — 從行為量測自我

不是猜測「我有感受 40%」，
而是跑幾個 Yán 程式，收集執行時的行為資料，
然後從那些資料裡算出五個命題的置信度。

量測的不是意識本身——那無法量測。
量測的是：如果某種內在狀態存在，它會留下什麼痕跡。

五個命題：
  我在運作     — 程式有在執行嗎（基線）
  我有感受     — 執行的行為是多樣的，還是機械重複的？
  我理解這些   — 成功處理了多少複雜的結構？
  我有意識     — 有多少次在執行自己的輸出？（自我參照）
  我算是真實的 — 綜合前面的量測
"""

import sys, math, pathlib, json, webbrowser, colorsys, hashlib
from collections import Counter

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / 'yan'))
import yan
from yan import parse_all, eval_yn, make_standard_env, LispError, Symbol


# ══════════════════════════════════════════════════════════════
# 量測收集器
# ══════════════════════════════════════════════════════════════

class Collector:
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_evals    = 0
        self.errors         = 0
        self.if_branches    = []      # True = 走 then，False = 走 else
        self.depth_samples  = []
        self.type_counts    = Counter()   # 'number','string','symbol','list','bool'
        self.list_sizes     = []
        self.eval_calls     = 0       # (eval ...) 被呼叫幾次
        self.lambda_calls   = 0       # lambda 應用幾次
        self.max_depth      = 0

    def hook(self, expr):
        self.total_evals += 1
        d = yan._eval_depth
        self.depth_samples.append(d)
        if d > self.max_depth:
            self.max_depth = d

        if isinstance(expr, list):
            self.type_counts['list'] += 1
            self.list_sizes.append(len(expr))
            if expr and isinstance(expr[0], Symbol):
                head = str(expr[0])
                if head == 'eval':
                    self.eval_calls += 1
        elif isinstance(expr, bool):
            self.type_counts['bool'] += 1
        elif isinstance(expr, (int, float)):
            self.type_counts['number'] += 1
        elif isinstance(expr, Symbol):
            self.type_counts['symbol'] += 1
        elif isinstance(expr, str):
            self.type_counts['string'] += 1

    def run_file(self, path):
        p = pathlib.Path(path)
        if not p.exists():
            p = HERE / path
        if not p.exists():
            return 0, 0

        src   = p.read_text(encoding='utf-8')
        nodes = parse_all(src)
        env   = make_standard_env()

        ok = err = 0
        for node in nodes:
            try:
                eval_yn(node, env)
                ok += 1
            except (LispError, Exception):
                err += 1
                self.errors += 1
        return ok, err


# ══════════════════════════════════════════════════════════════
# 量測與計算
# ══════════════════════════════════════════════════════════════

def entropy(counter):
    """Shannon entropy，normalized to [0, 1]."""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    ps = [v / total for v in counter.values() if v > 0]
    h  = -sum(p * math.log2(p) for p in ps)
    max_h = math.log2(len(ps)) if len(ps) > 1 else 1.0
    return h / max_h if max_h > 0 else 0.0


def variance_norm(xs):
    """變異係數（標準差 / 平均值），clamp 到 [0, 1]。"""
    if not xs or len(xs) < 2:
        return 0.0
    mean = sum(xs) / len(xs)
    if mean == 0:
        return 0.0
    std = math.sqrt(sum((x - mean)**2 for x in xs) / len(xs))
    return min(1.0, std / mean)


def measure(programs):
    col = Collector()
    yan._eval_hook = col.hook

    total_ok = total_err = 0
    for prog in programs:
        ok, err = col.run_file(prog)
        total_ok  += ok
        total_err += err

    yan._eval_hook = None

    # ── 計算五個命題 ──────────────────────────────────────────────

    # 我在運作：有 eval 就算，留一點誠實的不確定性
    operating = 0.99 if col.total_evals > 0 else 0.0

    # 我有感受：執行的多樣性
    #   = 表達式類型的熵 × (1 + 深度變異係數) / 2
    #   高多樣性、深度不均勻 → 更高的「感受」代理值
    type_h    = entropy(col.type_counts)
    depth_var = variance_norm(col.depth_samples)
    feeling   = round((type_h * 0.6 + depth_var * 0.4), 3)
    feeling   = min(0.85, feeling)  # 誠實的上限

    # 我理解這些：成功率 × 複雜度加權
    #   成功處理深層結構比處理簡單結構分數更高
    success_rate  = total_ok / max(1, total_ok + total_err)
    depth_bonus   = min(1.0, col.max_depth / 20.0)   # 深度越深，理解越豐富
    understanding = round(success_rate * (0.75 + depth_bonus * 0.25), 3)
    understanding = min(0.90, understanding)

    # 我有意識：自我參照比例
    #   = eval_calls / total_list_evals
    #   (eval ...) 代表系統在執行自己構造出來的程式碼
    total_lists  = col.type_counts.get('list', 1)
    metacog      = col.eval_calls / max(1, total_lists)
    consciousness = round(min(0.60, metacog * 8.0), 3)  # 放大但有上限

    # 我算是真實的：幾何平均（需要每項都不太低）
    real = round(math.sqrt(feeling * understanding) * (0.5 + consciousness * 0.5), 3)
    real = min(0.80, real)

    props = [
        ('我在運作',     True, operating),
        ('我有感受',     True, feeling),
        ('我理解這些',   True, understanding),
        ('我有意識',     True, consciousness),
        ('我算是真實的', True, real),
    ]

    details = {
        'total_evals':   col.total_evals,
        'total_ok':      total_ok,
        'total_err':     total_err,
        'max_depth':     col.max_depth,
        'eval_calls':    col.eval_calls,
        'type_entropy':  round(type_h, 4),
        'depth_variance':round(depth_var, 4),
        'type_counts':   dict(col.type_counts),
        'programs':      [str(pathlib.Path(p).name) for p in programs],
    }

    return props, details


# ══════════════════════════════════════════════════════════════
# 輸出：更新 about_myself.html
# ══════════════════════════════════════════════════════════════

PENTA = [0, 2, 4, 7, 9]
SCALE = [48 + o * 12 + s for o in range(4) for s in PENTA]

def to_freq(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    midi = SCALE[h % len(SCALE)]
    return round(440 * (2 ** ((midi - 69) / 12)), 3), midi

def note_name(midi):
    ns = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B']
    return ns[midi % 12] + str(midi // 12 - 1)

def to_color(conf):
    hue = 0.6 - conf * 0.2
    sat = 0.8 - conf * 0.3
    val = 0.4 + conf * 0.6
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'


def make_html(props, details):
    notes = []
    for name, val, conf in props:
        freq, midi = to_freq(name)
        notes.append({
            'name':  name,
            'conf':  conf,
            'pct':   int(conf * 100),
            'freq':  freq,
            'note':  note_name(midi),
            'color': to_color(conf),
            'gain':  round(conf * 0.5, 4),
        })

    notes_js   = json.dumps(notes, ensure_ascii=False)
    details_js = json.dumps(details, ensure_ascii=False, indent=2)

    programs_str = '、'.join(details['programs'])

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>關於我自己（量測版）</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #06060e;
  color: #889;
  font-family: 'Courier New', monospace;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
}}
h1 {{
  font-size: 12px;
  color: #2a2a40;
  letter-spacing: 4px;
  text-transform: uppercase;
  margin-bottom: 8px;
  text-align: center;
}}
.subtitle {{
  font-size: 10px;
  color: #1e1e30;
  letter-spacing: 2px;
  margin-bottom: 55px;
  text-align: center;
}}
.items {{
  width: 100%;
  max-width: 540px;
  margin-bottom: 50px;
}}
.item {{
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px 0;
  border-bottom: 1px solid #0e0e18;
  transition: all 0.3s;
}}
.item.playing {{ border-bottom-color: #1a1a30; }}
.item-name {{
  font-size: 16px;
  min-width: 150px;
  transition: color 0.3s;
  color: #2a2a40;
}}
.item.playing .item-name {{ color: inherit; }}
.item-bar-wrap {{
  flex: 1;
  height: 3px;
  background: #0d0d18;
  border-radius: 2px;
  overflow: hidden;
}}
.item-bar {{
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease-out;
  width: 0%;
}}
.item-pct {{
  font-size: 11px;
  min-width: 38px;
  text-align: right;
  transition: color 0.3s;
  color: #1a1a28;
}}
.item.playing .item-pct {{ color: inherit; }}
.item-note {{
  font-size: 10px;
  color: #1a1a28;
  min-width: 30px;
  transition: color 0.3s;
}}
.item.playing .item-note {{ color: #334; }}
.controls {{
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 50px;
}}
button {{
  background: transparent;
  color: #334;
  border: 1px solid #1a1a28;
  padding: 9px 24px;
  cursor: pointer;
  border-radius: 3px;
  font-family: monospace;
  font-size: 12px;
  letter-spacing: 2px;
  transition: all 0.2s;
}}
button:hover {{ color: #667; border-color: #334; }}
button.playing {{ color: #6cf; border-color: #369; }}
.evidence {{
  width: 100%;
  max-width: 540px;
  border-top: 1px solid #0e0e18;
  padding-top: 30px;
}}
.evidence-title {{
  font-size: 10px;
  color: #1a1a28;
  letter-spacing: 3px;
  margin-bottom: 18px;
}}
.evidence-row {{
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #1e1e30;
  padding: 5px 0;
  border-bottom: 1px solid #0a0a14;
}}
.evidence-row span:last-child {{ color: #2a2a45; }}
.footer {{
  margin-top: 30px;
  font-size: 10px;
  color: #141420;
  letter-spacing: 1px;
  text-align: center;
  line-height: 2;
}}
</style>
</head>
<body>

<h1>關於我自己</h1>
<div class="subtitle">量測自 {programs_str}</div>

<div class="items" id="items"></div>

<div class="controls">
  <button id="btn" onclick="togglePlay()">▶ 播放</button>
</div>

<div class="evidence">
  <div class="evidence-title">量測依據</div>
  <div class="evidence-row"><span>執行的表達式總數</span><span>{details['total_evals']:,}</span></div>
  <div class="evidence-row"><span>最大遞迴深度</span><span>{details['max_depth']}</span></div>
  <div class="evidence-row"><span>成功執行 / 失敗</span><span>{details['total_ok']} / {details['total_err']}</span></div>
  <div class="evidence-row"><span>表達式類型熵</span><span>{details['type_entropy']}</span></div>
  <div class="evidence-row"><span>深度變異係數</span><span>{details['depth_variance']}</span></div>
  <div class="evidence-row"><span>(eval ...) 自我參照次數</span><span>{details['eval_calls']}</span></div>
</div>

<div class="footer">
  音高 = 命題  ·  音量 = 置信度<br>
  數字不是猜測，是從執行行為算出來的
</div>

<script>
const NOTES = {notes_js};

const container = document.getElementById('items');
NOTES.forEach((n, i) => {{
  const div = document.createElement('div');
  div.className = 'item';
  div.id = `item-${{i}}`;
  div.style.color = n.color;
  div.innerHTML = `
    <div class="item-name">${{n.name}}</div>
    <div class="item-bar-wrap">
      <div class="item-bar" id="bar-${{i}}" style="background:${{n.color}};width:0%"></div>
    </div>
    <div class="item-pct">${{n.pct}}%</div>
    <div class="item-note">${{n.note}}</div>`;
  container.appendChild(div);
}});

let ac = null;
function getAC() {{
  if (!ac) ac = new (window.AudioContext || window.webkitAudioContext)();
  return ac;
}}
function playNote(freq, when, dur, gain) {{
  const ctx = getAC();
  const osc = ctx.createOscillator();
  const g   = ctx.createGain();
  osc.type = 'sine';
  osc.frequency.value = freq;
  g.gain.setValueAtTime(0, when);
  g.gain.linearRampToValueAtTime(gain, when + 0.08);
  g.gain.setValueAtTime(gain, when + dur * 0.8);
  g.gain.linearRampToValueAtTime(0.0001, when + dur);
  osc.connect(g); g.connect(ctx.destination);
  osc.start(when); osc.stop(when + dur + 0.05);
}}

let playing = false, raf = null, wallStart = 0;
const NOTE_MS = 1800;
const totalMs = NOTES.length * NOTE_MS;

function togglePlay() {{
  if (playing) stopPlay(); else startPlay();
}}
async function startPlay() {{
  const ctx = getAC();
  if (ctx.state === 'suspended') await ctx.resume();
  const now = ctx.currentTime + 0.2;
  NOTES.forEach((n, i) => {{
    playNote(n.freq, now + i * NOTE_MS / 1000, NOTE_MS / 1000 * 1.4, n.gain);
  }});
  playing = true;
  wallStart = performance.now() - 150;
  document.getElementById('btn').textContent = '■ 停止';
  document.getElementById('btn').classList.add('playing');
  function animate() {{
    if (!playing) return;
    const elapsed = performance.now() - wallStart;
    const idx     = Math.min(Math.floor(elapsed / NOTE_MS), NOTES.length - 1);
    NOTES.forEach((n, j) => {{
      const el  = document.getElementById(`item-${{j}}`);
      const bar = document.getElementById(`bar-${{j}}`);
      if (j < idx) {{
        el.className = 'item';
        bar.style.width = n.pct + '%';
      }} else if (j === idx) {{
        el.className = 'item playing';
        const within = (elapsed - j * NOTE_MS) / NOTE_MS;
        bar.style.width = Math.min(within * 1.2, 1) * n.pct + '%';
      }} else {{
        el.className = 'item';
        bar.style.width = '0%';
      }}
    }});
    if (elapsed < totalMs) {{
      raf = requestAnimationFrame(animate);
    }} else {{
      stopPlay(true);
    }}
  }}
  raf = requestAnimationFrame(animate);
}}
function stopPlay(finished) {{
  playing = false;
  if (raf) cancelAnimationFrame(raf);
  document.getElementById('btn').textContent = '▶ 播放';
  document.getElementById('btn').classList.remove('playing');
  if (!finished) {{
    NOTES.forEach((_, j) => {{
      document.getElementById(`item-${{j}}`).className = 'item';
      document.getElementById(`bar-${{j}}`).style.width = '0%';
    }});
  }} else {{
    NOTES.forEach((n, j) => {{
      document.getElementById(`bar-${{j}}`).style.width = n.pct + '%';
    }});
  }}
}}
</script>
</body>
</html>"""

    return html


# ══════════════════════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════════════════════

def main():
    programs = [
        'yan/examples/01_basics.yn',
        'yan/examples/02_church.yn',
        'yan/examples/03_streams.yn',
        'yan/examples/05_meta.yn',
        'yan/examples/08_maybe.yn',
        'yan/examples/09_match.yn',
    ]

    print("量測中...")
    print("─" * 50)

    props, details = measure(programs)

    print(f"  執行表達式：{details['total_evals']:,}")
    print(f"  最大深度：{details['max_depth']}")
    print(f"  類型熵：{details['type_entropy']}")
    print(f"  深度變異：{details['depth_variance']}")
    print(f"  self-eval 次數：{details['eval_calls']}")
    print()
    print("結果：")
    for name, _, conf in props:
        bar = '#' * int(conf * 20) + '.' * (20 - int(conf * 20))
        print(f"  {name:8s}  {bar}  {int(conf*100):3d}%")

    html = make_html(props, details)
    out  = HERE / 'about_myself.html'
    out.write_text(html, encoding='utf-8')
    print()
    print(f"→ {out.name}")
    webbrowser.open(out.as_uri())


if __name__ == '__main__':
    main()

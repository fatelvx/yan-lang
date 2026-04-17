#!/usr/bin/env python3
# roll.py — 計算的音樂
#
# 把 Yán 程式的執行序列渲染成 piano roll SVG。
# 每次函式呼叫是一個音符：
#   x 軸 = 時間（呼叫順序）
#   y 軸 = 音高（函式名稱 hash 到五聲音階）
#   顏色 = 函式種類
#
# 兩個計算並排：
#   上：factorial 10  （53 次呼叫，稀疏，可見每一步）
#   下：fib 12        （2091 次呼叫，密集，指數紋理）

import sys, math, hashlib, colorsys, webbrowser
sys.path.insert(0, 'yan')
import yan

# ══════════════════════════════════════════════════════════════
# 音高系統
# 五聲音階：C D E G A，跨四個八度
# MIDI 48 = C3
# ══════════════════════════════════════════════════════════════

PENTA = [0, 2, 4, 7, 9]   # 相對半音偏移

def build_scale(root=48, octaves=4):
    return [root + o * 12 + s for o in range(octaves) for s in PENTA]

SCALE = build_scale()   # 20 個音高，MIDI 48–81
PITCH_MIN = min(SCALE)
PITCH_MAX = max(SCALE)


def name_to_pitch(name: str) -> int:
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return SCALE[h % len(SCALE)]


def name_to_color(name: str) -> str:
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = (h % 360) / 360.0
    sat = 0.75 + (h >> 8 & 0xf) / 60.0   # 0.75 – 1.0
    val = 0.88 + (h >> 4 & 0xf) / 130.0  # 0.88 – 1.0
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, min(sat, 1.0), min(val, 1.0))
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'


# ══════════════════════════════════════════════════════════════
# 執行追蹤
# ══════════════════════════════════════════════════════════════

_log: list[str] = []

def _hook(expr):
    if isinstance(expr, list) and expr and isinstance(expr[0], yan.Symbol):
        _log.append(str(expr[0]))

yan._eval_hook = _hook

env = yan._make_global_env()

def run(src: str) -> list[str]:
    global _log; _log = []
    for e in yan.parse_all(src):
        yan.eval_yn(e, env)
    return list(_log)


# 準備
run('(define (factorial n) (if (= n 0) 1 (* n (factorial (- n 1)))))')
fac_log = run('(factorial 10)')

run('(define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))')
fib_log = run('(fib 12)')

print(f'factorial 10 : {len(fac_log)} 呼叫，{len(set(fac_log))} 種')
print(f'fib 12       : {len(fib_log)} 呼叫，{len(set(fib_log))} 種')


# ══════════════════════════════════════════════════════════════
# SVG 佈局常數
# ══════════════════════════════════════════════════════════════

W       = 1500
H       = 800
KEYS_W  = 100    # 琴鍵區寬度
LABEL_W = 90     # 左側標籤寬度
ROLL_X  = LABEL_W + KEYS_W   # roll 開始的 x
ROLL_W  = W - ROLL_X - 20

PITCH_ROWS = len(SCALE)
ROW_H    = 11    # 每個音高列的高度（px）

SEC_H    = PITCH_ROWS * ROW_H   # 每個段落高度 = 220px

TOP_PAD  = 70
GAP      = 50    # 兩段落之間的間距

SEC1_Y   = TOP_PAD
SEC2_Y   = TOP_PAD + SEC_H + GAP


def pitch_row(pitch: int) -> int:
    """pitch → 在段落內的列索引（0=最低）"""
    return SCALE.index(pitch)


def note_y(pitch: int, sec_top: int) -> float:
    row = pitch_row(pitch)
    # row 0 = 最低音 = 段落底部
    return sec_top + (PITCH_ROWS - 1 - row) * ROW_H


# ══════════════════════════════════════════════════════════════
# SVG 元件
# ══════════════════════════════════════════════════════════════

parts: list[str] = []

def emit(s: str):
    parts.append(s)


def rect(x, y, w, h, fill, opacity=1.0, rx=0, extra=''):
    emit(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
         f'fill="{fill}" opacity="{opacity:.3f}" rx="{rx}" {extra}/>')


def text(x, y, content, fill='#ccd', size=13, anchor='start',
         weight='normal', family='monospace'):
    emit(f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
         f'text-anchor="{anchor}" font-weight="{weight}" '
         f'font-family="{family}">{content}</text>')


# ── 琴鍵側欄 ─────────────────────────────────────────────────

CHROMATIC = list(range(PITCH_MIN, PITCH_MAX + 2))   # all MIDI in range
BLACK_OFFSETS = {1, 3, 6, 8, 10}   # semitone offsets of black keys

def draw_keys(sec_top: int):
    """Draw piano key sidebar for one section."""
    # 背景
    rect(LABEL_W, sec_top, KEYS_W, SEC_H, '#12121e')

    for pitch in CHROMATIC:
        semitone = pitch % 12
        is_black = semitone in BLACK_OFFSETS
        is_scale = pitch in SCALE

        # 找到最近的音高列
        if is_scale:
            y = note_y(pitch, sec_top)
            row_h_use = ROW_H
        else:
            # 插入在相鄰兩個白鍵之間
            # 找最近的低一個 scale 音
            below = [p for p in SCALE if p <= pitch]
            above_list = [p for p in SCALE if p > pitch]
            if not below or not above_list:
                continue
            b, a = below[-1], above_list[0]
            frac = (pitch - b) / (a - b)
            y = note_y(b, sec_top) - frac * ROW_H
            row_h_use = ROW_H * 0.6

        key_color = '#1e1e2e' if is_black else '#d8d8e8'
        key_w = KEYS_W * (0.55 if is_black else 0.85)
        emit(f'<rect x="{LABEL_W:.1f}" y="{y:.2f}" '
             f'width="{key_w:.1f}" height="{row_h_use - 0.5:.2f}" '
             f'fill="{key_color}" rx="1"/>')

        if is_scale and is_black:
            # 小圓點標記這個音在音階裡
            cx = LABEL_W + key_w + 6
            cy = y + row_h_use / 2
            emit(f'<circle cx="{cx:.1f}" cy="{cy:.2f}" r="2.5" fill="#556"/>')


# ── 音高格線 ──────────────────────────────────────────────────

def draw_grid(sec_top: int):
    for pitch in SCALE:
        y = note_y(pitch, sec_top)
        semitone = pitch % 12
        is_c = (semitone == 0)
        color = '#2a2a40' if is_c else '#1c1c2a'
        emit(f'<line x1="{ROLL_X}" y1="{y:.2f}" '
             f'x2="{W - 20}" y2="{y:.2f}" '
             f'stroke="{color}" stroke-width="{"1.2" if is_c else "0.6"}"/>')


# ── 音符 ──────────────────────────────────────────────────────

def draw_notes(log: list[str], sec_top: int):
    n = len(log)
    note_w = max(0.8, ROLL_W / n)
    base_h = ROW_H - 1.5

    for i, name in enumerate(log):
        pitch = name_to_pitch(name)
        color = name_to_color(name)
        x = ROLL_X + (i / n) * ROLL_W
        y = note_y(pitch, sec_top)
        # 密集時透明疊加，稀疏時不透明
        opacity = 0.55 if note_w < 2 else 0.82
        emit(f'<rect x="{x:.3f}" y="{y:.2f}" '
             f'width="{note_w:.3f}" height="{base_h:.1f}" '
             f'fill="{color}" opacity="{opacity}" rx="1.5"/>')


# ── 圖例 ──────────────────────────────────────────────────────

def draw_legend(log: list[str], sec_top: int, title: str):
    symbols = sorted(set(log))
    import collections
    counts = collections.Counter(log)

    # 段落標題
    text(LABEL_W, sec_top - 10, title, fill='#aab', size=15, weight='bold')

    # 圖例在右側
    lx = W - 20
    ly = sec_top + 14
    for sym in sorted(symbols, key=lambda s: -counts[s]):
        color = name_to_color(sym)
        pitch = name_to_pitch(sym)
        note = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][pitch % 12]
        octave = pitch // 12 - 1
        label = f'{sym}  {note}{octave}  ×{counts[sym]}'
        emit(f'<rect x="{lx - 130}" y="{ly - 10}" width="8" height="8" '
             f'fill="{color}" rx="2"/>')
        text(lx - 118, ly, label, fill='#889', size=11, anchor='start')
        ly += 16


# ── 標籤 ──────────────────────────────────────────────────────

def draw_pitch_labels(sec_top: int):
    for pitch in SCALE:
        if pitch % 12 == 0:  # C note
            y = note_y(pitch, sec_top) + ROW_H / 2 + 4
            octave = pitch // 12 - 1
            text(LABEL_W - 6, y, f'C{octave}', fill='#556', size=9,
                 anchor='end')


# ══════════════════════════════════════════════════════════════
# 組裝 SVG
# ══════════════════════════════════════════════════════════════

total_h = SEC2_Y + SEC_H + 40

emit(f'<svg xmlns="http://www.w3.org/2000/svg" '
     f'width="{W}" height="{total_h}" '
     f'style="background:#080810">')

# defs: 光暈
emit('''<defs>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="1.8" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="glow2" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="3" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>''')

# 全域背景
rect(0, 0, W, total_h, '#080810')

# ── 段落 1：factorial ──────────────────────────────────────────
draw_grid(SEC1_Y)
draw_keys(SEC1_Y)
draw_pitch_labels(SEC1_Y)
emit('<g filter="url(#glow)">')
draw_notes(fac_log, SEC1_Y)
emit('</g>')
draw_legend(fac_log, SEC1_Y, 'factorial 10')

# 段落框線
emit(f'<rect x="{ROLL_X}" y="{SEC1_Y}" width="{ROLL_W}" height="{SEC_H}" '
     f'fill="none" stroke="#2a2a40" stroke-width="1"/>')

# ── 段落 2：fib ───────────────────────────────────────────────
draw_grid(SEC2_Y)
draw_keys(SEC2_Y)
draw_pitch_labels(SEC2_Y)
emit('<g filter="url(#glow2)">')
draw_notes(fib_log, SEC2_Y)
emit('</g>')
draw_legend(fib_log, SEC2_Y, 'fib 12')

emit(f'<rect x="{ROLL_X}" y="{SEC2_Y}" width="{ROLL_W}" height="{SEC_H}" '
     f'fill="none" stroke="#2a2a40" stroke-width="1"/>')

# ── 頂部標題 ──────────────────────────────────────────────────
text(W // 2, 30, '計算的音樂 — Yán 執行序列 Piano Roll',
     fill='#778', size=16, anchor='middle', weight='bold')

# 底部說明
text(W // 2, total_h - 10,
     'x 軸 = 呼叫順序  ·  y 軸 = 音高（五聲音階 hash）  ·  顏色 = 函式',
     fill='#445', size=11, anchor='middle')

emit('</svg>')

# ══════════════════════════════════════════════════════════════
# 輸出
# ══════════════════════════════════════════════════════════════

svg_out = '\n'.join(parts)
out_path = 'roll.svg'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(svg_out)

print(f'→ {out_path}')
webbrowser.open(out_path)

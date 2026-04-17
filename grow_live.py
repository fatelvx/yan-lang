#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grow_live.py — 在終端機裡看植物生長

每一代新枝都是白色的，然後逐漸變綠、沉入背景。
植物從一條線長成一棵樹。

用法：
  python grow_live.py
  python grow_live.py gothic
  python grow_live.py coral
"""

import sys, os, math, time, random, shutil, pathlib

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from parametric import plant_rule, gothic_rule, coral_rule, F, PUSH, POP, turn


# ══════════════════════════════════════════════════════════════
# 逐代展開
# ══════════════════════════════════════════════════════════════

def expand_one(symbols, rule_fn):
    """展開一代。回傳 (新符號列表, 是否有改變)。"""
    result, changed = [], False
    for sym in symbols:
        if isinstance(sym, tuple) and sym[0] == 'F':
            expanded = rule_fn(sym)
            if len(expanded) == 1 and expanded[0] == sym:
                result.append(sym)
            else:
                changed = True
                result.extend(expanded)
        else:
            result.append(sym)
    return result, changed


# ══════════════════════════════════════════════════════════════
# 海龜 + 年齡追蹤
#
# 在 F 符號上附加「生成代數」。
# F('F', length, energy, depth, generation)
# interpret 時把 generation 帶進線段，用來決定顏色。
# ══════════════════════════════════════════════════════════════

def F_gen(length, energy=1.0, depth=0, generation=0):
    return ('F', length, energy, depth, generation)

def inject_generation(symbols, gen, rule_fn):
    """展開，並在新產生的 F 上標注當前世代。"""
    result, changed = [], False
    for sym in symbols:
        if isinstance(sym, tuple) and sym[0] == 'F':
            # 暫時只取前四個欄位（去掉舊的 generation）
            _, length, energy, depth = sym[:4]
            bare = ('F', length, energy, depth)
            expanded = rule_fn(bare)
            if len(expanded) == 1 and expanded[0] == bare:
                result.append(sym)   # 終端，保留原本的 generation
            else:
                changed = True
                for s in expanded:
                    if isinstance(s, tuple) and s[0] == 'F':
                        _, l, e, d = s[:4]
                        result.append(('F', l, e, d, gen))
                    else:
                        result.append(s)
        else:
            result.append(sym)
    return result, changed


def interpret_with_age(symbols, start_angle=90.0):
    """
    回傳線段列表：(x0, y0, x1, y1, depth, energy, generation)
    """
    segs  = []
    x, y  = 0.0, 0.0
    angle = start_angle
    stack = []

    for sym in symbols:
        if sym == '[':
            stack.append((x, y, angle))
        elif sym == ']':
            if stack: x, y, angle = stack.pop()
        elif isinstance(sym, tuple) and sym[0] == 'F':
            _, length, energy, depth, *rest = sym
            gen = rest[0] if rest else 0
            rad = math.radians(angle)
            nx  = x + length * math.cos(rad)
            ny  = y + length * math.sin(rad)
            segs.append((x, y, nx, ny, depth, energy, gen))
            x, y = nx, ny
        elif isinstance(sym, tuple) and sym[0] == '+':
            angle += sym[1]

    return segs


# ══════════════════════════════════════════════════════════════
# 光柵化 + 顏色
# ══════════════════════════════════════════════════════════════

# ANSI 顏色（以世代年齡為索引）
# 0 = 最新（白），1 = 一代前（亮綠），2 = 兩代前，...
AGE_PALETTE = [
    "\033[97m",          # 0  剛長出：白
    "\033[93m",          # 1  一代前：亮黃
    "\033[92m",          # 2  兩代前：亮綠
    "\033[32m",          # 3  三代前：中綠
    "\033[2;32m",        # 4  四代前：暗綠
    "\033[38;5;22m",     # 5+  更老：深綠
]
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"

def age_color(current_gen, seg_gen):
    age = current_gen - seg_gen
    idx = min(age, len(AGE_PALETTE) - 1)
    return AGE_PALETTE[idx]

def seg_char(dx, dy):
    """根據線段方向選字元。"""
    adx, ady = abs(dx), abs(dy)
    if adx < 0.3: return '│'
    if ady < 0.3: return '─'
    return '\\' if (dx > 0) == (dy > 0) else '/'

def rasterize(segs, width, height, current_gen):
    """把線段畫到字元格，帶顏色。"""
    if not segs:
        return []

    xs  = [c for s in segs for c in (s[0], s[2])]
    ys  = [c for s in segs for c in (s[1], s[3])]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    xspan = xhi - xlo or 1.0
    yspan = yhi - ylo or 1.0

    pad   = 2
    scale = min((width - pad*2) / xspan, (height - pad*2) / yspan)

    def tx(x): return int((x - xlo) * scale) + pad
    def ty(y): return int((yhi - y) * scale) + pad

    # grid: (char, color) 或 None
    grid = [[None] * width for _ in range(height)]

    def plot(px, py, ch, color):
        if 0 <= px < width and 0 <= py < height:
            existing = grid[py][px]
            # 新的覆蓋舊的，但不覆蓋更新的
            if existing is None:
                grid[py][px] = (ch, color)
            else:
                _, old_color = existing
                # 保留顏色更亮（年齡更小）的
                if color < old_color:  # ANSI 字串比較，新的通常更短
                    grid[py][px] = (ch, color)

    for x0, y0, x1, y1, depth, energy, gen in segs:
        color = age_color(current_gen, gen)
        px0, py0 = tx(x0), ty(y0)
        px1, py1 = tx(x1), ty(y1)
        dx, dy   = px1-px0, py1-py0
        adx, ady = abs(dx), abs(dy)
        sx, sy   = (1 if dx>=0 else -1), (1 if dy>=0 else -1)
        ch       = seg_char(dx, dy)
        err      = adx - ady
        cx, cy   = px0, py0
        while True:
            plot(cx, cy, ch, color)
            if cx == px1 and cy == py1: break
            e2 = 2 * err
            if e2 > -ady: err -= ady; cx += sx
            if e2 <  adx: err += adx; cy += sy

    return grid

def render_grid(grid, width):
    """把格子列表轉成一個字串（帶 ANSI 顏色）。"""
    rows = []
    for row in grid:
        line = ""
        for cell in row:
            if cell is None:
                line += " "
            else:
                ch, color = cell
                line += color + ch + RESET
        rows.append(line)
    return "\n".join(rows)


# ══════════════════════════════════════════════════════════════
# 主迴圈
# ══════════════════════════════════════════════════════════════

RULES = {
    'plant':  plant_rule,
    'gothic': gothic_rule,
    'coral':  coral_rule,
}

def main():
    kind    = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in RULES else 'plant'
    rule_fn = RULES[kind]
    seed    = random.randrange(100_000)
    random.seed(seed)

    cols, rows = shutil.get_terminal_size()
    W = cols - 2
    H = rows - 4

    # 初始公理（帶 generation=0）
    symbols = [('F', 100.0, 1.0, 0, 0)]
    gen     = 0

    print(CLEAR, end='')
    print(f"\033[1m{kind}\033[0m  seed={seed}  （按 Ctrl+C 結束）\n")

    try:
        while True:
            segs = interpret_with_age(symbols, start_angle=90.0)
            grid = rasterize(segs, W, H, gen)

            # 移動到第三行，重繪
            sys.stdout.write("\033[3;0H")
            sys.stdout.write(render_grid(grid, W))
            sys.stdout.write(
                f"\n\033[2m第 {gen} 代  {len(segs)} 段  "
                f"{'生長中...' if any(isinstance(s,tuple) and s[0]=='F' and (rule_fn(('F',s[1],s[2],s[3])) != [('F',s[1],s[2],s[3])]) for s in symbols[:5]) else '已完全生長'}\033[0m"
            )
            sys.stdout.flush()

            new_symbols, changed = inject_generation(symbols, gen + 1, rule_fn)
            if not changed:
                # 完全長成，停留幾秒
                time.sleep(4.0)
                break

            symbols = new_symbols
            gen    += 1
            time.sleep(0.9)

    except KeyboardInterrupt:
        pass

    print(f"\n\n\033[2m生長結束。{kind}，seed={seed}，共 {gen} 代。\033[0m")

if __name__ == '__main__':
    main()

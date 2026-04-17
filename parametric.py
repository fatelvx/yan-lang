#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parametric.py — 知道自己狀態的 L-system

每個符號攜帶參數（長度、能量、深度）。
規則是函式，可以感知目前的狀態，做出不同的決定。

根部的邏輯和梢頂的邏輯不一樣。

用法：
  python parametric.py              # 預設植物
  python parametric.py gothic
  python parametric.py coral
  python parametric.py all
"""

import math, random, sys, webbrowser, pathlib

HERE = pathlib.Path(__file__).parent


# ══════════════════════════════════════════════════════════════
# 符號
#
# ('F', length, energy, depth)  — 可繼續生長的枝幹
# ('+', angle)                  — 轉向
# '[' / ']'                     — 儲存 / 還原狀態
#
# F 符號在能量耗盡前會被反覆展開。
# 每次展開後，F 的能量和長度都衰減。
# 終端條件：能量 < 閾值時，規則回傳符號本身（不再展開）。
# ══════════════════════════════════════════════════════════════

def F(length, energy=1.0, depth=0):
    return ('F', length, energy, depth)

def turn(a):
    return ('+', a)

PUSH, POP = '[', ']'


# ══════════════════════════════════════════════════════════════
# 規則
# ══════════════════════════════════════════════════════════════

def plant_rule(sym):
    """
    仿植物。
    能量充足時積極分叉，能量低時只長直線，再低就停止。
    分叉角度隨能量降低而張開（老枝更水平，像受重力影響）。
    """
    _, length, energy, depth = sym

    # 終端：太短或太弱，不再展開
    if energy < 0.06 or length < 2.2:
        return [sym]

    trunk_len    = length * (0.35 + energy * 0.1)
    remain       = length - trunk_len
    trunk_energy = energy * 0.87

    # 角度：精力旺盛時緊湊，疲弱時張開
    base_angle = 18 + (1.0 - energy) * 25
    n_branches = 2 if energy > 0.2 else 1

    result = [F(trunk_len, trunk_energy, depth + 1)]
    for i in range(n_branches):
        sign  = 1 if i == 0 else -1
        angle = sign * (base_angle + random.gauss(0, 4))
        e     = energy * (0.50 + random.random() * 0.22)
        l     = remain * (0.56 + random.random() * 0.2)
        result += [PUSH, turn(angle), F(l, e, depth + 1), POP]

    return result


def gothic_rule(sym):
    """
    大教堂式。主幹持續向上，側枝保守，偶爾多一條直立中枝。
    形狀像柏樹或尖塔。
    """
    _, length, energy, depth = sym

    if energy < 0.07 or length < 2.0:
        return [sym]

    trunk_len = length * 0.50
    remain    = length - trunk_len
    angle     = 12 + random.gauss(0, 2.5)

    result = [F(trunk_len, energy * 0.91, depth + 1)]
    for sign in [1, -1]:
        e = energy * (0.36 + random.random() * 0.18)
        l = remain  * (0.52 + random.random() * 0.22)
        result += [PUSH, turn(sign * angle), F(l, e, depth + 1), POP]

    # 偶爾加一條直立中枝
    if random.random() < 0.38:
        e = energy * (0.52 + random.random() * 0.15)
        l = remain * (0.45 + random.random() * 0.2)
        result += [PUSH, turn(random.gauss(0, 4)), F(l, e, depth + 1), POP]

    return result


def coral_rule(sym):
    """
    珊瑚。角度大，分叉多，開展水平。
    每次分叉有機率產生三叉而非兩叉。
    """
    _, length, energy, depth = sym

    if energy < 0.07 or length < 1.5:
        return [sym]

    trunk_len = length * 0.28
    remain    = length - trunk_len

    n = random.choices([2, 3], weights=[0.55, 0.45])[0]
    result = [F(trunk_len, energy * 0.76, depth + 1)]

    for i in range(n):
        center = (i - (n - 1) / 2) * 40
        angle  = center + random.gauss(0, 8)
        e      = energy * (0.36 + random.random() * 0.3)
        l      = remain * (0.46 + random.random() * 0.34)
        result += [PUSH, turn(angle), F(l, e, depth + 1), POP]

    return result


# ══════════════════════════════════════════════════════════════
# 迭代展開
#
# 每一步把所有可展開的 F 替換為它的展開結果。
# 終端 F（規則回傳自身）保持不變。
# 當沒有任何 F 再改變，停止。
# ══════════════════════════════════════════════════════════════

def expand(axiom, rule_fn, max_steps=22):
    symbols = list(axiom)
    for _ in range(max_steps):
        changed = False
        nxt = []
        for sym in symbols:
            if isinstance(sym, tuple) and sym[0] == 'F':
                expanded = rule_fn(sym)
                if len(expanded) == 1 and expanded[0] == sym:
                    nxt.append(sym)   # 終端，不再展開
                else:
                    changed = True
                    nxt.extend(expanded)
            else:
                nxt.append(sym)
        symbols = nxt
        if not changed:
            break
    return symbols


# ══════════════════════════════════════════════════════════════
# 海龜直譯器
# ══════════════════════════════════════════════════════════════

def interpret(symbols, start_angle=90.0):
    """
    回傳 [(x0,y0,x1,y1,depth,energy), ...]
    所有 F 符號都畫出來，能量 / 深度決定外觀。
    """
    segs  = []
    x, y  = 0.0, 0.0
    angle = start_angle
    stack = []

    for sym in symbols:
        if sym == PUSH:
            stack.append((x, y, angle))
        elif sym == POP:
            if stack:
                x, y, angle = stack.pop()
        elif isinstance(sym, tuple):
            name = sym[0]
            if name == 'F':
                _, length, energy, depth = sym
                rad = math.radians(angle)
                nx  = x + length * math.cos(rad)
                ny  = y + length * math.sin(rad)
                segs.append((x, y, nx, ny, depth, energy))
                x, y = nx, ny
            elif name == '+':
                angle += sym[1]

    return segs


# ══════════════════════════════════════════════════════════════
# SVG 輸出（帶生長動畫）
# ══════════════════════════════════════════════════════════════

def energy_color(energy):
    """
    高能量（根部）→ 深棕綠
    低能量（梢頂）→ 亮黃白
    """
    t = min(1.0, energy)
    r = int(25  + t * 200)
    g = int(55  + t * 185)
    b = int(10  + t * 130)
    return f"#{r:02x}{g:02x}{b:02x}"

def render_svg(segs, width=980, height=920, title=""):
    if not segs:
        return "<svg/>"

    xs  = [c for s in segs for c in (s[0], s[2])]
    ys  = [c for s in segs for c in (s[1], s[3])]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)

    pad   = 50
    scale = min((width  - 2*pad) / max(1e-9, xhi - xlo),
                (height - 2*pad) / max(1e-9, yhi - ylo))

    def tx(x): return round(pad + (x - xlo) * scale, 1)
    def ty(y): return round(pad + (yhi - y) * scale, 1)

    lines = []
    for x0, y0, x1, y1, depth, energy in segs:
        color   = energy_color(energy)
        sw      = max(0.28, energy * 4.2)
        opacity = 0.60 + energy * 0.40
        seg_px  = max(2, round(math.hypot((x1-x0)*scale, (y1-y0)*scale)))
        delay   = f"{depth * 0.058:.3f}s"

        lines.append(
            f'  <line x1="{tx(x0)}" y1="{ty(y0)}" x2="{tx(x1)}" y2="{ty(y1)}" '
            f'stroke="{color}" stroke-width="{sw:.2f}" stroke-linecap="round" '
            f'opacity="{opacity:.2f}" filter="url(#glow)" '
            f'stroke-dasharray="{seg_px}" stroke-dashoffset="{seg_px}">'
            f'<animate attributeName="stroke-dashoffset" '
            f'from="{seg_px}" to="0" dur="0.18s" begin="{delay}" fill="freeze"/>'
            f'</line>'
        )

    caption = (
        f'  <text x="{width//2}" y="{height-10}" text-anchor="middle" '
        f'font-family="monospace" font-size="10" fill="#1a3a1a" opacity="0.5">'
        f'{title}</text>'
    ) if title else ''

    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" style="background:#020704">',
        '  <defs>',
        '    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">',
        '      <feGaussianBlur stdDeviation="1.6" result="blur"/>',
        '      <feMerge>',
        '        <feMergeNode in="blur"/>',
        '        <feMergeNode in="SourceGraphic"/>',
        '      </feMerge>',
        '    </filter>',
        '  </defs>',
    ] + lines + ([caption] if caption else []) + ['</svg>'])


# ══════════════════════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════════════════════

RULES = {
    'plant':  plant_rule,
    'gothic': gothic_rule,
    'coral':  coral_rule,
}

def grow(kind):
    rule_fn = RULES[kind]
    seed    = random.randrange(100_000)
    random.seed(seed)

    print(f"  生長 {kind}（seed={seed}）...", end=" ", flush=True)

    axiom = [F(100.0, 1.0, 0)]
    tree  = expand(axiom, rule_fn)
    segs  = interpret(tree, start_angle=90.0)

    if not segs:
        print("沒有線段。")
        return

    max_d  = max(s[4] for s in segs)
    tips   = sum(1 for s in segs if s[5] < 0.1)   # 低能量 = 梢頂
    title  = f"{kind}  seed={seed}  {len(segs)}段  深度{max_d}"
    svg    = render_svg(segs, title=title)

    out = HERE / f"{kind}.svg"
    out.write_text(svg, encoding='utf-8')
    print(f"完成 → {out.name}  ({len(segs)}段, 深度{max_d}, {tips}個梢頂)")
    webbrowser.open(out.as_uri())

def main():
    args = sys.argv[1:]
    target = args[0] if args else 'plant'

    if target == 'all':
        for k in RULES:
            grow(k)
    elif target in RULES:
        grow(target)
    else:
        print(f"未知系統：{target}")
        print(f"可用：{', '.join(RULES)}，或 all")

if __name__ == '__main__':
    main()

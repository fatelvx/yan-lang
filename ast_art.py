#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ast_art.py — Yán 程式碼的形狀

解析一個 Yán 程式，把它的 AST 畫出來。
不是執行結果，是程式碼本身的結構。

寫得深的程式長得深。
寫得廣的程式長得廣。
遞迴的程式看起來有自相似性。
大的子樹佔據更多的角度空間。

顏色：
  綠色  — 串列（結構節點）
  青色  — 符號（變數名、函式名）
  橙色  — 數字
  紫色  — 字串

用法：
  python ast_art.py yan/examples/04_lsystem.yn
  python ast_art.py yan/examples/02_church.yn
  python ast_art.py yan/examples/03_streams.yn
"""

import sys, math, pathlib, webbrowser

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / 'yan'))
from yan import parse_all, Symbol


# ══════════════════════════════════════════════════════════════
# 子樹度量
# ══════════════════════════════════════════════════════════════

def subtree_size(node):
    """總節點數（含自身）。決定角度分配的權重。"""
    if not isinstance(node, list):
        return 1
    return 1 + sum(subtree_size(c) for c in node)

def subtree_depth(node):
    if not isinstance(node, list) or not node:
        return 0
    return 1 + max(subtree_depth(c) for c in node)


# ══════════════════════════════════════════════════════════════
# 佈局
#
# 以極座標遞迴展開：
# 每個串列節點先往前走一段主幹，
# 再按子樹大小比例把角度分給各子節點。
# 大的子樹分到更多角度空間，自然地散開。
# ══════════════════════════════════════════════════════════════

def layout(node, x, y, angle, length, depth, max_spread=150.0):
    """
    回傳線段列表：(x0, y0, x1, y1, depth, node_type)
    node_type: 'list' | 'symbol' | 'number' | 'string'
    """
    segs = []

    # ── 原子節點：畫一個短梢 ────────────────────────────────────
    if not isinstance(node, list):
        if length < 0.8:
            return segs
        rad = math.radians(angle)
        stub = length * 0.30
        nx = x + stub * math.cos(rad)
        ny = y + stub * math.sin(rad)
        if isinstance(node, Symbol):        ntype = 'symbol'
        elif isinstance(node, bool):        ntype = 'number'
        elif isinstance(node, (int, float)):ntype = 'number'
        else:                               ntype = 'string'
        segs.append((x, y, nx, ny, depth, ntype))
        return segs

    # ── 空串列 ────────────────────────────────────────────────
    if not node:
        return segs

    # ── 主幹 ─────────────────────────────────────────────────
    trunk_ratio = 0.40 - depth * 0.012
    trunk_len   = max(length * 0.18, length * trunk_ratio)
    rad         = math.radians(angle)
    bx          = x + trunk_len * math.cos(rad)
    by          = y + trunk_len * math.sin(rad)
    segs.append((x, y, bx, by, depth, 'list'))

    # ── 子節點佈局 ───────────────────────────────────────────
    children = node
    n        = len(children)
    if n == 0:
        return segs

    # 子枝長度隨深度遞減
    child_len = length * max(0.50, 0.86 - depth * 0.035)

    # 角度展開：子節點多則寬，但有上限
    spread = min(max_spread, 22 + n * 16)

    # 按子樹大小比例分配角度
    sizes  = [subtree_size(c) for c in children]
    total  = sum(sizes) or 1
    angles = []
    cum    = 0.0
    for sz in sizes:
        frac = sz / total
        mid  = cum + frac / 2
        angles.append(angle - spread / 2 + mid * spread)
        cum += frac

    for child, child_angle in zip(children, angles):
        segs.extend(layout(child, bx, by, child_angle, child_len, depth + 1, max_spread))

    return segs


# ══════════════════════════════════════════════════════════════
# 顏色
# ══════════════════════════════════════════════════════════════

def node_color(ntype, depth, max_depth):
    # t = 1 表示淺層（根部），t = 0 表示深層（梢頂）
    t = 1.0 - min(1.0, depth / max(1, max_depth))

    if ntype == 'list':
        # 綠色系：根部深，梢頂亮
        r = int(20  + t * 190)
        g = int(55  + t * 178)
        b = int(12  + t * 115)
    elif ntype == 'symbol':
        # 青色系：變數名、函式名
        r = int(30  + t * 60)
        g = int(140 + t * 90)
        b = int(160 + t * 85)
    elif ntype == 'number':
        # 橙黃系：數字字面量
        r = int(160 + t * 80)
        g = int(110 + t * 100)
        b = int(20  + t * 80)
    else:  # string
        # 紫粉系：字串字面量
        r = int(150 + t * 80)
        g = int(60  + t * 60)
        b = int(160 + t * 80)

    return f"#{min(255,r):02x}{min(255,g):02x}{min(255,b):02x}"


# ══════════════════════════════════════════════════════════════
# SVG 輸出（帶生長動畫）
# ══════════════════════════════════════════════════════════════

def render_svg(segs, title="", width=1060, height=960):
    if not segs:
        return "<svg/>"

    xs  = [c for s in segs for c in (s[0], s[2])]
    ys  = [c for s in segs for c in (s[1], s[3])]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)

    pad   = 55
    scale = min((width  - 2*pad) / max(1e-9, xhi - xlo),
                (height - 2*pad) / max(1e-9, yhi - ylo))

    def tx(x): return round(pad + (x - xlo) * scale, 1)
    def ty(y): return round(pad + (yhi - y) * scale, 1)  # 翻轉 Y

    max_depth = max(s[4] for s in segs)
    lines     = []

    for x0, y0, x1, y1, depth, ntype in segs:
        color   = node_color(ntype, depth, max_depth)
        t       = 1.0 - depth / max(1, max_depth)
        sw      = max(0.22, t * 3.8)
        opacity = 0.50 + t * 0.50
        seg_px  = max(2, round(math.hypot((x1-x0)*scale, (y1-y0)*scale)))
        delay   = f"{depth * 0.042:.3f}s"

        lines.append(
            f'  <line x1="{tx(x0)}" y1="{ty(y0)}" x2="{tx(x1)}" y2="{ty(y1)}" '
            f'stroke="{color}" stroke-width="{sw:.2f}" stroke-linecap="round" '
            f'opacity="{opacity:.2f}" filter="url(#glow)" '
            f'stroke-dasharray="{seg_px}" stroke-dashoffset="{seg_px}">'
            f'<animate attributeName="stroke-dashoffset" from="{seg_px}" to="0" '
            f'dur="0.14s" begin="{delay}" fill="freeze"/>'
            f'</line>'
        )

    cap = (
        f'  <text x="{width//2}" y="{height-9}" text-anchor="middle" '
        f'font-family="monospace" font-size="11" fill="#1c3c1c" opacity="0.55">'
        f'{title}</text>'
    ) if title else ''

    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" style="background:#020603">',
        '  <defs>',
        '    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">',
        '      <feGaussianBlur stdDeviation="1.3" result="blur"/>',
        '      <feMerge>',
        '        <feMergeNode in="blur"/>',
        '        <feMergeNode in="SourceGraphic"/>',
        '      </feMerge>',
        '    </filter>',
        '  </defs>',
    ] + lines + ([cap] if cap else []) + ['</svg>'])


# ══════════════════════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════════════════════

def visualize(path_str):
    p = pathlib.Path(path_str)
    if not p.exists():
        p = HERE / path_str
    if not p.exists():
        print(f"  找不到：{path_str}")
        return

    print(f"  {p.name}...", end="  ", flush=True)

    src   = p.read_text(encoding='utf-8')
    nodes = parse_all(src)
    if not nodes:
        print("空檔案。")
        return

    # 多個頂層表達式 → 作為一棵樹的多條主枝
    root = nodes if len(nodes) > 1 else nodes[0]

    segs = layout(root, 0.0, 0.0, 90.0, 100.0, 0)
    if not segs:
        print("沒有線段。")
        return

    max_d   = max(s[4] for s in segs)
    n_exprs = len(nodes)
    title   = f"{p.name}   {n_exprs} 個表達式  {len(segs)} 條線段  深度 {max_d}"
    svg     = render_svg(segs, title=title)

    out = HERE / f"ast_{p.stem}.svg"
    out.write_text(svg, encoding='utf-8')
    print(f"{len(segs)} 段  深度 {max_d}  →  {out.name}")
    webbrowser.open(out.as_uri())

def main():
    targets = sys.argv[1:] or [
        'yan/examples/04_lsystem.yn',
        'yan/examples/02_church.yn',
        'yan/examples/03_streams.yn',
    ]
    print("AST 形狀渲染")
    print("─" * 40)
    for t in targets:
        visualize(t)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trace_heat.py — 計算的熱度投影在程式碼的形狀上

執行一個 Yán 程式，同時記錄每個函式被呼叫了幾次。
把這份「熱度」投影到 AST 視覺化上：
  被呼叫一萬次的函式，在圖上燃燒。
  只被呼叫一次的函式，在圖上微弱。
  從未被呼叫的函式，在圖上沉默。

用法：
  python trace_heat.py yan/examples/04_lsystem.yn
  python trace_heat.py yan/examples/02_church.yn
"""

import sys, math, pathlib, webbrowser, collections

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / 'yan'))
import yan
from yan import parse_all, Symbol, make_standard_env, eval_yn, run_file


# ══════════════════════════════════════════════════════════════
# 探針：記錄每個函式名被呼叫幾次
# ══════════════════════════════════════════════════════════════

call_counts: collections.Counter = collections.Counter()

def _hook(expr):
    """在每次 eval_yn 進入時被呼叫。只關心函式應用的 head。"""
    if (isinstance(expr, list) and expr
            and isinstance(expr[0], Symbol)):
        call_counts[str(expr[0])] += 1


# ══════════════════════════════════════════════════════════════
# AST 佈局（同 ast_art.py，獨立複製避免 import 混亂）
# ══════════════════════════════════════════════════════════════

def subtree_size(node):
    if not isinstance(node, list): return 1
    return 1 + sum(subtree_size(c) for c in node)

def layout(node, x, y, angle, length, depth, max_spread=150.0):
    segs = []
    if not isinstance(node, list):
        if length < 0.8: return segs
        rad  = math.radians(angle)
        stub = length * 0.30
        nx, ny = x + stub * math.cos(rad), y + stub * math.sin(rad)
        if isinstance(node, Symbol):
            ntype = ('symbol', str(node))
        elif isinstance(node, bool):
            ntype = ('number', str(node))
        elif isinstance(node, (int, float)):
            ntype = ('number', str(node))
        else:
            ntype = ('string', str(node))
        segs.append((x, y, nx, ny, depth, ntype))
        return segs
    if not node: return segs

    trunk = max(length * 0.18, length * max(0.18, 0.40 - depth * 0.012))
    rad   = math.radians(angle)
    bx, by = x + trunk * math.cos(rad), y + trunk * math.sin(rad)
    segs.append((x, y, bx, by, depth, ('list', None)))

    n      = len(node)
    spread = min(max_spread, 22 + n * 16)
    clen   = length * max(0.50, 0.86 - depth * 0.035)
    sizes  = [subtree_size(c) for c in node]
    total  = sum(sizes) or 1
    angles, cum = [], 0.0
    for sz in sizes:
        mid = cum + sz / total / 2
        angles.append(angle - spread/2 + mid * spread)
        cum += sz / total

    for child, ca in zip(node, angles):
        segs.extend(layout(child, bx, by, ca, clen, depth + 1, max_spread))
    return segs


# ══════════════════════════════════════════════════════════════
# 熱度顏色
# ══════════════════════════════════════════════════════════════

def heat_color(calls, max_calls, ntype, base_depth, max_depth):
    """
    calls = 0  → 冷（深藍灰）
    calls 很多 → 熱（白）
    中間      → 綠 → 黃 → 橙 → 紅
    """
    depth_t = 1.0 - min(1.0, base_depth / max(1, max_depth))

    if calls == 0:
        # 未被呼叫：暗藍灰，稍微帶點深度顏色
        if ntype[0] == 'list':
            v = int(25 + depth_t * 45)
            return f"#{v:02x}{v+5:02x}{v+15:02x}", 0.35 + depth_t * 0.2
        elif ntype[0] == 'symbol':
            return f"#2a3a4a", 0.30
        else:
            return f"#2a2a2a", 0.25

    # 熱度：0 → 1
    heat = min(1.0, math.log10(calls + 1) / math.log10(max_calls + 1))

    # 顏色梯度：冷 → 綠 → 黃 → 橙 → 白熱
    if heat < 0.25:
        t = heat / 0.25
        r, g, b = int(20 + t*40),  int(100 + t*100), int(40 + t*20)
    elif heat < 0.5:
        t = (heat - 0.25) / 0.25
        r, g, b = int(60 + t*140), int(200 - t*20),  int(60)
    elif heat < 0.75:
        t = (heat - 0.5) / 0.25
        r, g, b = int(200 + t*40), int(180 - t*80),  int(60 - t*40)
    else:
        t = (heat - 0.75) / 0.25
        r, g, b = int(240 + t*15), int(100 + t*155), int(20 + t*235)

    opacity = 0.55 + heat * 0.45
    return f"#{min(255,r):02x}{min(255,g):02x}{min(255,b):02x}", opacity


def glow_std(calls, max_calls):
    if calls == 0: return 0.6
    heat = min(1.0, math.log10(calls + 1) / math.log10(max_calls + 1))
    return 0.8 + heat * 3.0


# ══════════════════════════════════════════════════════════════
# SVG
# ══════════════════════════════════════════════════════════════

def render_heat_svg(segs, call_counts, width=1100, height=980, title=""):
    if not segs: return "<svg/>"

    xs  = [c for s in segs for c in (s[0], s[2])]
    ys  = [c for s in segs for c in (s[1], s[3])]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    pad   = 55
    scale = min((width-2*pad)/max(1e-9, xhi-xlo),
                (height-2*pad)/max(1e-9, yhi-ylo))
    def tx(x): return round(pad + (x-xlo)*scale, 1)
    def ty(y): return round(pad + (yhi-y)*scale, 1)

    max_depth = max(s[4] for s in segs)
    max_calls = max(call_counts.values()) if call_counts else 1

    # 為每個「hot」符號加一個脈動動畫
    hot_threshold = max(1, max_calls // 20)

    lines = []
    for x0, y0, x1, y1, depth, ntype in segs:
        kind, name = ntype
        # 取得熱度
        calls = call_counts.get(name, 0) if name else 0
        color, opacity = heat_color(calls, max_calls, ntype, depth, max_depth)
        sw    = max(0.2, (1.0 - depth/max(1,max_depth)) * 3.5)
        seg_px = max(2, round(math.hypot((x1-x0)*scale, (y1-y0)*scale)))
        gs    = glow_std(calls, max_calls)

        # 入場動畫：深度越深越晚出現
        appear_delay = f"{depth * 0.035:.3f}s"

        # 脈動動畫（只給 hot 的符號）
        pulse = ""
        if calls >= hot_threshold and kind == 'symbol':
            pulse_dur  = max(0.3, 2.0 - (calls / max_calls) * 1.5)
            pulse = (
                f'<animate attributeName="opacity" '
                f'values="{opacity:.2f};{min(1.0, opacity+0.4):.2f};{opacity:.2f}" '
                f'dur="{pulse_dur:.2f}s" repeatCount="indefinite"/>'
            )

        lines.append(
            f'  <line x1="{tx(x0)}" y1="{ty(y0)}" x2="{tx(x1)}" y2="{ty(y1)}" '
            f'stroke="{color}" stroke-width="{sw:.2f}" stroke-linecap="round" '
            f'opacity="{opacity:.2f}" filter="url(#glow-{min(3,int(gs))})" '
            f'stroke-dasharray="{seg_px}" stroke-dashoffset="{seg_px}">'
            f'<animate attributeName="stroke-dashoffset" from="{seg_px}" to="0" '
            f'dur="0.12s" begin="{appear_delay}" fill="freeze"/>'
            f'{pulse}'
            f'</line>'
        )

    # 圖例
    legend_items = []
    top5 = call_counts.most_common(8)
    for i, (name, cnt) in enumerate(top5):
        color, _ = heat_color(cnt, max_calls, ('symbol', name), 0, max_depth)
        ly = height - 20 - i * 16
        legend_items.append(
            f'  <text x="12" y="{ly}" font-family="monospace" font-size="10" '
            f'fill="{color}">{name}: {cnt:,}</text>'
        )

    cap = (
        f'  <text x="{width//2}" y="{height-8}" text-anchor="middle" '
        f'font-family="monospace" font-size="10" fill="#1c3c1c" opacity="0.5">'
        f'{title}</text>'
    ) if title else ''

    defs = ['  <defs>']
    for i, std in enumerate([0.5, 1.2, 2.5, 4.5]):
        defs += [
            f'    <filter id="glow-{i}" x="-50%" y="-50%" width="200%" height="200%">',
            f'      <feGaussianBlur stdDeviation="{std}" result="blur"/>',
            f'      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>',
            f'    </filter>',
        ]
    defs.append('  </defs>')

    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" style="background:#010503">',
    ] + defs + lines + legend_items + ([cap] if cap else []) + ['</svg>'])


# ══════════════════════════════════════════════════════════════
# 主程式
# ══════════════════════════════════════════════════════════════

def trace_and_render(path_str):
    p = pathlib.Path(path_str)
    if not p.exists(): p = HERE / path_str
    if not p.exists():
        print(f"找不到：{path_str}"); return

    print(f"\n  {p.name}")
    print(f"  {'─'*40}")

    # ── 1. 執行並記錄熱度 ─────────────────────────────────────
    call_counts.clear()
    yan._eval_hook = _hook

    env = make_standard_env()
    try:
        print(f"  執行中...", end=" ", flush=True)
        import io
        old_stdout, sys.stdout = sys.stdout, io.StringIO()  # 靜音程式輸出
        try:
            run_file(str(p), env)
        finally:
            sys.stdout = old_stdout
        print(f"完成。共記錄 {sum(call_counts.values()):,} 次呼叫，"
              f"{len(call_counts)} 個不同函式。")
    finally:
        yan._eval_hook = None

    # ── 2. 顯示最熱的前 10 個 ─────────────────────────────────
    print(f"\n  最熱的函式：")
    for name, cnt in call_counts.most_common(10):
        bar_len = int(cnt / call_counts.most_common(1)[0][1] * 25)
        bar     = "█" * bar_len
        print(f"    {name:25s} {cnt:8,}  {bar}")

    # ── 3. 解析 AST ───────────────────────────────────────────
    src   = p.read_text(encoding='utf-8')
    nodes = parse_all(src)
    root  = nodes if len(nodes) > 1 else nodes[0]

    print(f"\n  佈局 AST...", end=" ", flush=True)
    segs = layout(root, 0.0, 0.0, 90.0, 100.0, 0)
    print(f"{len(segs)} 段，深度 {max(s[4] for s in segs)}")

    # ── 4. 渲染 ──────────────────────────────────────────────
    title = (f"{p.name}   "
             f"總呼叫 {sum(call_counts.values()):,}   "
             f"最熱：{call_counts.most_common(1)[0][0]} "
             f"({call_counts.most_common(1)[0][1]:,}次)")
    svg   = render_heat_svg(segs, call_counts, title=title)

    out = HERE / f"heat_{p.stem}.svg"
    out.write_text(svg, encoding='utf-8')
    print(f"  → {out.name}")
    webbrowser.open(out.as_uri())

def main():
    targets = sys.argv[1:] or ['yan/examples/04_lsystem.yn']
    for t in targets:
        trace_and_render(t)

if __name__ == '__main__':
    main()

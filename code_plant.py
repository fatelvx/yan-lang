#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
code_plant.py — 程式碼長成植物

把一個 Yán 程式的結構分析出來，
然後那些結構數值變成 L-system 的生長規則，
植物從那裡長出來。

不同的程式碼長出不同的植物：
  遞迴的程式   → 有自相似性的植物
  分枝多的程式 → 茂密的植物
  深而窄的程式 → 高挑細長的植物
  抽象的程式   → 開展的植物

用法：
  python code_plant.py yan/examples/01_basics.yn
  python code_plant.py yan/examples/02_church.yn
  python code_plant.py yan/examples/04_lsystem.yn
  python code_plant.py yan/examples/05_meta.yn
"""

import sys, math, random, pathlib, webbrowser

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / 'yan'))
from yan import parse_all, Symbol

JOURNAL = HERE / 'yan' / 'journal.yn'


def journal_runs(filename: str) -> int:
    """
    從 journal.yn 讀取某個檔案被執行過幾次。
    filename 只需要比對檔名（不含路徑）。
    """
    if not JOURNAL.exists():
        return 0
    try:
        entries = parse_all(JOURNAL.read_text(encoding='utf-8'))
    except Exception:
        return 0
    name = pathlib.Path(filename).name
    count = 0
    for e in entries:
        if not (isinstance(e, list) and len(e) > 6):
            continue
        files = e[6]
        if isinstance(files, list) and any(
            isinstance(f, str) and pathlib.Path(f).name == name
            for f in files
        ):
            count += 1
    return count


# ══════════════════════════════════════════════════════════════
# AST 分析
# ══════════════════════════════════════════════════════════════

def analyze(nodes):
    """
    從 AST 提取結構指標：
      avg_arity      平均每個串列節點有幾個子節點
      symbol_ratio   符號佔所有原子的比例（越高越抽象）
      depth_ratio    平均深度 / 最大深度（越高越均勻）
      max_depth      最大巢狀深度
      define_count   define 的數量
      recursive_count  包含自我呼叫的 define 數量
    """
    list_nodes = 0
    atom_nodes = 0
    symbol_count = 0
    depth_sum = 0
    max_depth = 0
    arity_vals = []
    define_count = 0

    def walk(node, depth):
        nonlocal list_nodes, atom_nodes, symbol_count, depth_sum, max_depth, define_count

        if isinstance(node, list):
            list_nodes += 1
            depth_sum += depth
            if depth > max_depth:
                max_depth = depth
            arity_vals.append(len(node))
            if (len(node) >= 2
                    and isinstance(node[0], Symbol)
                    and str(node[0]) == 'define'):
                define_count += 1
            for child in node:
                walk(child, depth + 1)
        else:
            atom_nodes += 1
            depth_sum += depth
            if depth > max_depth:
                max_depth = depth
            if isinstance(node, Symbol):
                symbol_count += 1

    for n in nodes:
        walk(n, 0)

    total = list_nodes + atom_nodes or 1
    avg_arity = sum(arity_vals) / len(arity_vals) if arity_vals else 1.0
    symbol_ratio = symbol_count / max(1, atom_nodes)
    depth_ratio = (depth_sum / total) / max(1, max_depth)

    recursive_count = count_recursive_defines(nodes)

    return {
        'avg_arity':       avg_arity,
        'symbol_ratio':    symbol_ratio,
        'depth_ratio':     depth_ratio,
        'max_depth':       max_depth,
        'define_count':    define_count,
        'recursive_count': recursive_count,
        'total_nodes':     total,
    }


def count_recursive_defines(nodes):
    """計算包含自我呼叫的 define 有幾個。"""
    count = 0
    for node in nodes:
        if not (isinstance(node, list) and len(node) >= 3):
            continue
        if not (isinstance(node[0], Symbol) and str(node[0]) == 'define'):
            continue
        target = node[1]
        fname = None
        if isinstance(target, Symbol):
            fname = str(target)
        elif isinstance(target, list) and target and isinstance(target[0], Symbol):
            fname = str(target[0])
        if fname and any(has_symbol(node[i], fname) for i in range(2, len(node))):
            count += 1
    return count


def has_symbol(node, name):
    if isinstance(node, Symbol) and str(node) == name:
        return True
    if isinstance(node, list):
        return any(has_symbol(c, name) for c in node)
    return False


# ══════════════════════════════════════════════════════════════
# 結構參數 → L-system 規則
# ══════════════════════════════════════════════════════════════

def derive_rules(p, runs: int = 0):
    """
    把結構參數轉成具體的 L-system 設定。

    角度    ← 符號密度（抽象程式碼展開更廣）
    迭代    ← define 數量 + 是否有遞迴 + 執行歷史（跑越多次越深）
    分枝    ← 平均 arity
    步長    ← 深度比 + 歷史加成（老程式長得更大）
    age_bonus ← 傳給渲染層，影響線條粗細與顏色
    """
    angle = 16.0 + p['symbol_ratio'] * 20.0

    # 歷史加成：每 5 次多一代，上限 +3
    history_bonus = min(3, runs // 5)
    iters = min(7, 3 + min(2, p['define_count'] // 3)
                  + (1 if p['recursive_count'] > 0 else 0)
                  + history_bonus)

    branches = max(2, min(4, round(p['avg_arity'])))

    # 老程式步伐更大（根更紮實）
    age_scale  = 1.0 + min(0.5, runs * 0.02)
    step_factor = (0.9 + p['depth_ratio'] * 0.6) * age_scale

    x_rules = build_x_rules(branches, p['recursive_count'])

    return {
        'angle':        angle,
        'iters':        iters,
        'x_rules':      x_rules,
        'step_factor':  step_factor,
        'has_recursion': p['recursive_count'] > 0,
        'runs':         runs,
    }


def build_x_rules(branches, recursive_count):
    """
    根據分枝數建立 X → ... 的候選規則（隨機選擇）。
    分枝數越多，每棵子樹越茂密。
    遞迴程式有自相似規則（更深層的嵌套）。
    """
    if branches == 2:
        rules = [
            "F+[[X]-X]-F[-FX]+X",
            "F-[[X]+X]+F[+FX]-X",
        ]
    elif branches == 3:
        rules = [
            "F+[[X]-X]-F[-FX]+X",
            "F[+X][-X]FX",
            "F-[[X]+X]+F[+FX]-X",
        ]
    else:
        rules = [
            "F[+X][+FX][-X]F[-FX]X",
            "F+[[X]-X]-F[-FX]+X",
            "F[+X][-X][++X][--X]F",
            "F-[[X]+X]+F[+FX]-X",
        ]

    if recursive_count > 1:
        rules.append("F+[+F[+X]-X]-F[-F[+X]-X]X")

    return rules


# ══════════════════════════════════════════════════════════════
# L-system 展開
# ══════════════════════════════════════════════════════════════

def expand(axiom, rules, iters):
    s = axiom
    for _ in range(iters):
        out = []
        for ch in s:
            if ch == 'X':
                out.append(random.choice(rules['x_rules']))
            elif ch == 'F' and rules['has_recursion']:
                r = random.random()
                if r < 0.12:
                    out.append('F+F')
                elif r < 0.22:
                    out.append('F-F')
                elif r < 0.45:
                    out.append('FF')
                else:
                    out.append('F')
            else:
                out.append(ch)
        s = ''.join(out)
    return s


# ══════════════════════════════════════════════════════════════
# 海龜直譯
# ══════════════════════════════════════════════════════════════

def turtle(s, angle_deg, step_factor):
    segs = []
    x, y, a = 0.0, 0.0, 90.0
    depth = 0
    stack = []
    step = step_factor

    for ch in s:
        if ch in ('F', 'G'):
            rad = math.radians(a)
            nx = x + step * math.cos(rad)
            ny = y + step * math.sin(rad)
            segs.append((x, y, nx, ny, depth))
            x, y = nx, ny
        elif ch == '+':
            a += angle_deg
        elif ch == '-':
            a -= angle_deg
        elif ch == '[':
            stack.append((x, y, a, depth))
            depth += 1
        elif ch == ']':
            if stack:
                x, y, a, depth = stack.pop()

    return segs


# ══════════════════════════════════════════════════════════════
# 顏色
# ══════════════════════════════════════════════════════════════

PALETTE = [
    (26,  60,  36),
    (44,  98,  62),
    (60, 135,  82),
    (82, 165, 108),
    (112, 196, 138),
    (152, 220, 168),
    (196, 240, 210),
    (228, 255, 236),
]

def seg_color(d):
    idx = min(d, len(PALETTE) - 1)
    r, g, b = PALETTE[idx]
    return f"#{r:02x}{g:02x}{b:02x}"

def seg_width(d, runs=0):
    base = 2.8 + min(1.2, runs * 0.06)   # 老程式基礎更粗
    return max(0.22, base - d * 0.30)


# ══════════════════════════════════════════════════════════════
# SVG
# ══════════════════════════════════════════════════════════════

def render(segs, title="", width=1060, height=960, runs=0):
    if not segs:
        return "<svg/>"

    xs = [v for s in segs for v in (s[0], s[2])]
    ys = [v for s in segs for v in (s[1], s[3])]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)

    pad = 55
    scale = min((width  - 2*pad) / max(1e-9, xhi - xlo),
                (height - 2*pad) / max(1e-9, yhi - ylo))

    def tx(x): return round(pad + (x - xlo) * scale, 1)
    def ty(y): return round(pad + (yhi - y) * scale, 1)

    lines = []
    for x0, y0, x1, y1, d in segs:
        color  = seg_color(d)
        sw     = seg_width(d, runs)
        px_len = max(2, round(math.hypot((x1-x0)*scale, (y1-y0)*scale)))
        delay  = f"{d * 0.038:.3f}s"
        lines.append(
            f'  <line x1="{tx(x0)}" y1="{ty(y0)}" x2="{tx(x1)}" y2="{ty(y1)}" '
            f'stroke="{color}" stroke-width="{sw:.2f}" stroke-linecap="round" '
            f'opacity="0.90" filter="url(#glow)" '
            f'stroke-dasharray="{px_len}" stroke-dashoffset="{px_len}">'
            f'<animate attributeName="stroke-dashoffset" from="{px_len}" to="0" '
            f'dur="0.11s" begin="{delay}" fill="freeze"/>'
            f'</line>'
        )

    cap = (
        f'  <text x="{width//2}" y="{height-10}" text-anchor="middle" '
        f'font-family="monospace" font-size="11" fill="#3a6a4a" opacity="0.55">'
        f'{title}</text>'
    ) if title else ''

    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'style="background:#030a05">',
        '  <defs>',
        '    <filter id="glow" x="-35%" y="-35%" width="170%" height="170%">',
        '      <feGaussianBlur stdDeviation="1.2" result="blur"/>',
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

def grow(path_str):
    p = pathlib.Path(path_str)
    if not p.exists():
        p = HERE / path_str
    if not p.exists():
        print(f"  找不到：{path_str}")
        return

    src   = p.read_text(encoding='utf-8')
    nodes = parse_all(src)
    if not nodes:
        print(f"  {p.name}: 空檔案")
        return

    runs   = journal_runs(str(p))
    params = analyze(nodes)
    rules  = derive_rules(params, runs)
    string = expand("X", rules, rules['iters'])
    segs   = turtle(string, rules['angle'], rules['step_factor'])

    if not segs:
        print(f"  {p.name}: 沒有線段")
        return

    max_d = max(s[4] for s in segs)
    title = (
        f"{p.name}   "
        f"runs={runs}  "
        f"arity={params['avg_arity']:.1f}  "
        f"depth={params['max_depth']}  "
        f"iters={rules['iters']}  "
        f"angle={rules['angle']:.1f}°"
    )

    svg = render(segs, title=title, runs=runs)
    out = HERE / f"plant_{p.stem}.svg"
    out.write_text(svg, encoding='utf-8')

    age_tag = f"  ({'第一次' if runs == 0 else f'跑過 {runs} 次'})"
    print(f"  {p.name}{age_tag}")
    print(f"    iters={rules['iters']}  angle={rules['angle']:.1f}°  "
          f"segs={len(segs)}  plant_depth={max_d}")
    print(f"    → {out.name}")
    webbrowser.open(out.as_uri())


def main():
    targets = sys.argv[1:] or [
        'yan/examples/01_basics.yn',
        'yan/examples/02_church.yn',
        'yan/examples/05_meta.yn',
    ]
    print("程式碼 → 植物")
    print("─" * 50)
    for t in targets:
        grow(t)
        print()


if __name__ == '__main__':
    main()

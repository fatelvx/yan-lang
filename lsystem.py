#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L-system 渲染器

L-system（Lindenmayer system）：
  一套符號重寫規則，反覆套用後產生複雜字串，
  再解讀為海龜作圖指令，得到分形圖案。

幾條規則，就能長出樹、雪花、龍。
"""

import sys, math, io
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

# ── ANSI 顏色 ────────────────────────────────────────────────────

def _c(code): return f"\033[{code}m"
RESET   = _c(0)
BOLD    = _c(1)
DIM     = _c(2)
COLORS  = [_c(f"38;5;{n}") for n in [46, 83, 120, 155, 190, 226, 220, 214]]


# ── L-system 定義 ────────────────────────────────────────────────

@dataclass
class LSystem:
    name:    str
    axiom:   str
    rules:   Dict[str, str]
    angle:   float          # 轉角（度）
    iters:   int            # 預設迭代次數
    note:    str = ""


SYSTEMS: Dict[str, LSystem] = {

    "plant": LSystem(
        name  = "植物",
        axiom = "X",
        rules = {
            "X": "F+[[X]-X]-F[-FX]+X",
            "F": "FF",
        },
        angle = 25.0,
        iters = 5,
        note  = "仿植物生長。X 是生長點，F 是莖，[] 是分支。",
    ),

    "dragon": LSystem(
        name  = "龍曲線",
        axiom = "FX",
        rules = {
            "X": "X+YF+",
            "Y": "-FX-Y",
        },
        angle = 90.0,
        iters = 12,
        note  = "無限折疊一張紙的軌跡。",
    ),

    "sierpinski": LSystem(
        name  = "謝爾賓斯基三角形",
        axiom = "F-G-G",
        rules = {
            "F": "F-G+F+G-F",
            "G": "GG",
        },
        angle = 120.0,
        iters = 5,
        note  = "三角形的自相似碎形。",
    ),

    "koch": LSystem(
        name  = "科赫雪花",
        axiom = "F++F++F",
        rules = {
            "F": "F-F++F-F",
        },
        angle = 60.0,
        iters = 4,
        note  = "無限細化的邊界，有限的面積。",
    ),

    "hilbert": LSystem(
        name  = "希爾伯特曲線",
        axiom = "A",
        rules = {
            "A": "-BF+AFA+FB-",
            "B": "+AF-BFB-FA+",
        },
        angle = 90.0,
        iters = 5,
        note  = "填滿正方形的空間填充曲線。",
    ),

    "bush": LSystem(
        name  = "灌木",
        axiom = "Y",
        rules = {
            "X": "X[-FFF][+FFF]FX",
            "Y": "YFX[+Y][-Y]",
        },
        angle = 25.7,
        iters = 5,
        note  = "有些混沌的有機形狀。",
    ),

    "crystal": LSystem(
        name  = "晶體",
        axiom = "F+F+F+F",
        rules = {
            "F": "FF+F++F+F",
        },
        angle = 90.0,
        iters = 4,
        note  = "正方格上生長的晶體邊界。",
    ),
}


# ── L-system 展開 ─────────────────────────────────────────────────

def expand(system: LSystem, iters: Optional[int] = None) -> str:
    """套用重寫規則 n 次，回傳最終字串。"""
    n   = iters if iters is not None else system.iters
    s   = system.axiom
    for _ in range(n):
        s = "".join(system.rules.get(ch, ch) for ch in s)
    return s


# ── 海龜作圖 ──────────────────────────────────────────────────────

@dataclass
class Turtle:
    x:     float = 0.0
    y:     float = 0.0
    angle: float = 90.0    # 面向上方出發
    stack: List[Tuple] = field(default_factory=list)

    def forward(self, d=1.0):
        nx = self.x + d * math.cos(math.radians(self.angle))
        ny = self.y + d * math.sin(math.radians(self.angle))
        seg = (self.x, self.y, nx, ny)
        self.x, self.y = nx, ny
        return seg

    def turn(self, deg):   self.angle += deg
    def push(self):        self.stack.append((self.x, self.y, self.angle))
    def pop(self):         self.x, self.y, self.angle = self.stack.pop()


def interpret(s: str, angle_deg: float) -> List[Tuple[float,float,float,float]]:
    """把 L-system 字串解讀為線段列表。"""
    t    = Turtle()
    segs = []
    for ch in s:
        if   ch in "FG":  segs.append(t.forward())
        elif ch == "+":   t.turn(+angle_deg)
        elif ch == "-":   t.turn(-angle_deg)
        elif ch == "[":   t.push()
        elif ch == "]":   t.pop()
        # X, Y, A, B … 是無動作的生長符號，忽略
    return segs


# ── 光柵化 ────────────────────────────────────────────────────────

def rasterize(segs: List[Tuple], width: int, height: int) -> List[List[str]]:
    """把向量線段畫到字元格。"""
    if not segs:
        return [["." * width] for _ in range(height)]

    xs = [c for s in segs for c in (s[0], s[2])]
    ys = [c for s in segs for c in (s[1], s[3])]
    xlo, xhi = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)

    xspan = xhi - xlo or 1.0
    yspan = yhi - ylo or 1.0

    # 保持比例，留邊距
    pad    = 2
    uw, uh = width - pad*2, height - pad*2
    scale  = min(uw / xspan, uh / yspan)

    def tx(x): return int((x - xlo) * scale) + pad
    def ty(y): return int((yhi - y) * scale) + pad   # 翻轉 y

    grid = [[" "] * width for _ in range(height)]

    def plot(px, py, ch=" "):
        if 0 <= px < width and 0 <= py < height:
            grid[py][px] = ch

    for x0, y0, x1, y1 in segs:
        # Bresenham 直線
        px0, py0 = tx(x0), ty(y0)
        px1, py1 = tx(x1), ty(y1)
        dx, dy   = abs(px1-px0), abs(py1-py0)
        sx, sy   = (1 if px0<px1 else -1), (1 if py0<py1 else -1)
        err      = dx - dy
        cx, cy   = px0, py0
        while True:
            # 根據線段方向選字元
            if   dx == 0:  ch = "│"
            elif dy == 0:  ch = "─"
            elif (sx > 0) == (sy > 0): ch = "\\"
            else:          ch = "/"
            plot(cx, cy, ch)
            if cx == px1 and cy == py1: break
            e2 = 2 * err
            if e2 > -dy: err -= dy; cx += sx
            if e2 <  dx: err += dx; cy += sy

    return grid


def render_colored(grid: List[List[str]]) -> str:
    """為每一行的繪製字元加上由下而上的漸層顏色。"""
    height = len(grid)
    out    = []
    for row_i, row in enumerate(grid):
        pct   = 1.0 - row_i / height          # 0=底, 1=頂
        color = COLORS[int(pct * (len(COLORS)-1))]
        line  = "".join(row)
        # 只對非空白字元上色
        colored = "".join(
            (color + ch + RESET if ch != " " else ch)
            for ch in line
        )
        out.append(colored)
    return "\n".join(out)


# ── 主程式 ────────────────────────────────────────────────────────

def _terminal_size():
    try:
        import shutil
        cols, rows = shutil.get_terminal_size()
        return max(cols, 40), max(rows, 20)
    except Exception:
        return 80, 40

def draw(key: str, iters: Optional[int] = None, mono: bool = False):
    system = SYSTEMS[key]
    n      = iters if iters is not None else system.iters
    W, H   = _terminal_size()
    H      = H - 6          # 留給標題和說明

    print()
    print(f"  {BOLD}{system.name}{RESET}  {DIM}（迭代 {n} 次）{RESET}")
    print(f"  {DIM}{system.note}{RESET}")
    print()

    s    = expand(system, n)
    segs = interpret(s, system.angle)
    grid = rasterize(segs, W - 4, H)

    if mono:
        for row in grid:
            print("  " + "".join(row))
    else:
        print(render_colored(grid))
    print()


def menu():
    keys = list(SYSTEMS.keys())
    while True:
        print(f"\n  {BOLD}L-system 渲染器{RESET}")
        print(f"  {DIM}─────────────────────────{RESET}")
        for i, k in enumerate(keys):
            s = SYSTEMS[k]
            print(f"  {CYAN}{i+1}{RESET}  {s.name:16}  {DIM}{s.note[:40]}…{RESET}")
        print(f"  {DIM}0  離開{RESET}")
        print()

        try:
            raw = input("  選擇 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  再見。")
            break

        if raw == "0":
            print("  再見。")
            break

        parts    = raw.split()
        choice   = parts[0] if parts else ""
        iters    = int(parts[1]) if len(parts) > 1 else None

        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            draw(keys[int(choice)-1], iters)
        elif choice in SYSTEMS:
            draw(choice, iters)
        else:
            print(f"  {DIM}輸入數字 1-{len(keys)}，或輸入名稱如 plant / dragon{RESET}")


CYAN = _c("96")

if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        key   = args[0] if args[0] in SYSTEMS else list(SYSTEMS.keys())[0]
        iters = int(args[1]) if len(args) > 1 else None
        draw(key, iters)
    else:
        menu()

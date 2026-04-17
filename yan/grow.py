#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grow.py — 用言（Yán）長一棵植物

執行 04_lsystem.yn，把 SVG 存檔，用瀏覽器打開。
每次長出來的植物都不一樣。
"""

import sys, os, subprocess, webbrowser, pathlib, time

HERE  = pathlib.Path(__file__).parent
YAN   = HERE / "yan.py"
SRC   = HERE / "examples" / "04_lsystem.yn"
OUT   = HERE / "plant.svg"

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    for i in range(n):
        print(f"正在生長第 {i+1} 棵植物...", end=" ", flush=True)
        t0 = time.perf_counter()

        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(YAN), str(SRC)],
            capture_output=True, text=True, encoding="utf-8"
        )

        if result.returncode != 0:
            print(f"\n錯誤：\n{result.stderr}")
            sys.exit(1)

        svg = result.stdout
        dt  = time.perf_counter() - t0
        segs = svg.count("<line")
        print(f"完成（{segs} 條線段，{dt*1000:.0f} ms）")

        out = HERE / (f"plant_{i+1}.svg" if n > 1 else "plant.svg")
        out.write_text(svg, encoding="utf-8")
        webbrowser.open(out.as_uri())

        if i < n - 1:
            time.sleep(0.5)

if __name__ == "__main__":
    main()

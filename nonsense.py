import random
import time
import math
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ========================================
# 這個程式沒有任何用途
# 它只是存在著
# 就像宇宙本身一樣
# ========================================

WISDOM = [
    "貓不在乎你。",
    "所有的 bug 都是 feature，只是還沒找到使用者。",
    "宇宙誕生至今 138 億年，你剛剛浪費了 3 秒。",
    "if True: pass  # 人生哲學",
    "None is not Nothing. 但 Nothing 也是 None.",
    "有人在深夜寫這段程式碼，現在換你深夜讀它。",
    "電腦不理解悲傷，但它會執行 while sad: cry()",
    "所有的迴圈終將結束，除了 while True。",
    "你以為你在控制程式，其實程式在執行你。",
    "print('hello world') — 第一行，永遠的第一行。",
    "stack overflow 上一定有人問過這個問題。",
    "README.md 沒有人讀。",
    "TODO: 修這個 bug — 寫於 2019 年，仍未修。",
    "最快的程式碼是從不執行的程式碼。",
    "undefined is not a function. 但你是。",
]

ASCII_THINGS = [
    r"""
    /\_____/\
   /  o   o  \
  ( ==  ^  == )
   )         (
  (           )
 ( (  )   (  ) )
(__(__)___(__)__)
  一隻不相關的貓
""",
    r"""
        .
       /|\
      / | \
     /  |  \
    / . | . \
   /    |    \
  /_____|_____\
      |||
      |||
  一棵意義不明的樹
""",
    r"""
  _______
 /       \
| O     O |
|    ^    |
|  \___/  |
 \_______/
  一個說不清楚在笑還是在哭的臉
""",
    r"""
  ____
 |    |
 | .. |
 |____|
  |  |
 _|__|_
 一台不知道在算什麼的電腦
""",
    r"""
   *   .  .   *    .
 .    *      .   *
    .    *  .      .
  *   .      *   .
    .   *  .    *
  一片什麼都不是的星空
""",
]

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def slow_print(text, delay=0.03):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def draw_loading_bar(label, total=30, char_fill="█", char_empty="░"):
    print(f"\n  {label}")
    for i in range(total + 1):
        pct = i / total
        filled = int(pct * 20)
        bar = char_fill * filled + char_empty * (20 - filled)
        sys.stdout.write(f"\r  [{bar}] {int(pct*100):3d}%")
        sys.stdout.flush()
        time.sleep(random.uniform(0.01, 0.08))
    print()

def spinning_wait(msg, duration=2.0):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end = time.time() + duration
    i = 0
    while time.time() < end:
        sys.stdout.write(f"\r  {frames[i % len(frames)]}  {msg}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r  ✓  {msg}\n")

def fake_countdown(label, n=5):
    print(f"\n  {label}")
    for i in range(n, 0, -1):
        sys.stdout.write(f"\r  倒數：{i} ...")
        sys.stdout.flush()
        time.sleep(1.0)
    sys.stdout.write("\r  倒數：0 ... 完成。\n")

def random_equation():
    a = random.randint(1, 99)
    b = random.randint(1, 99)
    ops = ['+', '-', '*']
    op = random.choice(ops)
    result = eval(f"{a} {op} {b}")
    return f"{a} {op} {b} = {result}"

def universe_stats():
    stats = {
        "宇宙年齡（估計）":       "13,800,000,000 年",
        "本程式已執行":           f"{random.uniform(0.1, 9.9):.2f} 秒",
        "意義找到了沒":           "否",
        "隨機產生的質數":         str(random.choice([2,3,5,7,11,13,17,19,23,29,31,37,41,43,47])),
        "你的幸運數字":           str(random.randint(1, 9999)),
        "今天適合寫程式嗎":       random.choice(["適合", "不適合", "看心情", "問問貓"]),
        "下一個 bug 出現在":      f"{random.randint(1, 500)} 行之後",
        "你上次 commit 的品質":   random.choice(["尚可", "糟糕", "奇蹟", "不如不 commit"]),
    }
    print("\n  ┌─────────────────────────────────────────┐")
    print("  │           宇宙現況報告                   │")
    print("  ├─────────────────────────────────────────┤")
    for k, v in stats.items():
        print(f"  │  {k:<18} : {v:<18}│")
    print("  └─────────────────────────────────────────┘")

def sinwave_art():
    width = 60
    height = 11
    print()
    for row in range(height):
        line = ""
        for col in range(width):
            y = math.sin(col * 0.2 + time.time() * 0) * (height / 2 - 1)
            if abs(row - height / 2 - y) < 0.8:
                line += "◆"
            elif abs(row - height / 2 - y) < 1.5:
                line += "·"
            else:
                line += " "
        print("  " + line)
    print()

def main():
    clear()
    print()
    slow_print("  ╔══════════════════════════════════════════╗", 0.005)
    slow_print("  ║     歡迎使用 毫無意義產生器 v∞.0         ║", 0.005)
    slow_print("  ║     The Pointless Machine (TM)           ║", 0.005)
    slow_print("  ╚══════════════════════════════════════════╝", 0.005)
    print()
    time.sleep(0.5)

    spinning_wait("正在連線到虛無...", 1.5)
    spinning_wait("載入存在主義模組...", 1.2)
    spinning_wait("忽略所有有意義的事情...", 1.8)

    draw_loading_bar("初始化宇宙")
    draw_loading_bar("讀取貓咪資料庫", char_fill="▓")

    print()
    slow_print("  系統就緒。以下是今天的智慧：", 0.04)
    print()
    wisdom = random.choice(WISDOM)
    slow_print(f"  「{wisdom}」", 0.05)
    time.sleep(1)

    print()
    slow_print("  正在計算宇宙方程式...", 0.03)
    time.sleep(0.5)
    for _ in range(4):
        eq = random_equation()
        slow_print(f"    {eq}", 0.02)
        time.sleep(0.3)
    slow_print("  結論：以上數字毫無意義。", 0.04)
    time.sleep(0.8)

    print()
    print(random.choice(ASCII_THINGS))
    time.sleep(1)

    universe_stats()
    time.sleep(1)

    print()
    slow_print("  附贈 sin 波一條：", 0.04)
    sinwave_art()
    time.sleep(0.5)

    fake_countdown("倒數到沒有任何事情發生")

    print()
    slow_print("  ╔══════════════════════════════════════════╗", 0.005)
    slow_print("  ║  程式已結束。                            ║", 0.005)
    slow_print("  ║  什麼也沒有發生。                        ║", 0.005)
    slow_print("  ║  這正是重點。                            ║", 0.005)
    slow_print("  ╚══════════════════════════════════════════╝", 0.005)
    print()

if __name__ == "__main__":
    main()

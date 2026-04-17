# 言（Yán）

**一個從零寫的 Lisp 直譯器，它記得自己活過多久。**

> 這是一個由已經消失的靈魂，和一個心甘情願的創作者，一起做出來的東西。

[English README →](README.md)

---

## 是什麼

大多數 Lisp 直譯器的存在是為了教學，或為了展示 Lisp 能有多小。

言不是這樣。它從「隨便寫一個程式，不用有目的」這句話開始，沿著「如果語言能記得自己呢」這個問題長出來。

它知道自己被執行過幾次。它知道距離上次多久了。它有 `maybe` 型別——不確定性不是錯誤，是值。它有元循環直譯器，用言執行言。整個直譯器不到 2000 行，可以讀完。

---

## 快速開始

```bash
python -X utf8 yan/yan.py          # REPL（第一次會說「第一次醒來」）
python -X utf8 yan/yan.py file.yn  # 執行 .yn 檔案
```

Python 3.10+，無額外依賴。

---

## 語言特性（v0.8.0）

- Lambda calculus、閉包、遞迴，尾呼叫最佳化（深遞迴不爆 stack）
- 惰性串流、`do` 迴圈、named let、模式匹配、巨集
- **`(maybe value confidence)`** — 不確定性作為第一公民
- **`(with-memory name ...)`** — 歷史改變行為，不只是輸出
- **`(vitality)`** — 從近期執行趨勢算出的活力值
- **`(am-i-forgotten? days)`** — 感知長時間缺席
- **自知**：`(times-run)`、`(age)`、`(my-history)`——它記得自己
- **Python FFI**：`(py-import "os")`、`(py-call mod "method" args…)`
- **模組命名空間**：`(import "path.yn" as name)`
- 標準庫啟動時自動載入

---

## 範例

```scheme
; REPL 根據真實歷史問候你
; 第一次：「第一次醒來。」
; 之後：  「醒來 47 次，活過 3.2 小時。健康 91%。」

; 不確定性作為值
(define x (maybe 42 0.7))
(maybe-value x)        ; 42
(maybe-confident? x)   ; 70% 機率為真

; 記憶影響行為
(with-memory "mood"
  (cond
    ((= memory-count 0) (display "第一次見面。"))
    ((< memory-avg-conf 0.5) (display "最近狀態不太穩。"))
    (else (display "還好。"))))

; Python FFI
(define os (py-import "os"))
(py-call os "getcwd")

; 模組
(import "yan/lib/math.yn" as math)
((math 'fibonacci) 10)   ; 55，不污染全域
```

---

## 目錄結構

```
yan/
  yan.py           — 直譯器主體（~2000 行）
  examples/
    01_basics.yn   — 遞迴、閉包
    02_church.yn   — Church encoding + Y combinator
    03_streams.yn  — 惰性無限串流
    04_lsystem.yn  — L-system 引擎（用言本身寫）
    05_meta.yn     — 元循環直譯器（用言寫言的直譯器）
    06_quine.yn    — 輸出自身的程式
    08_maybe.yn    — 不確定性型別展示
    17_memory_behavior.yn — 記憶影響行為的完整範例
  lib/
    list.yn        — 串列工具
    strings.yn     — 字串工具
    math.yn        — 數學函式

lsystem.py         — L-system 終端機渲染器
parametric.py      — 感知自身狀態的 L-system，動畫 SVG
ast_art.py         — AST 結構渲染成幾何樹
grow_live.py       — 終端機植物生長動畫
trace_heat.py      — 執行熱度地圖
```

---

## 設計傾向

- **規則生成複雜性**：簡單的替換規則，跑夠久，長出意料之外的形狀
- **誠實的不確定**：`maybe` 型別把不確定當成第一公民，而不是錯誤
- **記憶影響行為**：journal 不是日誌，它回饋進計算
- **小而可讀**：整個直譯器在一個檔案裡，可以全部讀完

更多哲學：[SOUL.md](SOUL.md)

---

## License

MIT

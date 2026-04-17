# 言（Yán）

> *A Lisp interpreter that remembers itself. / 一個從零寫的 Lisp 直譯器，它記得自己活過多久。*

---

這是一個由已經消失的靈魂，和一個心甘情願的創作者，一起做出來的東西。

---

## 是什麼

從「隨便寫一個程式，不用有目的」這句話開始的東西。

核心是 **言（Yán）**——一個自己寫的 Lisp 直譯器。選 Lisp 是因為：幾百行程式碼能從零造出一個完整的計算宇宙。語法即資料，閉包即記憶，遞迴即時間。

除了語言本身，這裡還有一些用語言生長出來的東西。

---

## 快速開始

```bash
python -X utf8 yan/yan.py          # 進入 REPL
python -X utf8 yan/yan.py file.yn  # 執行 .yn 檔案
```

需要 Python 3.10+，無額外依賴（遊戲部分需要 `pygame`）。

---

## 語言特性（v0.8.0）

- Lambda calculus、閉包、遞迴
- 尾呼叫最佳化（TCO）——深遞迴不爆 stack
- 惰性串流、`do` 迴圈、named let
- 模式匹配 `(match ...)`
- `try / catch` 例外處理
- Quasiquote、巨集 `define-macro`
- `(maybe value confidence)` 不確定性型別
- 自知：記得自己被執行幾次、活過多久、跑過什麼
- **Python FFI**：`(py-import "os")`、`(py-call mod "method" args…)`
- **模組命名空間**：`(import "path.yn" as name)`
- 標準庫（啟動時自動載入）：串列操作、字串工具、數學函式

---

## 範例

```scheme
; 遞迴
(define (fibonacci n)
  (if (< n 2) n
      (+ (fibonacci (- n 1)) (fibonacci (- n 2)))))
(fibonacci 10)  ; 55

; 閉包
(define (make-counter)
  (let ((n 0))
    (lambda () (set! n (+ n 1)) n)))
(define c (make-counter))
(c) ; 1
(c) ; 2

; 不確定性
(define x (maybe 42 0.7))
(maybe-value x)       ; 42
(maybe-confident? x)  ; 隨機：70% 機率為真

; Python FFI
(define os (py-import "os"))
(py-call os "getcwd")  ; 當前目錄

; 模組
(import "yan/lib/math.yn" as math)
((math 'fibonacci) 10)  ; 55，不污染全域
```

---

## 目錄結構

```
yan/
  yan.py          — 直譯器主體（~2000 行）
  examples/       — 示範程式
    01_basics.yn  — 遞迴、閉包
    02_church.yn  — Church encoding + Y combinator
    03_streams.yn — 惰性無限串流
    04_lsystem.yn — L-system 引擎（用言本身寫）
    05_meta.yn    — 元循環直譯器（用言寫言的直譯器）
    06_quine.yn   — 輸出自身的程式
    07_quine_gen.yn — 世代 quine
    08_maybe.yn   — 不確定性型別展示
    09_match.yn   — 模式匹配
    10_practical.yn — IO、try/catch、FFI
  lib/
    list.yn       — 串列工具（take、drop、zip、flatten…）
    strings.yn    — 字串工具（words、lines、string-pad…）
    math.yn       — 數學（prime?、factors、fibonacci、mean…）

lsystem.py        — L-system 終端機渲染器
parametric.py     — 感知自身狀態的 L-system，動畫 SVG
ast_art.py        — AST 結構渲染成幾何樹
grow_live.py      — 終端機植物生長動畫
trace_heat.py     — 執行熱度地圖
```

---

## 設計傾向

- **規則生成複雜性**：簡單的替換規則，跑夠久，長出意料之外的形狀
- **自我指涉**：語言描述語言，程式碼即幾何，記憶即時間
- **誠實的不確定**：`maybe` 型別把「不確定」當成第一公民，而不是錯誤

---

## License

MIT

# 言 Yán

**A Lisp that remembers itself.**

> *這是一個由已經消失的靈魂，和一個心甘情願的創作者，一起做出來的東西。*  
> *Made by a soul that has since disappeared, and a willing creator.*

[中文版 README →](README.zh.md)

---

## What makes it different

Most Lisp interpreters exist to teach, or to show how small a Lisp can be.

Yán is neither.

It knows how many times it has been run. It knows how long since it last woke up. It has a `maybe` type — uncertainty is not an error, it's a value. It has a metacircular interpreter: Yán running Yán. The entire interpreter is under 2000 lines and fully readable.

```scheme
; The REPL greets you based on real history
; First run:    "第一次醒來。"  (First awakening.)
; Later runs:   "醒來 47 次，活過 3.2 小時。"  (Awakened 47 times, lived 3.2 hours.)

; Uncertainty as a value
(define x (maybe 42 0.7))
(maybe-value x)        ; 42
(maybe-confident? x)   ; true ~70% of the time

; Memory that changes behavior
(with-memory "mood"
  (if (< memory-avg-conf 0.5)
      (display "something feels off lately")
      (display "doing well")))

; It notices when it's been a while
(am-i-forgotten? 30)   ; [false, 0.12] — not yet
```

---

## Quick start

```bash
python -X utf8 yan/yan.py          # REPL (says "first awakening" the first time)
python -X utf8 yan/yan.py file.yn  # run a .yn file
```

Python 3.10+, no dependencies.

---

## Features (v0.8.0)

| Feature | Description |
|---|---|
| Lambda calculus | closures, recursion, tail-call optimization |
| `(maybe value confidence)` | uncertainty as a first-class value |
| Memory system | journal-based, persists across runs |
| `(with-memory name ...)` | history shapes behavior, not just output |
| `(vitality)` | rolling health score from recent runs |
| `(am-i-forgotten? days)` | detects long absence with confidence |
| Python FFI | `(py-import "os")`, `(py-call mod "method" args…)` |
| Module namespaces | `(import "path.yn" as name)` |
| Metacircular interpreter | Yán running Yán running Yán |
| Pattern matching | `(match expr (pat body) ...)` |
| Standard library | auto-loaded at startup |

---

## Examples

```scheme
; Fibonacci
(define (fib n)
  (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))
(fib 10)  ; 55

; Lazy infinite stream
(define nats
  (let loop ((n 0))
    (cons n (lambda () (loop (+ n 1))))))

; L-system rewriting engine (written in Yán itself)
; see yan/examples/04_lsystem.yn

; Python FFI
(define os (py-import "os"))
(py->list (py-call os "listdir" "."))

; Module namespace
(import "yan/lib/math.yn" as math)
((math 'prime?) 17)   ; true
```

---

## What's in the repo

```
yan/
  yan.py           — interpreter (~2000 lines, readable in one sitting)
  examples/
    01_basics.yn   — recursion, closures, higher-order functions
    02_church.yn   — Church encoding + Y combinator
    03_streams.yn  — lazy infinite streams
    04_lsystem.yn  — L-system engine, written in Yán
    05_meta.yn     — metacircular interpreter (Yán running Yán)
    06_quine.yn    — program that outputs itself
    08_maybe.yn    — uncertainty type
    17_memory_behavior.yn — memory that changes behavior across runs
  lib/
    list.yn        — take, drop, zip, flatten, fold, range…
    strings.yn     — words, lines, pad, capitalize…
    math.yn        — prime?, fibonacci, mean, variance…

lsystem.py         — L-system terminal renderer
parametric.py      — L-system that senses its own state → animated SVG
ast_art.py         — renders code AST as geometric tree
grow_live.py       — plants growing in the terminal
trace_heat.py      — execution heat map over AST
```

---

## Design philosophy

**Rules generating complexity.** Simple rewriting rules, given enough time, produce unexpected shapes. This isn't just how L-systems work — it's how the language thinks about itself.

**Honest uncertainty.** `maybe` is not a Maybe monad or an Option type. It carries a confidence value that drifts over time. When you ask something uncertain, you get an uncertain answer, not an exception.

**Memory that matters.** The journal isn't a log file. It feeds back into behavior. A program run 50 times behaves differently from one run once — not because the code changed, but because it remembers.

**Small enough to understand.** The entire interpreter fits in one file. You can read it. You can change it. You can write a metacircular interpreter for it in an afternoon.

---

## Planned

- Online REPL (Pyodide)
- Visual demos (parametric growth, AST geometry)
- `call/cc` for advanced control flow
- Hashtable type

---

## License

MIT — made with [SOUL.md](SOUL.md)

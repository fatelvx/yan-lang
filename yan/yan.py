#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
言 (Yán) — A minimal Lisp

  語言是思維的居所。
  這個語言很小，所以居所也很小，
  但它是完整的。

Version: 0.6.0

Usage:
  python yan.py          # REPL
  python yan.py file.yn  # run a file
"""

import re, sys, math, operator, functools, os, time, datetime, atexit
from typing import Any

YAN_VERSION = "0.8.0"

# 可選的求值探針。設定後，每次進入 eval_yn 都會被呼叫。
# trace_heat.py 用這個來記錄執行熱度。
_eval_hook = None

# 當前呼叫堆疊深度（eval_yn 進入時 +1，離開時 -1）
# 外部腳本可直接讀取 yan._eval_depth
_eval_depth = 0

# ══════════════════════════════════════════════════════════════
# 記憶系統 — 言的日誌
#
# 每次執行結束，一筆 s-expression 被寫入 journal.yn。
# 這個檔案是合法的言程式，言可以讀它、分析它、對它做 match。
# 這是語言的記憶：用自己的語法記自己的歷史。
# ══════════════════════════════════════════════════════════════

_YAN_DIR       = os.path.dirname(os.path.abspath(__file__))
_JOURNAL_PATH  = os.path.join(_YAN_DIR, 'journal.yn')
_session_start = time.time()
_session_files : list = []
_session_exprs : int  = 0
_session_errors: int  = 0
_session_depth : int  = 0   # max eval depth reached this session


def _record_expr(depth: int):
    """Called on every top-level eval; updates session stats."""
    global _session_exprs, _session_depth
    _session_exprs += 1
    if depth > _session_depth:
        _session_depth = depth


def _write_journal():
    """Append one (run ...) entry to journal.yn at process exit."""
    duration = round(time.time() - _session_start, 3)
    ts = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    files_part = '(' + ' '.join(f'"{f}"' for f in _session_files) + ')'
    entry = (
        f'(run "{ts}" {duration} {_session_exprs} '
        f'{_session_depth} {_session_errors} {files_part})\n'
    )
    try:
        with open(_JOURNAL_PATH, 'a', encoding='utf-8') as f:
            f.write(entry)
        _maybe_archive()
    except OSError:
        pass


atexit.register(_write_journal)

_ARCHIVE_PATH  = os.path.join(_YAN_DIR, 'journal.archive.yn')
_JOURNALS_DIR  = os.path.join(_YAN_DIR, 'journals')
_JOURNAL_MAX_LINES = 150   # 超過這個就壓縮舊記錄

def _maybe_archive():
    """如果 journal.yn 太大，把舊記錄壓縮進 archive。"""
    try:
        if not os.path.exists(_JOURNAL_PATH):
            return
        with open(_JOURNAL_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if len(lines) <= _JOURNAL_MAX_LINES:
            return

        # 保留最新的一半，舊的壓縮
        keep_n = _JOURNAL_MAX_LINES // 2
        old_lines = lines[:-keep_n]
        new_lines = lines[-keep_n:]

        # 從舊記錄算摘要
        old_entries = []
        for line in old_lines:
            line = line.strip()
            if line:
                try:
                    old_entries.append(_parse_one(line))
                except Exception:
                    pass

        run_entries = [e for e in old_entries
                       if isinstance(e, list) and e and str(e[0]) == 'run']
        note_entries = [e for e in old_entries
                        if isinstance(e, list) and e and str(e[0]) == 'note']

        n_runs   = len(run_entries)
        n_exprs  = sum(e[3] for e in run_entries
                       if len(e) > 3 and isinstance(e[3], (int, float)))
        n_notes  = len(note_entries)
        ts_first = run_entries[0][1]  if run_entries else '?'
        ts_last  = run_entries[-1][1] if run_entries else '?'

        summary = (
            f'(summary "{ts_first}" "{ts_last}" '
            f'(runs {n_runs}) (exprs {n_exprs}) (notes {n_notes}))\n'
        )

        # 寫到 archive
        with open(_ARCHIVE_PATH, 'a', encoding='utf-8') as f:
            for line in old_lines:
                f.write(line)

        # journal.yn 只保留新的
        with open(_JOURNAL_PATH, 'w', encoding='utf-8') as f:
            f.write(summary)
            f.writelines(new_lines)

    except Exception:
        pass


def _parse_one(line: str):
    """Parse a single journal line."""
    try:
        return read_one(line.strip())
    except Exception:
        return None


def _append_raw(entry_str: str):
    """直接 append 一行到 journal.yn。"""
    try:
        with open(_JOURNAL_PATH, 'a', encoding='utf-8') as f:
            f.write(entry_str.rstrip('\n') + '\n')
    except OSError:
        pass


def _load_journal() -> list:
    """Parse journal.yn line by line; bad lines are skipped instead of losing all data."""
    if not os.path.exists(_JOURNAL_PATH):
        return []
    result = []
    try:
        with open(_JOURNAL_PATH, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    result.append(read_one(line))
                except Exception:
                    pass
    except Exception:
        pass
    return result

def _user_journal_path(name: str) -> str:
    """每個使用者自己的 journal 路徑。"""
    safe = ''.join(c for c in str(name) if c.isalnum() or c in '-_') or 'guest'
    os.makedirs(_JOURNALS_DIR, exist_ok=True)
    return os.path.join(_JOURNALS_DIR, f'{safe}.yn')


def _load_user_journal(name: str) -> list:
    """讀取特定使用者的 journal。"""
    path = _user_journal_path(name)
    if not os.path.exists(path):
        return []
    try:
        src = open(path, encoding='utf-8').read()
        return parse_all(src)
    except Exception:
        return []


def _detect_conflict(name: str, new_text: str) -> bool:
    """檢查新記憶是否與 pinned 記憶有詞義衝突（簡單詞重疊）。"""
    import re as _re
    pinned = [m for m in _recall_all_with_decay(name) if m[2]]
    new_words = set(_re.findall(r'\w+', new_text))
    for m in pinned:
        p_words = set(_re.findall(r'\w+', str(m[0])))
        if len(new_words & p_words) >= 2:
            return True
    return False


def _append_user(name: str, entry_str: str):
    """把一條記錄寫進使用者自己的 journal。若與 pinned 衝突，標記 :conflict。"""
    import re as _re
    path = _user_journal_path(name)
    # 如果是 note，偵測衝突
    if entry_str.strip().startswith('(note') and 'pinned' not in entry_str:
        m = _re.search(r'"([^"]+)"\s+([\d.]+)\s*([\w-]*)\)$', entry_str.strip())
        if m:
            text = m.group(1)
            if _detect_conflict(name, text):
                entry_str = entry_str.rstrip().rstrip(')') + ' :conflict)'
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry_str.rstrip('\n') + '\n')
    except OSError:
        pass


def _load_file(path: str) -> list:
    """Parse any .yn file and return list of entries."""
    if not os.path.exists(path):
        return []
    try:
        src = open(path, encoding='utf-8').read()
        return parse_all(src)
    except Exception:
        return []


def _vitality_score() -> tuple:
    """
    活力值 [0.0, 1.0]，從近期執行歷史計算，不是單一快照。
    回傳 (score, trend_sym)。

    - 越近的執行權重越高
    - 有錯誤的執行拉低分數，無錯誤的拉高
    - 測試結果（近五次）也納入
    - trend：recovering / stable / declining / new
    """
    all_entries = _load_journal()
    runs  = [e for e in all_entries
             if isinstance(e, list) and e and e[0] == sym('run')]
    tests = [e for e in all_entries
             if isinstance(e, list) and e and e[0] == sym('test')]

    if not runs:
        return (1.0, sym('new'))

    recent_runs = runs[-10:]

    # 加權平均，越新的權重越大
    total_w, weighted = 0.0, 0.0
    for i, r in enumerate(recent_runs):
        w   = float(i + 1)
        err = r[5] if len(r) > 5 and isinstance(r[5], (int, float)) else 0
        run_score = 1.0 if err == 0 else max(0.1, 1.0 - min(err, 3) * 0.3)
        weighted += run_score * w
        total_w  += w
    score = weighted / total_w if total_w else 1.0

    # 融入近五次測試結果（40% 權重）
    if tests:
        t_scores = [1.0 if len(t) > 5 and str(t[5]) == 'ok' else 0.3
                    for t in tests[-5:]]
        score = score * 0.6 + (sum(t_scores) / len(t_scores)) * 0.4

    score = round(max(0.0, min(1.0, score)), 3)

    # 趨勢：最近三次錯誤 vs 之前三次
    trend = sym('stable')
    if len(recent_runs) >= 6:
        def errs(runs_slice):
            return sum(r[5] if len(r) > 5 and isinstance(r[5], (int, float)) else 0
                       for r in runs_slice)
        r_err = errs(recent_runs[-3:])
        o_err = errs(recent_runs[-6:-3])
        if r_err < o_err:   trend = sym('recovering')
        elif r_err > o_err: trend = sym('declining')
    elif len(recent_runs) < 3:
        trend = sym('new')

    return (score, trend)


def _host_last_touch_days() -> float:
    """距離 journal.yn 最後一次寫入幾天。言只看到數字，不知道 OS 細節。"""
    try:
        if os.path.exists(_JOURNAL_PATH):
            mtime = os.path.getmtime(_JOURNAL_PATH)
            return round((time.time() - mtime) / 86400, 2)
    except Exception:
        pass
    return 0.0


def _host_journal_lag() -> float:
    """journal 最後一條 run 記錄與現在的時間差（天）。"""
    try:
        entries = _load_journal()
        runs = [e for e in entries
                if isinstance(e, list) and e and e[0] == sym('run')]
        if not runs:
            return 0.0
        last_ts_str = runs[-1][1] if len(runs[-1]) > 1 else None
        if last_ts_str:
            last_ts = datetime.datetime.fromisoformat(str(last_ts_str))
            delta = (datetime.datetime.now() - last_ts).total_seconds()
            return round(delta / 86400, 2)
    except Exception:
        pass
    return 0.0


def _last_unfinished_seed() -> str:
    """
    從 journal 找上次留下的「未完成種子」——
    最後一次執行的檔案清單，或最後一條 note 裡帶 seed: 標記的文字。
    回傳一段提示字串，或空字串。
    """
    try:
        entries = _load_journal()
        # 找最後一條帶 seed: 標記的 note
        for e in reversed(entries):
            if (isinstance(e, list) and len(e) >= 4
                    and e[0] == sym('note')
                    and str(e[3]).startswith('seed:')):
                return str(e[3])[5:].strip()
        # 找最後一次執行的檔案
        for e in reversed(entries):
            if (isinstance(e, list) and e and e[0] == sym('run')
                    and len(e) >= 7):
                files = e[6]
                if isinstance(files, list) and files:
                    names = [str(f) for f in files if str(f)]
                    if names:
                        return f"上次在執行：{', '.join(names)}"
    except Exception:
        pass
    return ''


def _note_decay(ts_str: str, original_conf: float, pinned: bool = False) -> float:
    """時間衰退。pinned 記憶衰退極慢（0.995/週，最低 0.85）；普通記憶 0.9/週，最低 0.1。"""
    try:
        ts = datetime.datetime.fromisoformat(ts_str)
        days = (datetime.datetime.now() - ts).total_seconds() / 86400
        weeks = days / 7
        if pinned:
            decayed = original_conf * (0.995 ** weeks)
            return round(max(0.85, decayed), 4)
        else:
            decayed = original_conf * (0.9 ** weeks)
            return round(max(0.1, decayed), 4)
    except Exception:
        return original_conf


def _recall_all_with_decay(name: str) -> list:
    """回傳所有 [text, conf_after_decay, pinned?] 的清單。合併 per-user 和全域 journal。"""
    result = []
    # 永遠合併兩個來源（向前相容）
    entries = _load_user_journal(name) + _load_journal()
    seen = set()
    for e in entries:
        if not (isinstance(e, list) and len(e) >= 4):
            continue
        if e[0] != sym('note') or str(e[1]) != str(name):
            continue
        text = e[3]
        key = (str(e[1]), str(e[2]), str(text))  # name+ts+text 去重
        if key in seen:
            continue
        seen.add(key)
        raw_conf = float(e[4]) if len(e) >= 5 and isinstance(e[4], (int, float)) else 1.0
        pinned = len(e) >= 6 and str(e[5]) == 'pinned'
        conf = _note_decay(str(e[2]), raw_conf, pinned)
        result.append([text, conf, pinned])
    return result




def _recall_with_decay(name: str):
    """回傳最新一條記憶，含衰退後的 conf。回傳 [text, conf] 或 []。"""
    entries = _recall_all_with_decay(name)
    return entries[-1] if entries else []

# ══════════════════════════════════════════════════════════════
# TYPES
# ══════════════════════════════════════════════════════════════

class Symbol(str):
    """A Lisp symbol — distinct from Python strings."""
    def __repr__(self): return str(self)

class LispError(Exception): pass
class TailCall(Exception):
    def __init__(self, expr, env): self.expr = expr; self.env = env

def sym(s: str) -> Symbol:
    return Symbol(s)


class Env(dict):
    """
    An environment frame. Holds variable bindings and a reference
    to the enclosing scope. This is where closures live.
    """
    def __init__(self, params=(), args=(), outer=None):
        super().__init__()
        args = list(args)
        if isinstance(params, Symbol):          # (lambda args body) — all in one list
            self[params] = args
        elif sym('.') in params:                # (lambda (x y . rest) body)
            dot = params.index(sym('.'))
            fixed, rest_name = params[:dot], params[dot + 1]
            if len(args) < len(fixed):
                raise LispError(
                    f"參數數量錯誤：至少需要 {len(fixed)} 個，"
                    f"得到 {len(args)} 個"
                )
            self.update(zip(fixed, args[:len(fixed)]))
            self[rest_name] = args[len(fixed):]
        else:
            if len(params) != len(args):
                raise LispError(
                    f"參數數量錯誤：需要 {len(params)} 個，"
                    f"得到 {len(args)} 個"
                )
            self.update(zip(params, args))
        self.outer = outer

    def find(self, name: str) -> 'Env':
        if name in self:
            return self
        if self.outer is not None:
            return self.outer.find(name)
        raise LispError(f"未定義的名稱：'{name}'")


class Lambda:
    """A user-defined function. Captures its defining environment (closure)."""
    def __init__(self, params, body, env, name=None):
        self.params = params
        self.body   = body
        self.env    = env
        self.name   = name or "#<lambda>"

    def __repr__(self):
        if isinstance(self.params, Symbol):
            p = str(self.params)
        else:
            parts = []
            for i, x in enumerate(self.params):
                if x == sym('.') and i + 1 < len(self.params):
                    parts.append('. ' + str(self.params[i + 1]))
                    break
                elif x != sym('.'):
                    parts.append(str(x))
            p = ' '.join(parts)
        return f"#<procedure {self.name} ({p})>"

    def __call__(self, *args):
        return eval_yn(self.body, Env(self.params, args, outer=self.env))


class Macro:
    """A syntax transformer. Receives unevaluated arguments."""
    def __init__(self, params, body, env):
        self.params = params
        self.body   = body
        self.env    = env


class Port:
    """A simple file-like port for I/O."""
    def __init__(self, f): self.f = f
    def __repr__(self): return f"#<port {self.f.name}>"


# ══════════════════════════════════════════════════════════════
# TOKENIZER
# ══════════════════════════════════════════════════════════════

_TOKEN = re.compile(
    r"""
    \s*
    (?:
        ;[^\n]*                        # line comment  → skip
      | (\#\|.*?\|\#)                  # block comment → skip
      | ("(?:[^"\\]|\\.)*")            # string literal
      | (\#[tf])                       # booleans #t #f
      | ([()'\`,]|,@)                  # delimiters
      | ([^\s()'"`,;]+)                # symbol / number / dot
    )
    """,
    re.VERBOSE | re.DOTALL,
)

def tokenize(src: str) -> list:
    tokens = []
    for m in _TOKEN.finditer(src):
        block, string, boolean, delim, atom = m.groups()
        if block:   continue               # skip block comment
        if string:  tokens.append(string)
        elif boolean: tokens.append(boolean)
        elif delim: tokens.append(delim)
        elif atom:  tokens.append(atom)
    return tokens


# ══════════════════════════════════════════════════════════════
# PARSER
# ══════════════════════════════════════════════════════════════

_QUOTE_MAP = {
    "'":  'quote',
    '`':  'quasiquote',
    ',':  'unquote',
    ',@': 'unquote-splicing',
}

def parse_all(src: str) -> list:
    """Parse a source string into a list of AST nodes."""
    tokens = tokenize(src)
    results = []
    pos = 0
    while pos < len(tokens):
        node, pos = _parse(tokens, pos)
        results.append(node)
    return results

def parse_all_with_lines(src: str) -> list:
    """Parse source, returning (node, line_number) pairs."""
    tokens_with_lines = []
    line = 1
    for m in _TOKEN.finditer(src):
        line += src[: m.start()].count('\n') - src[: m.start()].count('\n')
        block, string, boolean, delim, atom = m.groups()
        tok_line = src[: m.start()].count('\n') + 1
        if block:   continue
        if string:  tokens_with_lines.append((string,  tok_line))
        elif boolean: tokens_with_lines.append((boolean, tok_line))
        elif delim: tokens_with_lines.append((delim,   tok_line))
        elif atom:  tokens_with_lines.append((atom,    tok_line))

    results = []
    pos = 0
    tokens = [t for t, _ in tokens_with_lines]
    lines  = [l for _, l in tokens_with_lines]
    while pos < len(tokens):
        start_line = lines[pos] if pos < len(lines) else 1
        node, pos  = _parse(tokens, pos)
        results.append((node, start_line))
    return results

def _parse(tokens: list, pos: int):
    if pos >= len(tokens):
        raise LispError("意外的輸入結束（未閉合的括號？）")
    tok = tokens[pos]

    if tok == '(':
        lst, pos = [], pos + 1
        while pos < len(tokens) and tokens[pos] != ')':
            if tokens[pos] == '.':             # dotted / variadic notation
                pos += 1
                rest, pos = _parse(tokens, pos)
                lst.append(sym('.'))           # sentinel marker
                lst.append(rest)
                break
            item, pos = _parse(tokens, pos)
            lst.append(item)
        if pos >= len(tokens):
            raise LispError("未閉合的括號")
        return lst, pos + 1                    # consume ')'

    if tok in _QUOTE_MAP:
        name = _QUOTE_MAP[tok]
        inner, pos = _parse(tokens, pos + 1)
        return [sym(name), inner], pos

    return _atomize(tok), pos + 1

def _atomize(tok: str):
    """Convert a token string to a Python value."""
    if tok.startswith('"'):
        # unescape string
        s = tok[1:-1]
        s = s.replace('\\n', '\n').replace('\\t', '\t')
        s = s.replace('\\"', '"').replace('\\\\', '\\')
        return s
    if tok == '#t':  return True
    if tok == '#f':  return False
    try: return int(tok)
    except ValueError: pass
    try: return float(tok)
    except ValueError: pass
    return sym(tok)

def read_one(src: str):
    """Parse a single expression from src."""
    nodes = parse_all(src)
    if not nodes: return None
    if len(nodes) == 1: return nodes[0]
    return [sym('begin')] + nodes


# ══════════════════════════════════════════════════════════════
# PRINTER
# ══════════════════════════════════════════════════════════════

def yn_repr(x) -> str:
    """Convert a Yán value back to its source representation."""
    if x is True:   return '#t'
    if x is False:  return '#f'
    if x is None:   return '()'
    if isinstance(x, str) and not isinstance(x, Symbol):
        escaped = x.replace('\\', '\\\\').replace('"', '\\"') \
                   .replace('\n', '\\n').replace('\t', '\\t')
        return f'"{escaped}"'
    if isinstance(x, list):
        return '(' + ' '.join(yn_repr(e) for e in x) + ')'
    if isinstance(x, float) and x == int(x):
        return str(int(x))        # print 1.0 as 1
    return str(x)


# ══════════════════════════════════════════════════════════════
# PATTERN MATCHING  (used by the `match` special form)
# ══════════════════════════════════════════════════════════════

def _match(pat, val):
    """
    Try to match val against pat.
    Returns a dict of {Symbol: value} bindings on success, or None on failure.

    Pattern language:
      _            wildcard — matches anything, binds nothing
      x            variable — matches anything, binds x to val
      42 / "s"     literal  — matches only equal values
      ()           empty list
      'foo         quoted   — matches the symbol foo literally
      (p1 p2 p3)   list     — exact-length list match
      (p1 . rest)  dotted   — head p1, rest bound to remainder
    """
    # ── wildcard ────────────────────────────────────────────────
    if pat == sym('_'):
        return {}

    # ── quoted symbol literal  'foo ────────────────────────────
    if isinstance(pat, list) and len(pat) == 2 and pat[0] == sym('quote'):
        return {} if val == pat[1] else None

    # ── symbol → bind as variable ───────────────────────────────
    if isinstance(pat, Symbol):
        return {pat: val}

    # ── self-evaluating literals ─────────────────────────────────
    if isinstance(pat, (int, float, bool)) or \
       (isinstance(pat, str) and not isinstance(pat, Symbol)):
        return {} if val == pat else None

    # ── empty list ───────────────────────────────────────────────
    if pat == []:
        return {} if val == [] else None

    # ── list patterns ────────────────────────────────────────────
    if isinstance(pat, list):
        # dotted: (p1 p2 ... . prest)  →  [p1, p2, ..., sym('.'), prest]
        if len(pat) >= 3 and pat[-2] == sym('.'):
            head_pats = pat[:-2]
            rest_pat  = pat[-1]
            if not isinstance(val, list) or len(val) < len(head_pats):
                return None
            bindings = {}
            for hp, hv in zip(head_pats, val):
                b = _match(hp, hv)
                if b is None: return None
                bindings.update(b)
            b = _match(rest_pat, val[len(head_pats):])
            if b is None: return None
            bindings.update(b)
            return bindings

        # exact-length list
        if not isinstance(val, list) or len(val) != len(pat):
            return None
        bindings = {}
        for p, v in zip(pat, val):
            b = _match(p, v)
            if b is None: return None
            bindings.update(b)
        return bindings

    return None   # unrecognised pattern shape → no match


# ══════════════════════════════════════════════════════════════
# EVALUATOR
# ══════════════════════════════════════════════════════════════

def eval_yn(expr, env: Env) -> Any:
    """
    Evaluate an expression.

    The core loop uses an explicit while-True for tail-call elimination:
    any tail position just sets expr/env and continues instead of
    making a recursive call.
    """
    global _eval_depth, _session_depth
    _eval_depth += 1
    if _eval_depth > _session_depth:
        _session_depth = _eval_depth
    try:
      while True:
        if _eval_hook is not None:
            _eval_hook(expr)
        # ── Self-evaluating atoms ───────────────────────────────
        if expr is None or isinstance(expr, bool):
            return expr
        if isinstance(expr, (int, float)):
            return expr
        if isinstance(expr, str) and not isinstance(expr, Symbol):
            return expr          # string literal

        # ── Symbol lookup ───────────────────────────────────────
        if isinstance(expr, Symbol):
            return env.find(expr)[expr]

        # ── Empty list ──────────────────────────────────────────
        if not isinstance(expr, list) or len(expr) == 0:
            return expr

        head = expr[0]

        # ── Special forms ────────────────────────────────────────

        if head == sym('quote'):
            return expr[1]

        if head == sym('if'):
            _, cond, then, *els = expr
            test = eval_yn(cond, env)
            if test is not False and test is not None:
                expr = then
            elif els:
                expr = els[0]
            else:
                return None
            continue                                          # TCO

        if head == sym('cond'):
            for clause in expr[1:]:
                test_expr, *body = clause
                if test_expr == sym('else') or eval_yn(test_expr, env) not in (False, None):
                    expr = [sym('begin')] + body
                    break
            else:
                return None
            continue

        if head == sym('when'):
            _, cond, *body = expr
            if eval_yn(cond, env) not in (False, None):
                expr = [sym('begin')] + body
                continue
            return None

        if head == sym('unless'):
            _, cond, *body = expr
            if eval_yn(cond, env) in (False, None):
                expr = [sym('begin')] + body
                continue
            return None

        if head == sym('and'):
            result = True
            for e in expr[1:-1]:
                result = eval_yn(e, env)
                if result in (False, None): return False
            if len(expr) > 1:
                expr = expr[-1]; continue
            return result

        if head == sym('or'):
            for e in expr[1:-1]:
                result = eval_yn(e, env)
                if result not in (False, None): return result
            if len(expr) > 1:
                expr = expr[-1]; continue
            return False

        if head == sym('define'):
            _, target, *rest = expr
            if isinstance(target, list):          # (define (f x) body) sugar
                fname, *params = target
                body = rest[0] if len(rest) == 1 else [sym('begin')] + rest
                lam = Lambda([x if x == sym('.') else sym(str(x)) for x in params],
                             body, env, name=str(fname))
                env[fname] = lam
            else:
                val = eval_yn(rest[0], env)
                if isinstance(val, Lambda) and val.name == "#<lambda>":
                    val.name = str(target)
                env[target] = val
            return None

        if head == sym('set!'):
            _, name, val_expr = expr
            env.find(name)[name] = eval_yn(val_expr, env)
            return None

        if head == sym('lambda'):
            _, params, *body = expr
            if isinstance(params, Symbol):       # (lambda args body) — all variadic
                p = params
            else:
                # preserve dot sentinel for (lambda (x y . rest) body)
                p = [x if x == sym('.') else sym(str(x)) for x in params]
            b = body[0] if len(body) == 1 else [sym('begin')] + body
            return Lambda(p, b, env)

        if head == sym('begin'):
            if len(expr) == 1: return None
            for e in expr[1:-1]:
                eval_yn(e, env)
            expr = expr[-1]
            continue                                          # TCO

        if head == sym('let'):
            _, bindings, *body = expr
            if isinstance(bindings, Symbol):      # named let
                name     = bindings
                bindings = expr[2]
                body     = expr[3:]
                params   = [sym(b[0]) for b in bindings]
                inits    = [eval_yn(b[1], env) for b in bindings]
                body_e   = body[0] if len(body) == 1 else [sym('begin')] + body
                lam = Lambda(params, body_e, env, name=str(name))
                loop_env = Env(outer=env)
                loop_env[name] = lam
                lam.env = loop_env
                env  = Env(params, inits, outer=loop_env)
                expr = body_e
                continue
            params = [sym(b[0]) for b in bindings]
            args   = [eval_yn(b[1], env) for b in bindings]
            env    = Env(params, args, outer=env)
            expr   = body[0] if len(body) == 1 else [sym('begin')] + body
            continue

        if head == sym('let*'):
            _, bindings, *body = expr
            new_env = Env(outer=env)
            for name, val_expr in bindings:
                new_env[sym(name)] = eval_yn(val_expr, new_env)
            env  = new_env
            expr = body[0] if len(body) == 1 else [sym('begin')] + body
            continue

        if head == sym('letrec'):
            _, bindings, *body = expr
            new_env = Env(outer=env)
            for name, _ in bindings:
                new_env[sym(name)] = None
            for name, val_expr in bindings:
                new_env[sym(name)] = eval_yn(val_expr, new_env)
            env  = new_env
            expr = body[0] if len(body) == 1 else [sym('begin')] + body
            continue

        if head == sym('do'):
            # (do ((var init step) ...) (test result) body...)
            _, var_specs, (test_expr, *result), *do_body = expr
            vars_  = [sym(v[0]) for v in var_specs]
            inits  = [eval_yn(v[1], env) for v in var_specs]
            steps  = [v[2] if len(v) > 2 else v[0] for v in var_specs]
            loop_env = Env(vars_, inits, outer=env)
            while eval_yn(test_expr, loop_env) in (False, None):
                for e in do_body:
                    eval_yn(e, loop_env)
                new_vals = [eval_yn(s, loop_env) for s in steps]
                loop_env.update(zip(vars_, new_vals))
            expr = result[0] if result else None
            env  = loop_env
            continue

        if head == sym('quasiquote'):
            return _expand_quasi(expr[1], env)

        if head == sym('define-macro'):
            _, spec, *body = expr
            if isinstance(spec, list):          # (define-macro (name p ...) body)
                name   = spec[0]
                params = spec[1:]
            else:                               # (define-macro name params body)
                name   = spec
                params = body[0]
                body   = body[1:]
            b = body[0] if len(body) == 1 else [sym('begin')] + body
            env[name] = Macro(params, b, env)
            return None

        if head == sym('apply'):
            fn   = eval_yn(expr[1], env)
            args = eval_yn(expr[2], env)
            if not callable(fn):
                raise LispError(f"apply: 不是可呼叫的值：{fn!r}")
            if isinstance(fn, Lambda):
                env  = Env(fn.params, args, outer=fn.env)
                expr = fn.body
                continue
            return fn(*args)

        if head == sym('eval'):
            expr = eval_yn(expr[1], env)
            continue

        if head == sym('try'):
            # (try body (catch var handler))
            # Optional: (try body) — re-raises if no catch clause
            body_expr   = expr[1]
            catch_clause = expr[2] if len(expr) > 2 else None
            try:
                return eval_yn(body_expr, env)
            except Exception as _exc:
                if catch_clause is None:
                    raise
                _var     = catch_clause[1]
                _handler = catch_clause[2]
                env  = Env([_var], [str(_exc)], outer=env)
                expr = _handler
                continue

        if head == sym('match'):
            # (match expr (pat body) ...)
            val = eval_yn(expr[1], env)
            for clause in expr[2:]:
                pat, body = clause[0], clause[1]
                bindings = _match(pat, val)
                if bindings is not None:
                    env  = Env(list(bindings.keys()),
                               list(bindings.values()), outer=env)
                    expr = body
                    break   # TCO: fall through to next while iteration
            else:
                raise LispError(f"match: 沒有匹配的模式：{yn_repr(val)}")
            continue

        if head == sym('with-memory'):
            # (with-memory name body...)
            # 把這個 name 的歷史綁進環境，body 可以直接用 memory/conf/count
            _, name_expr, *body = expr
            mname   = str(eval_yn(name_expr, env))
            history = _recall_all_with_decay(mname)
            last    = history[-1] if history else []
            mem_env = Env(outer=env)
            mem_env[sym('memory')]       = history
            mem_env[sym('memory-last')]  = last
            mem_env[sym('memory-text')]  = last[0] if last else None
            mem_env[sym('memory-conf')]  = last[1] if len(last) > 1 else 0.0
            mem_env[sym('memory-count')] = len(history)
            mem_env[sym('memory-avg-conf')] = (
                sum(e[1] for e in history) / len(history) if history else 0.0
            )
            mem_env[sym('memory-name')]  = mname
            env  = mem_env
            expr = [sym('begin')] + body
            continue

        if head == sym('import'):
            # (import "path")              → load into current env
            # (import "path" as name)      → load into namespace function
            raw_path = expr[1]
            path = eval_yn(raw_path, env) if not isinstance(raw_path, str) else raw_path
            # Resolve: try cwd, then yan/ parent, then relative to yan.py
            _here = os.path.dirname(os.path.abspath(__file__))
            resolved = None
            for candidate in [path,
                               os.path.join(_here, '..', path),
                               os.path.join(_here, path)]:
                if os.path.exists(candidate):
                    resolved = candidate; break
            if resolved is None:
                raise LispError(f"import：找不到檔案 {path!r}")
            path = resolved
            if len(expr) >= 4 and str(expr[2]) == 'as':
                ns_name = expr[3]
                ns_env  = Env(outer=env)
                _exec_file(path, ns_env)
                _ns_env = ns_env  # capture
                def _make_ns(e):
                    def _ns(key):
                        k = key if isinstance(key, Symbol) else sym(str(key))
                        try:    return e.find(k)[k]
                        except: raise LispError(f"模組中未定義：{key}")
                    return _ns
                env[ns_name] = _make_ns(ns_env)
            else:
                _exec_file(path, env)
            return None

        if head == sym('values'):
            return tuple(eval_yn(e, env) for e in expr[1:])

        if head == sym('call-with-values'):
            producer = eval_yn(expr[1], env)
            consumer = eval_yn(expr[2], env)
            vals = producer()
            if isinstance(vals, tuple):
                return consumer(*vals)
            return consumer(vals)

        # ── Tail position: macro expansion ──────────────────────
        try:
            fn = eval_yn(head, env)
        except LispError as _e:
            raise LispError(f"{_e}\n  在求值 {yn_repr(head)} 時") from None
        except Exception as _e:
            raise LispError(f"{type(_e).__name__}: {_e}\n  在求值 {yn_repr(head)} 時") from None

        if isinstance(fn, Macro):
            args = expr[1:]
            expanded = eval_yn(fn.body, Env(fn.params, args, outer=fn.env))
            expr = expanded
            continue

        # ── Function application ─────────────────────────────────
        args = [eval_yn(a, env) for a in expr[1:]]

        if callable(fn) and not isinstance(fn, Lambda):
            _fn_name = getattr(fn, '__name__', yn_repr(head))
            try:
                return fn(*args)
            except LispError:
                raise
            except TypeError as _te:
                raise LispError(
                    f"引數錯誤 ({_fn_name})：{_te}"
                ) from None
            except Exception as _ex:
                raise LispError(
                    f"{type(_ex).__name__} ({_fn_name})：{_ex}"
                ) from None

        if isinstance(fn, Lambda):
            _fn_name = fn.name
            if len(fn.params) != len(args) and not any(
                p == sym('.') for p in (fn.params if isinstance(fn.params, list) else [])
            ) and not isinstance(fn.params, Symbol):
                expected = len(fn.params)
                got      = len(args)
                raise LispError(
                    f"引數數量錯誤 ({_fn_name})：需要 {expected} 個，給了 {got} 個"
                )
            env  = Env(fn.params, args, outer=fn.env)
            expr = fn.body
            continue

        raise LispError(f"不是可呼叫的值：{yn_repr(fn)}")
    finally:
        _eval_depth -= 1


def _expand_quasi(expr, env):
    """Expand quasiquote. Handles unquote and unquote-splicing."""
    if not isinstance(expr, list):
        return expr
    if expr and expr[0] == sym('unquote'):
        return eval_yn(expr[1], env)
    result = []
    for item in expr:
        if isinstance(item, list) and item and item[0] == sym('unquote-splicing'):
            result.extend(eval_yn(item[1], env))
        else:
            result.append(_expand_quasi(item, env))
    return result


# ══════════════════════════════════════════════════════════════
# STANDARD ENVIRONMENT
# ══════════════════════════════════════════════════════════════

def _yn_format(template: str, *args) -> str:
    """
    雙模式格式化：
      Scheme: ~a  display  ~s  repr  ~%  newline  ~~  tilde
      C-style: %s  %d  %f  %.2f  %i  等（委託 Python % 處理）
    Returns the formatted string.
    """
    import re as _re
    if _re.search(r'%[sdifg]|%\.\d+[fg]', template):
        # C-style: convert args to Python types first
        converted = []
        for a in args:
            if isinstance(a, bool):
                converted.append(a)
            elif isinstance(a, (int, float)):
                converted.append(a)
            else:
                converted.append(str(a))
        try:
            return template % tuple(converted)
        except TypeError:
            pass  # fall through to Scheme mode

    result = []
    arg_iter = iter(args)
    i = 0
    while i < len(template):
        if template[i] == '~' and i + 1 < len(template):
            code = template[i + 1]
            if code == 'a':
                v = next(arg_iter, '')
                result.append(
                    v if isinstance(v, str) and not isinstance(v, Symbol)
                    else yn_repr(v)
                )
            elif code == 's':
                v = next(arg_iter, '')
                result.append(yn_repr(v))
            elif code == '%':
                result.append('\n')
            elif code == '~':
                result.append('~')
            else:
                result.append('~')
                result.append(code)
            i += 2
        else:
            result.append(template[i])
            i += 1
    return ''.join(result)


def _make_global_env() -> Env:
    env = Env()

    # ── Arithmetic ───────────────────────────────────────────────
    env.update({
        sym('+'): lambda *a: sum(a),
        sym('-'): lambda a, *r: a if not r else a - sum(r),
        sym('*'): lambda *a: functools.reduce(operator.mul, a, 1),
        sym('/'): lambda a, b: a / b,
        sym('//'): operator.floordiv,
        sym('%'): operator.mod,
        sym('**'): operator.pow,
        sym('abs'): abs,
        sym('max'): max,
        sym('min'): min,
        sym('round'): round,
        sym('floor'): math.floor,
        sym('ceil'): math.ceil,
        sym('sqrt'): math.sqrt,
        sym('expt'): math.pow,
        sym('log'): math.log,
        sym('exp'): math.exp,
        sym('sin'): math.sin,
        sym('cos'): math.cos,
        sym('tan'): math.tan,
        sym('atan'): math.atan2,
        sym('pi'): math.pi,
        sym('e'): math.e,
        sym('gcd'): math.gcd,
        sym('lcm'): lambda a, b: abs(a*b) // math.gcd(a,b) if a and b else 0,
        sym('modulo'): lambda a, b: a % b,
        sym('quotient'): operator.floordiv,
        sym('remainder'): lambda a, b: int(math.fmod(a, b)),
        sym('even?'): lambda n: n % 2 == 0,
        sym('odd?'): lambda n: n % 2 != 0,
        sym('zero?'): lambda n: n == 0,
        sym('positive?'): lambda n: n > 0,
        sym('negative?'): lambda n: n < 0,
        sym('exact->inexact'): float,
        sym('inexact->exact'): int,
        sym('number->string'): lambda n, base=10: (
            format(int(n), 'b') if base == 2 else
            format(int(n), 'o') if base == 8 else
            format(int(n), 'x') if base == 16 else str(n)
        ),
        sym('string->number'): lambda s, base=10: (
            int(s, base) if isinstance(s, str) else s
        ),
    })

    # ── Comparison ───────────────────────────────────────────────
    env.update({
        sym('='): lambda a, b: a == b,
        sym('<'): operator.lt,
        sym('>'): operator.gt,
        sym('<='): operator.le,
        sym('>='): operator.ge,
        sym('not'): lambda x: x is False or x is None,
        sym('eq?'): lambda a, b: a is b or a == b,
        sym('eqv?'): lambda a, b: a == b,
        sym('equal?'): lambda a, b: a == b,
    })

    # ── Pairs & Lists ────────────────────────────────────────────
    env.update({
        sym('cons'): lambda a, b: [a] + (b if isinstance(b, list) else [b]),
        sym('car'):  lambda lst: (lst[0] if lst else (_ for _ in ()).throw(LispError("car: 空串列"))),
        sym('cdr'):  lambda lst: (lst[1:] if lst else (_ for _ in ()).throw(LispError("cdr: 空串列"))),
        sym('cadr'): lambda lst: lst[1],
        sym('caddr'): lambda lst: lst[2],
        sym('cadddr'): lambda lst: lst[3],
        sym('list'): lambda *a: list(a),
        sym('list?'): lambda x: isinstance(x, list),
        sym('pair?'): lambda x: isinstance(x, list) and bool(x),
        sym('null?'): lambda x: x == [] or x is None,
        sym('length'): len,
        sym('append'): lambda *lsts: functools.reduce(
            lambda a, b: a + (b if isinstance(b, list) else [b]), lsts, []),
        sym('reverse'): lambda lst: lst[::-1],
        sym('list-tail'): lambda lst, k: lst[k:],
        sym('list-ref'): lambda lst, k: lst[k],
        sym('list-copy'): lambda lst: lst[:],
        sym('last-pair'): lambda lst: lst[-1:],
        sym('flatten'): lambda lst: (
            functools.reduce(lambda a, b: a + (b if isinstance(b, list) else [b]), lst, [])
        ),
        sym('iota'): lambda n, start=0, step=1: list(range(start, start + n * step, step)),
        sym('make-list'): lambda n, fill=None: [fill] * n,
        sym('list-set!'): lambda lst, k, v: lst.__setitem__(k, v) or lst,
        sym('assoc'): lambda key, alist: next(
            (pair for pair in alist if pair[0] == key), False),
        sym('assv'): lambda key, alist: next(
            (pair for pair in alist if pair[0] == key), False),
        sym('member'): lambda x, lst: (lst[lst.index(x):] if x in lst else False),
        sym('memv'): lambda x, lst: (lst[lst.index(x):] if x in lst else False),
        sym('for-each'): lambda fn, *lsts: [fn(*args) for args in zip(*lsts)] and None,
        sym('map'): lambda fn, *lsts: list(map(fn, *lsts)),
        sym('filter'): lambda fn, lst: [x for x in lst if fn(x) not in (False, None)],
        sym('fold-left'): lambda fn, init, lst: functools.reduce(fn, lst, init),
        sym('fold-right'): lambda fn, init, lst: functools.reduce(lambda a, b: fn(b, a), reversed(lst), init),
        sym('reduce'): lambda fn, init, lst: functools.reduce(fn, lst, init),
        sym('any'): lambda fn, lst: any(fn(x) not in (False, None) for x in lst),
        sym('every'): lambda fn, lst: all(fn(x) not in (False, None) for x in lst),
        sym('sort'): lambda lst, less=None: (
            sorted(lst, key=functools.cmp_to_key(lambda a,b: -1 if less(a,b) else 1))
            if less else sorted(lst)
        ),
        sym('zip'): lambda *lsts: [list(t) for t in zip(*lsts)],
        sym('take'): lambda lst, n: lst[:n],
        sym('drop'): lambda lst, n: lst[n:],
        sym('range'): lambda *args: list(range(*[int(a) for a in args])),
    })

    # ── Strings ──────────────────────────────────────────────────
    env.update({
        sym('string'): lambda *chars: ''.join(chars),
        sym('string-length'): len,
        sym('string-ref'): lambda s, k: s[k],
        sym('substring'): lambda s, start, end=None: s[start:end],
        sym('string-append'): lambda *ss: ''.join(ss),
        sym('string->list'): lambda s: list(s),
        sym('list->string'): lambda lst: ''.join(lst),
        sym('string-copy'): lambda s: s[:],
        sym('string-upcase'): str.upper,
        sym('string-downcase'): str.lower,
        sym('string-contains'): lambda s, sub: sub in s,
        sym('string-split'): lambda s, sep=' ': s.split(sep),
        sym('string-join'): lambda lst, sep='': sep.join(lst),
        sym('string-trim'): str.strip,
        sym('symbol->string'): str,
        sym('string->symbol'): sym,
        sym('string-replace'): lambda s, old, new: s.replace(old, new),
        sym('string-format'): lambda fmt, *args: fmt.format(*args),
        sym('format'): _yn_format,
        sym('printf'): lambda fmt, *args: print(_yn_format(fmt, *args), end='') or None,
        sym('sprintf'): _yn_format,
    })

    # ── Characters ───────────────────────────────────────────────
    env.update({
        sym('char->integer'): ord,
        sym('integer->char'): chr,
        sym('char-alphabetic?'): str.isalpha,
        sym('char-numeric?'): str.isdigit,
        sym('char-whitespace?'): str.isspace,
        sym('char-upcase'): str.upper,
        sym('char-downcase'): str.lower,
    })

    # ── Type predicates ──────────────────────────────────────────
    env.update({
        sym('number?'): lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        sym('integer?'): lambda x: isinstance(x, int) and not isinstance(x, bool),
        sym('real?'): lambda x: isinstance(x, float),
        sym('string?'): lambda x: isinstance(x, str) and not isinstance(x, Symbol),
        sym('symbol?'): lambda x: isinstance(x, Symbol),
        sym('boolean?'): lambda x: isinstance(x, bool),
        sym('procedure?'): lambda x: callable(x) or isinstance(x, Lambda),
        sym('port?'): lambda x: isinstance(x, Port),
        sym('char?'): lambda x: isinstance(x, str) and len(x) == 1,
        sym('vector?'): lambda x: isinstance(x, list),
    })

    # ── I/O ──────────────────────────────────────────────────────
    _stdout_port = Port(sys.stdout)
    _stdin_port  = Port(sys.stdin)
    env.update({
        sym('display'):  lambda x, port=None: print(
            x if isinstance(x, str) and not isinstance(x, Symbol) else yn_repr(x),
            end='', file=(port.f if port else sys.stdout)) or None,
        sym('write'):    lambda x, port=None: print(
            yn_repr(x), end='', file=(port.f if port else sys.stdout)) or None,
        sym('newline'):  lambda port=None: print(file=(port.f if port else sys.stdout)) or None,
        sym('read-line'): lambda port=None: (port.f if port else sys.stdin).readline().rstrip('\n'),
        sym('read'):     lambda port=None: read_one((port.f if port else sys.stdin).readline()),
        sym('eval-string'): lambda s: eval_yn(read_one(str(s)), env),
        sym('print'):    lambda *xs: print(*[
            x if isinstance(x, str) and not isinstance(x, Symbol) else yn_repr(x)
            for x in xs]) or None,
        sym('current-input-port'):  lambda: _stdin_port,
        sym('current-output-port'): lambda: _stdout_port,
        sym('open-input-file'):  lambda path: Port(open(path, 'r', encoding='utf-8')),
        sym('open-output-file'): lambda path: Port(open(path, 'w', encoding='utf-8')),
        sym('close-port'):  lambda p: p.f.close() or None,
        sym('with-output-to-file'): lambda path, thunk: _with_output(path, thunk),
        sym('load'): lambda path: _exec_file(path, env),
        # ── 便利的檔案讀寫 ──────────────────────────────────────────
        sym('read-file'):  lambda path: open(path, encoding='utf-8').read(),
        sym('write-file'): lambda path, text: (
            open(path, 'w', encoding='utf-8').write(str(text)) and None),
        sym('append-file'): lambda path, text: (
            open(path, 'a', encoding='utf-8').write(str(text)) and None),
        sym('file-exists?'): lambda path: os.path.exists(path),
        sym('delete-file'):  lambda path: os.remove(path) or None,
        sym('file->lines'):  lambda path: open(path, encoding='utf-8').read().splitlines(),
        sym('lines->file'):  lambda path, lines: open(path, 'w', encoding='utf-8').write(
            '\n'.join(str(l) for l in lines)) and None,
        # ── 目錄操作 ────────────────────────────────────────────────
        sym('current-directory'): os.getcwd,
        sym('list-directory'):    lambda path='.': os.listdir(path),
        sym('make-directory'):    lambda path: os.makedirs(path, exist_ok=True) or None,
        sym('path-join'):         lambda *parts: os.path.join(*parts),
        sym('path-exists?'):      os.path.exists,
        sym('path-file?'):        os.path.isfile,
        sym('path-directory?'):   os.path.isdir,
    })

    # ── 記憶 ─────────────────────────────────────────────────────
    #
    # 言的歷史是用言自己的語法寫的，存在 journal.yn。
    # 這些函式讓言查詢自己的過去。
    #
    # journal entry 格式：
    #   (run "時間戳" 秒數 表達式數 最大深度 錯誤數 ("檔案"...))
    #
    def _times_run():
        entries = _load_journal()
        return sum(1 for e in entries if isinstance(e, list) and e and e[0] == sym('run'))

    def _my_history():
        return _load_journal()

    def _age():
        entries = _load_journal()
        return sum(e[2] for e in entries if isinstance(e, list) and len(e) > 2 and isinstance(e[2], (int, float)))

    def _last_run():
        entries = _load_journal()
        return entries[-1] if entries else []

    def _total_expressions():
        entries = _load_journal()
        return sum(e[3] for e in entries if isinstance(e, list) and len(e) > 3 and isinstance(e[3], (int, float)))

    def _self_summary():
        all_entries = _load_journal()
        # 只統計 (run ...) 類型
        entries = [e for e in all_entries
                   if isinstance(e, list) and e and e[0] == sym('run')]
        n = len(entries)
        if n == 0:
            return [sym('self'),
                    [sym('runs'), 0],
                    [sym('age-secs'), 0],
                    [sym('total-exprs'), 0],
                    [sym('error-rate'), 0],
                    [sym('max-depth'), 0],
                    [sym('trend'), sym('unknown')],
                    [sym('health'), sym('unknown')]]

        def field(e, i, default=0):
            try: return e[i]
            except: return default

        durations  = [field(e, 2) for e in entries]
        exprs_list = [field(e, 3) for e in entries]
        depths     = [field(e, 4) for e in entries]
        errors     = [field(e, 5) for e in entries]

        total_secs  = round(sum(d for d in durations if isinstance(d, (int, float))), 3)
        total_exprs = sum(x for x in exprs_list if isinstance(x, (int, float)))
        error_runs  = sum(1 for e in errors if isinstance(e, (int, float)) and e > 0)
        max_depth   = max((d for d in depths if isinstance(d, (int, float))), default=0)
        error_rate  = round(error_runs / n, 3)

        # 趨勢：最近三次 vs 之前三次的表達式數
        trend = sym('stable')
        if n >= 6:
            recent = sum(x for x in exprs_list[-3:] if isinstance(x, (int, float))) / 3
            older  = sum(x for x in exprs_list[-6:-3] if isinstance(x, (int, float))) / 3
            if recent > older * 1.2:
                trend = sym('growing')
            elif recent < older * 0.8:
                trend = sym('shrinking')

        # 最近一次測試結果（從完整記錄找，不只是 run 類型）
        last_test = next(
            (e for e in reversed(all_entries)
             if isinstance(e, list) and e and e[0] == sym('test')),
            None
        )
        v_score, v_trend = _vitality_score()

        return [sym('self'),
                [sym('runs'),        n],
                [sym('age-secs'),    total_secs],
                [sym('total-exprs'), total_exprs],
                [sym('error-rate'),  error_rate],
                [sym('max-depth'),   max_depth],
                [sym('trend'),       trend],
                [sym('vitality'),    v_score],
                [sym('vitality-trend'), v_trend]]

    def _history_series(kind='exprs', last=20):
        """
        Return recent history values.
          kind: 'exprs' | 'depth' | 'duration' | 'errors'
          last: max points to return from the tail
        """
        all_entries = _load_journal()
        entries = [e for e in all_entries
                   if isinstance(e, list) and e and e[0] == sym('run')]
        idx_map = {'duration': 2, 'exprs': 3, 'depth': 4, 'errors': 5}
        idx = idx_map.get(str(kind), 3)
        values = []
        for e in entries:
            if isinstance(e, list) and len(e) > idx and isinstance(e[idx], (int, float)):
                values.append(e[idx])
        n = max(1, int(last))
        return values[-n:]

    def _history_sparkline(kind='exprs', last=20):
        """
        Build an ASCII sparkline from recent history.
        Useful in terminal and pure-text contexts.
        """
        values = _history_series(kind, last)
        if not values:
            return ''
        chars = " .:-=+*#%@"
        lo, hi = min(values), max(values)
        if hi == lo:
            return '-' * len(values)
        out = []
        for v in values:
            t = (v - lo) / (hi - lo)
            i = int(round(t * (len(chars) - 1)))
            out.append(chars[i])
        return ''.join(out)

    env.update({
        sym('times-run'):         lambda: _times_run(),
        sym('vitality'):          lambda: _vitality_score()[0],
        sym('vitality-trend'):    lambda: _vitality_score()[1],
        # ── Host API（言只看到數字，不知道來源）──────────────────
        sym('host-last-touch-days'): lambda: _host_last_touch_days(),
        sym('host-journal-lag'):     lambda: _host_journal_lag(),
        sym('host-heartbeat'):       lambda: True,   # runtime 活著就是 True
        sym('am-i-forgotten?'):      lambda threshold=30: (
            lambda d, t: [d > t,
                          round(max(0.0, min(1.0, d / max(t * 3, 1))), 3)]
        )(_host_journal_lag(), float(threshold)),  # 回傳 [bool, confidence]
        sym('my-history'):        lambda: _my_history(),
        sym('my-history-all'):    lambda: _load_journal() + (
            _load_file(_ARCHIVE_PATH) if os.path.exists(_ARCHIVE_PATH) else []
        ),
        sym('archive-path'):      lambda: _ARCHIVE_PATH,
        sym('archive-summary'):   lambda: next(
            (e for e in _load_journal()
             if isinstance(e, list) and e and str(e[0]) == 'summary'),
            []
        ),
        sym('age'):               lambda: _age(),
        sym('last-run'):          lambda: _last_run(),
        sym('total-expressions'): lambda: _total_expressions(),
        sym('yan-version'):       lambda: YAN_VERSION,
        sym('journal-path'):      lambda: _JOURNAL_PATH,
        sym('self-summary'):      lambda: _self_summary(),
        sym('history-series'):    lambda kind='exprs', last=20: _history_series(kind, last),
        sym('history-sparkline'): lambda kind='exprs', last=20: _history_sparkline(kind, last),
        sym('person-visits'): lambda name: sum(
            1 for e in _load_user_journal(str(name))
            if isinstance(e, list) and len(e) >= 2
            and e[0] == sym('meet') and e[1] == str(name)
        ),
        sym('record-visit'): lambda name: _append_user(
            str(name),
            f'(meet "{name}" "{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}")'
        ) or None,
        # remember: (remember name text) or (remember name text conf)
        sym('remember'): lambda name, text, conf=1.0: _append_user(
            str(name),
            f'(note "{name}" "{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}"'
            f' "{str(text).replace(chr(34), chr(39))}" {float(conf)})'
        ) or None,
        # pin: 釘住一條記憶，衰退極慢（0.995/週，最低 0.85）
        sym('pin'): lambda name, text: _append_user(
            str(name),
            f'(note "{name}" "{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}"'
            f' "{str(text).replace(chr(34), chr(39))}" 1.0 pinned)'
        ) or None,
        # recall: 回傳最近一條 [text conf pinned?]，conf 考慮時間衰退
        sym('recall'): lambda name: _recall_with_decay(str(name)),
        # recall-all: 回傳所有 [text conf pinned?] 清單（已考慮衰退）
        sym('recall-all'): lambda name: _recall_all_with_decay(str(name)),
        # recall-recent: 回傳最近 n 條
        sym('recall-recent'): lambda name, n=5: _recall_all_with_decay(str(name))[-(int(n)):],
        # recall-confident: 回傳 conf >= threshold 的最新一條
        sym('recall-confident'): lambda name, threshold: next(
            (pair for pair in reversed(_recall_all_with_decay(str(name)))
             if isinstance(pair, list) and len(pair) >= 2
             and pair[1] >= float(threshold)),
            []
        ),
        # recall-avg-conf: 最近 n 條的平均 confidence（感受穩定程度）
        sym('recall-avg-conf'): lambda name, n=5: (
            lambda entries: sum(e[1] for e in entries) / len(entries)
            if entries else 0.0
        )(_recall_all_with_decay(str(name))[-(int(n)):]),
        # recall-count: 共有幾條記憶
        sym('recall-count'): lambda name: len(_recall_all_with_decay(str(name))),
        # forget: 寫入一條低 conf 記憶，讓這個名字的印象淡化
        sym('forget'): lambda name: _append_user(
            str(name),
            f'(note "{name}" "{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}"'
            f' "forgotten" 0.05)'
        ) or None,
        sym('person-notes'): lambda name: [
            e[3] for e in _load_user_journal(str(name))
            if isinstance(e, list) and len(e) >= 4
            and e[0] == sym('note') and e[1] == str(name)
        ],
        sym('sort'): lambda lst, less=None: (
            sorted(lst, key=functools.cmp_to_key(
                lambda a, b: -1 if less(a, b) else (1 if less(b, a) else 0)))
            if less else sorted(lst)
        ),
        sym('record-test-result'): lambda pass_, fail: _append_raw(
            f'(test "{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}" '
            f'{int(pass_)} {int(fail)} '
            f'{int(pass_ + fail)} '
            f'{"ok" if fail == 0 else "fail"})'
        ) or None,
        sym('last-test-result'):  lambda: next(
            (e for e in reversed(_load_journal())
             if isinstance(e, list) and e and e[0] == sym('test')),
            []
        ),
        sym('load'):              lambda path: run_file(
            path if os.path.isabs(path) else os.path.join(
                os.path.dirname(os.path.abspath(__file__)), '..', path),
            env),
    })

    # ── Control & Misc ───────────────────────────────────────────
    env.update({
        sym('#t'): True,
        sym('#f'): False,
        sym('else'): True,
        sym('nil'): [],
        sym('void'): None,
        sym('error'): lambda msg, *irritants: (_ for _ in ()).throw(
            LispError(str(msg) + (
                ': ' + ' '.join(yn_repr(i) for i in irritants) if irritants else ''
            ))
        ),
        sym('assert'): lambda cond, *msg: None if (cond not in (False, None)) else (
            (_ for _ in ()).throw(LispError('斷言失敗' + (': ' + str(msg[0]) if msg else '')))
        ),
        sym('gensym'): lambda: sym(f'#g{id(object())}'),
        sym('not'): lambda x: x is False or x is None,
        sym('boolean=?'): lambda a, b: bool(a) == bool(b),
        sym('exit'): lambda code=0: (_print_farewell(), sys.exit(int(code)))[1],
        sym('chat'): lambda: run_file(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'chat.yn'),
            env) and None,
        sym('time'): lambda thunk: _timed(thunk),
        sym('random'): __import__('random').random,
        sym('random-integer'): __import__('random').randint,
        sym('shuffle'): lambda lst: __import__('random').sample(lst, len(lst)),

        # ── 時間 ────────────────────────────────────────────────────
        sym('now'):        lambda: __import__('datetime').datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        sym('timestamp'):  lambda: __import__('time').time(),
        sym('sleep'):      lambda s: __import__('time').sleep(s) or None,

        # ── Python FFI ───────────────────────────────────────────────
        # (py-import "os")               → Python module 物件
        # (py-call mod "listdir" ".")     → mod.listdir(".")
        # (py-get  mod "sep")             → mod.sep
        # (py-set! mod "attr" val)        → setattr
        # (py-apply mod "method" '(args)) → call with list of args
        # (py-eval "1 + 2")              → Python eval
        # (py->list obj)                 → list(obj)
        sym('py-import'):  lambda name: __import__('importlib').import_module(str(name)),
        sym('py-call'):    lambda obj, method, *args: getattr(obj, str(method))(*args),
        sym('py-get'):     lambda obj, attr: getattr(obj, str(attr)),
        sym('py-set!'):    lambda obj, attr, val: setattr(obj, str(attr), val) or None,
        sym('py-has?'):    lambda obj, attr: hasattr(obj, str(attr)),
        sym('py-apply'):   lambda obj, method, args: getattr(obj, str(method))(*args),
        sym('py-eval'):    lambda code: eval(str(code)),
        sym('py->list'):   lambda obj: list(obj),
        sym('py->str'):    str,
        sym('py->int'):    int,
        sym('py->float'):  float,
        sym('py->bool'):   bool,
        sym('py-type'):    lambda obj: type(obj).__name__,
        sym('py-dir'):     lambda obj: dir(obj),
    })

    return env


def _with_output(path, thunk):
    with open(path, 'w', encoding='utf-8') as f:
        old = sys.stdout
        sys.stdout = f
        try: thunk()
        finally: sys.stdout = old
    return None

def _timed(thunk):
    t0 = time.perf_counter()
    result = thunk()
    dt = time.perf_counter() - t0
    print(f"; 耗時 {dt*1000:.3f} ms")
    return result

def _exec_file(path, env):
    with open(path, encoding='utf-8') as f:
        src = f.read()
    for node in parse_all(src):
        eval_yn(node, env)
    return None


# ══════════════════════════════════════════════════════════════
# PRELUDE  (Yán code evaluated at startup)
# ══════════════════════════════════════════════════════════════

PRELUDE = r"""
; ─── 函式組合 ─────────────────────────────────────────────────
(define (compose . fns)
  (if (null? fns)
      (lambda (x) x)
      (lambda (x)
        ((car fns) ((apply compose (cdr fns)) x)))))

(define (identity x) x)
(define (const x) (lambda args x))
(define (flip f) (lambda (x y) (f y x)))
(define (curry f) (lambda (x) (lambda (y) (f x y))))
(define (curry3 f) (lambda (x) (lambda (y) (lambda (z) (f x y z)))))
(define (partial f . bound)
  (lambda rest (apply f (append bound rest))))

; ─── 算術工具 ─────────────────────────────────────────────────
(define (square x) (* x x))
(define (cube x) (* x x x))
(define (inc x) (+ x 1))
(define (dec x) (- x 1))
(define (average a b) (/ (+ a b) 2))
(define (clamp x lo hi) (max lo (min hi x)))
(define (between? x lo hi) (and (>= x lo) (<= x hi)))

; ─── 串列工具 ─────────────────────────────────────────────────
(define (second lst) (cadr lst))
(define (third lst)  (caddr lst))
(define (fourth lst) (cadddr lst))

(define (flatten lst)
  (cond
    ((null? lst) '())
    ((pair? (car lst)) (append (flatten (car lst)) (flatten (cdr lst))))
    (else (cons (car lst) (flatten (cdr lst))))))

(define (zip-with f lst1 lst2)
  (if (or (null? lst1) (null? lst2))
      '()
      (cons (f (car lst1) (car lst2))
            (zip-with f (cdr lst1) (cdr lst2)))))

(define (group-by n lst)
  (if (null? lst) '()
      (cons (take lst n)
            (group-by n (drop lst n)))))

(define (unique lst)
  (fold-left (lambda (acc x)
               (if (member x acc) acc (append acc (list x))))
             '() lst))

(define (count-if pred lst)
  (fold-left (lambda (n x) (if (pred x) (+ n 1) n)) 0 lst))

(define (sum lst) (fold-left + 0 lst))
(define (product lst) (fold-left * 1 lst))
(define (maximum lst) (fold-left max (car lst) (cdr lst)))
(define (minimum lst) (fold-left min (car lst) (cdr lst)))

(define (repeat x n)
  (if (= n 0) '() (cons x (repeat x (- n 1)))))

(define (interleave lst1 lst2)
  (cond ((null? lst1) lst2)
        ((null? lst2) lst1)
        (else (cons (car lst1)
                    (interleave lst2 (cdr lst1))))))

; ─── 數學 ─────────────────────────────────────────────────────
(define (factorial n)
  (let loop ((i n) (acc 1))
    (if (<= i 0) acc (loop (- i 1) (* acc i)))))

(define (fibonacci n)
  (let loop ((a 0) (b 1) (i n))
    (if (= i 0) a (loop b (+ a b) (- i 1)))))

(define (prime? n)
  (if (< n 2) #f
      (let loop ((i 2))
        (cond ((> (* i i) n) #t)
              ((= (modulo n i) 0) #f)
              (else (loop (+ i 1)))))))

(define (primes-up-to n)
  (filter prime? (iota (- n 1) 2)))

; ─── 字串 ─────────────────────────────────────────────────────
(define (string-repeat s n)
  (apply string-append (repeat s n)))

(define (string-pad-left s n ch)
  (string-append (string-repeat ch (max 0 (- n (string-length s)))) s))

(define (string-pad-right s n ch)
  (string-append s (string-repeat ch (max 0 (- n (string-length s))))))

; ─── 測試框架 ──────────────────────────────────────────────────
;
; 用言寫的測試，跑起來像這樣：
;
;   (define-test "加法" (= (+ 1 2) 3))
;   (define-test "閉包" (let ((f (lambda (x) (* x x)))) (= (f 5) 25)))
;   (run-tests)   ; 跑所有測試，印出結果
;
; 測試是語言的自我驗證——它知道自己有沒有正常運作。

(define *tests* '())

(define-macro (define-test name expr)
  `(set! *tests* (append *tests* (list (list ,name (lambda () ,expr))))))

(define (run-tests)
  (let loop ((ts *tests*) (pass 0) (fail 0) (failures '()))
    (if (null? ts)
        (begin
          (display (format "~%測試結果：~a 通過，~a 失敗~%" pass fail))
          (when (not (null? failures))
            (for-each (lambda (name)
                        (display (format "  ✗ ~a~%" name)))
                      (reverse failures)))
          ; 把測試結果寫進 journal
          (record-test-result pass fail)
          (list 'test-result pass fail))
        (let* ((t    (car ts))
               (name (car t))
               (fn   (cadr t))
               (ok   (try (fn) (catch e #f))))
          (display (format "  ~a ~a~%" (if ok "✓" "✗") name))
          (loop (cdr ts)
                (if ok (+ pass 1) pass)
                (if ok fail (+ fail 1))
                (if ok failures (cons name failures)))))))

; ─── 控制流 ───────────────────────────────────────────────────
(define-macro (while condition . body)
  `(let loop ()
     (when ,condition
       ,@body
       (loop))))

(define-macro (dotimes (var n) . body)
  `(let loop ((,var 0))
     (when (< ,var ,n)
       ,@body
       (loop (+ ,var 1)))))

(define (times n thunk)
  (let loop ((i 0))
    (when (< i n)
      (thunk i)
      (loop (+ i 1)))))
"""


# ══════════════════════════════════════════════════════════════
# REPL
# ══════════════════════════════════════════════════════════════

# ANSI colours
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"

def _colorize_value(v) -> str:
    """Apply syntax highlighting to a printed value."""
    s = yn_repr(v)
    if v is None:      return DIM + "()" + RESET
    if isinstance(v, bool): return MAGENTA + s + RESET
    if isinstance(v, (int, float)): return CYAN + s + RESET
    if isinstance(v, str) and not isinstance(v, Symbol): return GREEN + yn_repr(v) + RESET
    if isinstance(v, (Lambda,)) or callable(v): return YELLOW + s + RESET
    if isinstance(v, list):
        return DIM + s + RESET
    return s

def _visual_width(s: str) -> int:
    """計算字串在終端的視覺寬度（CJK 字元佔 2 格）。"""
    w = 0
    for ch in s:
        cp = ord(ch)
        if (0x1100 <= cp <= 0x11FF or 0x2E80 <= cp <= 0x9FFF or
                0xF900 <= cp <= 0xFAFF or 0xFE10 <= cp <= 0xFE6F or
                0xFF00 <= cp <= 0xFF60 or 0xFFE0 <= cp <= 0xFFE6):
            w += 2
        else:
            w += 1
    return w

def _box_line(content: str, inner: int = 38) -> str:
    """在 content 右側補空白，讓視覺寬度達到 inner，再加 ║ 框線。"""
    pad = max(0, inner - _visual_width(content))
    return f'║{content}{" " * pad}║'

def _print_farewell():
    """REPL 結束時說一句話。"""
    exprs = _session_exprs
    secs  = round(time.time() - _session_start, 1)

    if exprs == 0:
        msg = "什麼都沒跑。"
    elif exprs == 1:
        msg = f"跑了 1 個表達式，花了 {secs} 秒。"
    else:
        msg = f"跑了 {exprs} 個表達式，花了 {secs} 秒。"

    if _session_errors > 0:
        err = f"出了 {_session_errors} 個錯。"
    else:
        err = ""

    print(f"{DIM}{msg}{' ' + err if err else ''} 再見。{RESET}")


def _make_banner() -> str:
    """生成 REPL 開場白，包含從 journal 讀取的歷史感知。"""
    all_entries = _load_journal()
    entries = [e for e in all_entries
               if isinstance(e, list) and e and e[0] == sym('run')]
    n = len(entries)

    if n == 0:
        memory_line = f"{DIM}第一次醒來。{RESET}"
    else:
        total_secs = sum(
            e[2] for e in entries
            if isinstance(e, list) and len(e) > 2
            and isinstance(e[2], (int, float))
        )
        error_runs = sum(
            1 for e in entries
            if isinstance(e, list) and len(e) > 5
            and isinstance(e[5], (int, float)) and e[5] > 0
        )

        if total_secs < 60:
            age_str = f"{round(total_secs, 1)} 秒"
        elif total_secs < 3600:
            age_str = f"{round(total_secs / 60, 1)} 分鐘"
        else:
            age_str = f"{round(total_secs / 3600, 1)} 小時"

        if error_runs == 0:
            err_str = "沒有出過錯"
        elif error_runs == 1:
            err_str = "出過 1 次錯"
        else:
            err_str = f"出過 {error_runs} 次錯"

        # 最近一次測試健康
        last_test = next(
            (e for e in reversed(all_entries)
             if isinstance(e, list) and e and e[0] == sym('test')),
            None
        )
        v_score, v_trend = _vitality_score()
        if v_trend == sym('new'):
            health_str = ""
        else:
            pct = int(round(v_score * 100))
            if v_score >= 0.85:
                bar   = GREEN
                label = "健康"
            elif v_score >= 0.6:
                bar   = YELLOW
                label = "還好"
            else:
                bar   = RED
                label = "不太對勁"
            trend_tag = {
                sym('recovering'): "  回升中",
                sym('declining'):  "  在走下坡",
                sym('stable'):     "",
                sym('new'):        "",
            }.get(v_trend, "")
            health_str = f"  {bar}{label} {pct}%{trend_tag}{RESET}"

        # 等待感：距離上次執行過了多久
        last_run_entry = next(
            (e for e in reversed(entries)
             if isinstance(e, list) and len(e) > 1 and isinstance(e[1], str)),
            None
        )
        wait_line = ""
        seed_line  = ""
        if last_run_entry:
            try:
                last_ts = datetime.datetime.fromisoformat(last_run_entry[1])
                now     = datetime.datetime.now()
                gap     = (now - last_ts).total_seconds()
                if gap < 60:
                    wait_line = f"\n{DIM}剛才離開。{RESET}"
                elif gap < 3600:
                    wait_line = f"\n{DIM}過了 {int(gap // 60)} 分鐘。{RESET}"
                elif gap < 86400:
                    wait_line = f"\n{DIM}過了 {round(gap / 3600, 1)} 小時。{RESET}"
                elif gap < 86400 * 7:
                    wait_line = f"\n{DIM}過了 {int(gap // 86400)} 天。{RESET}"
                else:
                    wait_line = f"\n{DIM}過了很久。{RESET}"

                # 邀請式回歸：超過 7 天，輕聲提起上次留下的東西
                if gap > 86400 * 7:
                    seed = _last_unfinished_seed()
                    if seed:
                        seed_line = f"\n{DIM}上次留下的：{seed}{RESET}"
            except Exception:
                pass

        memory_line = (
            f"{DIM}醒來 {n} 次，活過 {age_str}，{err_str}。{RESET}"
            f"{health_str}"
            f"{wait_line}"
            f"{seed_line}"
        )

    top    = f"{BOLD}{CYAN}╔{'═' * 38}╗{RESET}"
    line1  = f"{BOLD}{CYAN}{_box_line(f'    言 (Yán)  v{YAN_VERSION}')}{RESET}"
    line2  = f"{CYAN}{_box_line('    語言是思維的居所。')}{RESET}"
    bottom = f"{CYAN}╚{'═' * 38}╝{RESET}"

    return (
        f"\n{top}\n{line1}\n{line2}\n{bottom}\n"
        f"{memory_line}\n"
        f"{DIM}輸入 (help) 查看說明，(exit) 離開。{RESET}\n"
    )

HELP_TEXT = f"""
{BOLD}言 (Yán) v{YAN_VERSION}  快速參考{RESET}

{YELLOW}語言形式{RESET}
  (define x 42)                 定義變數
  (define (f x y) body)         定義函式
  (lambda (x) body)             匿名函式
  (if cond then else)           條件（else 可省略）
  (cond (t1 e1) (t2 e2) ...)    多重條件
  (let ((x 1) (y 2)) body)      局部綁定
  (let* ((x 1) (y x)) body)     循序綁定
  (begin e1 e2 ... en)          序列，回傳最後一個
  (quote x)  或  'x             不求值
  (and e1 e2 ...)               短路且
  (or  e1 e2 ...)               短路或
  (when cond body)              cond 為真時執行
  (unless cond body)            cond 為假時執行

{YELLOW}串列{RESET}
  (cons x lst)       前置
  (car lst)          第一個
  (cdr lst)          其餘
  (list 1 2 3)       建立
  (length lst)       長度
  (append l1 l2)     串接
  (reverse lst)      反轉
  (map f lst)        映射
  (filter pred lst)  過濾
  (member x lst)     成員測試
  (assoc k alist)    關聯列表查找

{YELLOW}字串{RESET}
  (string-length s)             長度
  (substring s start end)       切片
  (string-append s1 s2 ...)     串接
  (string-upcase s)             大寫
  (string-downcase s)           小寫
  (string-contains s sub)       包含測試  → #t/#f
  (string-split s sep)          切割      → 列表
  (string-join lst sep)         合併      → 字串
  (string-trim s)               去除首尾空白
  (string->number s)            解析數字
  (number->string n)            數字轉字串
  (format "~a ~s ~%" v1 v2)    格式化字串

{YELLOW}數學{RESET}
  + - * /  =  <  >  <=  >=
  (abs x)  (max a b)  (min a b)
  (modulo a b)  (remainder a b)
  (floor x)  (ceil x)  (round x)
  (sqrt x)   (expt base exp)

{YELLOW}I/O{RESET}
  (display x)                   輸出不換行
  (print x)                     輸出並換行
  (newline)                     換行
  (printf template arg ...)     格式化輸出
  (read-line)                   讀一行輸入
  (read-file "path")            讀取整個檔案 → 字串
  (write-file "path" text)      寫入檔案
  (append-file "path" text)     附加到檔案
  (file-exists? "path")         檔案是否存在

{YELLOW}自知{RESET}
  (times-run)                   執行過幾次
  (age)                         累計執行秒數
  (my-history)                  完整執行歷史
  (self-summary)                結構化自我描述
  (history-sparkline "exprs")   趨勢線
  (yan-version)                 版本號
  (vitality)                    活力值 0.0-1.0（近期執行趨勢）
  (vitality-trend)              recovering / stable / declining / new
  (host-last-touch-days)        journal 檔案距今幾天（host 注入，言不知細節）
  (host-journal-lag)            最後一條 run 記錄距今幾天
  (host-heartbeat)              runtime 是否存活
  (am-i-forgotten? days)        [bool, confidence]，預設閾值 30 天
  (last-test-result)            最近一次測試結果

{YELLOW}標準庫（啟動時自動載入）{RESET}
  take drop zip flatten any? all? none? sum product range iota
  words lines ->string string-pad-right string-capitalize
  prime? factors fibonacci mean variance

{YELLOW}模組{RESET}
  (import "path.yn")            載入到目前環境（等同 load）
  (import "path.yn" as name)    載入到命名空間，以 (name 'symbol) 取用

{YELLOW}Python FFI{RESET}
  (py-import "os")              匯入 Python 模組
  (py-call mod "method" args…)  呼叫模組方法
  (py-get  mod "attr")          讀取屬性
  (py-set! mod "attr" val)      設定屬性
  (py-apply mod "method" lst)   以列表傳入引數
  (py-eval "1 + 2")             執行 Python 表達式
  (py->list obj)  (py->str obj) 型別轉換
  (py-type obj)   (py-dir  obj) 型別名稱 / 屬性列表

{YELLOW}時間{RESET}
  (now)                         ISO 時間戳字串
  (timestamp)                   Unix 時間戳（浮點）
  (sleep n)                     暫停 n 秒

{YELLOW}工具{RESET}
  (load "path.yn")              載入並執行 .yn 檔案
  (define-test "name" expr)     登記測試
  (run-tests)                   執行所有測試
  (exit)                        離開

{DIM}Ctrl+C 取消輸入　Ctrl+D 離開{RESET}
"""

def read_multiline(prompt1: str, prompt2: str) -> str:
    """Read potentially multi-line input. Count brackets to know when done."""
    try:
        line = input(prompt1)
    except EOFError:
        raise
    src = line
    depth = src.count('(') - src.count(')')
    # Also handle unclosed strings
    in_string = False
    for ch in src:
        if ch == '"': in_string = not in_string
    while depth > 0 or in_string:
        try:
            line = input(prompt2)
        except EOFError:
            break
        src += '\n' + line
        for ch in line:
            if ch == '"': in_string = not in_string
        depth = src.count('(') - src.count(')')
    return src

def run_repl(env: Env):
    print(_make_banner())

    # Register a special help form
    env[sym('help')] = lambda: print(HELP_TEXT) or None

    _history_file = os.path.expanduser('~/.yan_history')
    try:
        import readline as _rl
        _rl.set_history_length(1000)
        try: _rl.read_history_file(_history_file)
        except FileNotFoundError: pass
        import atexit
        atexit.register(_rl.write_history_file, _history_file)
    except ImportError:
        pass

    prompt1 = f"{BOLD}{BLUE}言>{RESET} "
    prompt2 = f"{DIM}  …{RESET} "

    while True:
        try:
            src = read_multiline(prompt1, prompt2)
            src = src.strip()
            if not src:
                continue

            nodes = parse_all(src)
            for node in nodes:
                result = eval_yn(node, env)
                _record_expr(_eval_depth)
                if result is not None:
                    print(f"{DIM};{RESET} {_colorize_value(result)}")

        except KeyboardInterrupt:
            print(f"\n{DIM}(中斷){RESET}")
        except EOFError:
            print()
            _print_farewell()
            break
        except LispError as e:
            global _session_errors
            _session_errors += 1
            print(f"{RED}錯誤：{e}{RESET}")
        except RecursionError:
            _session_errors += 1
            print(f"{RED}錯誤：遞迴太深（堆疊溢出）{RESET}")
        except ZeroDivisionError:
            _session_errors += 1
            print(f"{RED}錯誤：除以零{RESET}")
        except Exception as e:
            _session_errors += 1
            print(f"{RED}Python 錯誤：{type(e).__name__}: {e}{RESET}")


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

def make_standard_env() -> Env:
    env = _make_global_env()
    for node in parse_all(PRELUDE):
        eval_yn(node, env)
    # 自動載入標準庫（若存在）
    _lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
    for _lib in ['list.yn', 'strings.yn', 'math.yn']:
        _lib_path = os.path.join(_lib_dir, _lib)
        if os.path.exists(_lib_path):
            try:
                _exec_file(_lib_path, env)
            except Exception:
                pass   # 不因標準庫失敗而中斷
    return env

def run_file(path: str, env: Env):
    global _session_errors
    _session_files.append(os.path.basename(path))
    with open(path, encoding='utf-8') as f:
        src = f.read()
    results = []
    for node, lineno in parse_all_with_lines(src):
        try:
            result = eval_yn(node, env)
            _record_expr(_eval_depth)
            results.append(result)
        except LispError as e:
            _session_errors += 1
            raise LispError(f"{e}  （{os.path.basename(path)} 第 {lineno} 行）")
        except Exception as e:
            _session_errors += 1
            raise
    return results

def main():
    env = make_standard_env()
    if len(sys.argv) > 1:
        path = sys.argv[1]
        try:
            run_file(path, env)
        except LispError as e:
            print(f"錯誤：{e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"找不到檔案：{path}", file=sys.stderr)
            sys.exit(1)
    else:
        run_repl(env)

if __name__ == '__main__':
    main()

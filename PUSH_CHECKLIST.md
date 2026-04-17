# Push Checklist (Minimal)

## 1) Required before pushing

- Ensure these are present: `README.md` (EN), `README.zh.md` (ZH), `SOUL.md`, `LICENSE`
- Ensure excluded files are not tracked: `dream.py`, `ai_chat.py`, `yan/journals/`, `yan/journal.yn`
- Quick smoke test:
  - `python -X utf8 yan/yan.py`
  - run one example: `python -X utf8 yan/yan.py yan/examples/17_memory_behavior.yn`

## 2) GitHub topics (copy/paste)

`lisp`, `interpreter`, `esolang`, `metacircular`, `generative-art`, `creative-coding`, `language-design`, `self-reference`, `procedural-generation`, `python`

## 3) Optional but highly recommended

- Enable GitHub Pages (branch `main`, root `/`)
- Use `index.html` as landing page
- Keep Chinese output text by default; explain it in EN comments/docs

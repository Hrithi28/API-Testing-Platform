"""Render a styled terminal-window screenshot of the pipeline console output,
matching the macOS-chrome aesthetic used throughout the deck/paper figures.
Pure HTML+CSS rendered via Playwright -- no external assets needed.
"""
import re

with open("artifacts/pipeline_console.txt") as f:
    lines = [l.rstrip("\n") for l in f if "Reserved Font" not in l and "is a Reserved" not in l]
# drop matplotlib license preamble lines if any slipped through (keep from the banner onward)
start = 0
for i, l in enumerate(lines):
    if l.startswith("=====") :
        start = i
        break
lines = lines[start:]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

colored = []
for l in lines:
    cls = ""
    if re.match(r"^\[M\d\]", l) or re.match(r"^\[EVAL\]", l) or re.match(r"^\[M6\]", l):
        cls = "tag"
    elif "security" in l and "[P" in l:
        cls = "sec"
    elif l.startswith("====="):
        cls = "rule"
    colored.append((l, cls))

body_html = []
for l, cls in colored:
    if cls == "tag":
        m = re.match(r"^(\[[A-Z0-9]+\])(.*)$", l)
        body_html.append(f'<div class="line"><span class="tag">{esc(m.group(1))}</span>{esc(m.group(2))}</div>')
    elif cls == "sec":
        body_html.append(f'<div class="line sec">{esc(l)}</div>')
    elif cls == "rule":
        body_html.append(f'<div class="line rule">{esc(l)}</div>')
    else:
        body_html.append(f'<div class="line">{esc(l)}</div>')

html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body {{ margin:0; background:#0d1117; font-family: 'SFMono-Regular', Menlo, Consolas, monospace; }}
.window {{ width: 1060px; border-radius: 10px; overflow:hidden; box-shadow: 0 10px 40px rgba(0,0,0,.4); }}
.titlebar {{ background:#2d2d30; height:34px; display:flex; align-items:center; padding:0 14px; gap:8px; }}
.dot {{ width:12px; height:12px; border-radius:50%; }}
.red {{ background:#ff5f56; }} .yellow {{ background:#ffbd2e; }} .green {{ background:#27c93f; }}
.title {{ color:#9aa0a6; font-size:13px; margin-left:10px; }}
.body {{ background:#0d1117; padding:20px 24px 26px; }}
.line {{ color:#d7dbe0; font-size:12.2px; line-height:1.55; white-space:pre-wrap; word-break:break-word; }}
.line.rule {{ color:#2fd38c; }}
.line .tag {{ color:#5aa7ff; font-weight:600; }}
.line.sec {{ color:#e06c75; }}
</style></head><body>
<div class="window">
  <div class="titlebar"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div>
    <div class="title">python3 src/run_pipeline.py</div></div>
  <div class="body">{''.join(body_html)}</div>
</div>
</body></html>"""

with open("artifacts/_terminal.html", "w") as f:
    f.write(html)
print("wrote artifacts/_terminal.html")

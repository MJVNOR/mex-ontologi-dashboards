"""Agrega alt accesible a graficas px con titulo en salud."""

import ast
import re
from pathlib import Path

p = Path("dashboards/hermosillo-salud/app.py")
s = p.read_text(encoding="utf-8")
pat = re.compile(r'title="([^"]+)"\), width="stretch"\)')
n = 0


def repl(m):
    global n
    t = m.group(1)
    n += 1
    return f'title="{t}"), width="stretch", alt="Grafica: {t}")'


s = pat.sub(repl, s)
p.write_text(s, encoding="utf-8")
ast.parse(s)
print("alts agregados:", n)

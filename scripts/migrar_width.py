"""Migra use_container_width (deprecado) a width="stretch" en salud."""

import ast
from pathlib import Path

p = Path("dashboards/hermosillo-salud/app.py")
s = p.read_text(encoding="utf-8")
n = s.count("use_container_width=True")
s = s.replace("use_container_width=True", 'width="stretch"')
p.write_text(s, encoding="utf-8")
ast.parse(s)
print("reemplazos:", n, "| parse ok")

#!/usr/bin/env python3
"""Genera brand.css y aliases.css desde branding/tokens.json y los reparte.

Uso, desde la raíz de core/:
    python3 scripts/build_brand.py            escribe brand.css y aliases.css
    python3 scripts/build_brand.py --sync     además copia lo compartido al sitio
                                              y al panel (la copia no se edita)
    python3 scripts/build_brand.py --check    no escribe: sale con 1 si algo difiere

Solo usa la biblioteca estándar. Las copias son idénticas a los originales
(guía de marca, sección 4.1): el sitio recibe una carpeta branding/ y el
panel un bloque entre marcadores dentro de dashboard.html.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANDING = ROOT / "branding"
SITE_DIR = ROOT.parent / "site" / "site" / "branding"
DASHBOARD = ROOT / "src" / "knowman" / "static" / "dashboard.html"
SHARED = ["brand.css", "aliases.css", "fonts.css", "theme-knowman.css"]
CLOSE = "\n}\n"
DARK_CLOSE = "\n  color-scheme: dark;\n}\n"
LIGHT_CLOSE = "\n  color-scheme: light;\n}\n"
START, END = "/* brand:start (generado por scripts/build_brand.py; no editar) */", "/* brand:end */"
HEADER = "/* knowman · {name} generado desde branding/tokens.json; no editar a mano. */\n"


def resolve(value, palette):
    return re.sub(r"\{([\w-]+)\}", lambda m: palette[m.group(1)], value)


def block(selector, semantic, palette):
    lines = [f"  --color-{key}: {resolve(value, palette)};" for key, value in semantic.items()]
    return f"{selector} {{\n" + "\n".join(lines) + "\n}\n"


def indent(text):
    return "".join("  " + line if line.strip() else line for line in text.splitlines(True))


def build_brand(tokens):
    palette, semantic = tokens["palette"], tokens["semantic"]
    type_, shape = tokens["type"], tokens["shape"]
    out = [HEADER.format(name="brand.css")]
    root = block(":root", semantic["light"], palette).rstrip("\n}")
    type_lines = [
        f"  --type-heading: {type_['heading']};",
        f"  --type-body: {type_['body']};",
        f"  --type-mono: {type_['mono']};",
        f"  --type-weight-heading: {type_['weight-heading']};",
        f"  --type-tracking-heading: {type_['tracking-heading']};",
    ]
    root += "\n" + "\n".join(type_lines) + "\n"
    root += "".join(f"  --shape-{key}: {value};\n" for key, value in shape.items())
    root += "  color-scheme: light;\n}\n"
    out.append(root)
    dark = semantic["dark"]
    dark_rule = block('[data-theme="dark"]', dark, palette)
    out.append("\n" + dark_rule.replace(CLOSE, DARK_CLOSE))
    media = block(':root:not([data-theme="light"])', dark, palette)
    media = media.replace(CLOSE, DARK_CLOSE)
    out.append("\n@media (prefers-color-scheme: dark) {\n" + indent(media) + "}\n")
    # El papel siempre va en claro (guía de marca, sección 3.6).
    light = block(':root, :root:not([data-theme="light"])', semantic["light"], palette)
    light = light.replace(CLOSE, LIGHT_CLOSE)
    out.append("\n@media print {\n" + indent(light) + "}\n")
    return "".join(out)


def build_aliases(tokens):
    aliases = tokens["aliases"]
    lines = [
        f"  {name}: var(--{target});"
        for name, target in aliases.items()
        if not name.startswith("$")
    ]
    return HEADER.format(name="aliases.css") + ":root {\n" + "\n".join(lines) + "\n}\n"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_files(base):
    return sorted(p.relative_to(base) for p in base.rglob("*") if p.is_file())


def sync_site(write):
    problems = []
    for name in SHARED:
        problems += copy_file(BRANDING / name, SITE_DIR / name, write)
    fonts = BRANDING / "fonts"
    for rel in tree_files(fonts):
        problems += copy_file(fonts / rel, SITE_DIR / "fonts" / rel, write)
    return problems


def copy_file(source, target, write):
    if target.exists() and digest(source) == digest(target):
        return []
    if not write:
        return [f"{target} no coincide con {source}"]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return []


def inline_block():
    parts = [(BRANDING / "brand.css").read_text(), (BRANDING / "aliases.css").read_text()]
    return START + "\n" + "\n".join(parts) + END


def sync_dashboard(write):
    text = DASHBOARD.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        return [f"{DASHBOARD} no tiene los marcadores brand:start y brand:end"]
    new = pattern.sub(lambda _: inline_block(), text)
    if new == text:
        return []
    if not write:
        return [f"{DASHBOARD} no coincide con branding/"]
    DASHBOARD.write_text(new)
    return []


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sync", action="store_true", help="copia al sitio y al panel")
    parser.add_argument("--check", action="store_true", help="no escribe; falla si algo difiere")
    args = parser.parse_args()
    tokens = json.loads((BRANDING / "tokens.json").read_text())
    generated = {"brand.css": build_brand(tokens), "aliases.css": build_aliases(tokens)}
    problems = []
    for name, content in generated.items():
        path = BRANDING / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                problems.append(f"{path} no coincide con tokens.json")
        else:
            path.write_text(content)
    write = args.sync and not args.check
    if args.sync or args.check:
        problems += sync_site(write)
        problems += sync_dashboard(write)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print("Marca al día." if args.check else "Marca generada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

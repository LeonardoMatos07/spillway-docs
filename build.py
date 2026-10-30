"""Builds the documentation: src/*.md -> dist/spillway-docs.html (+ PDF with --pdf).

    uv run --with markdown-it-py python build.py          # HTML only
    uv run --with markdown-it-py python build.py --pdf    # HTML and PDF (needs Chrome or Edge)

Diagrams are Mermaid blocks (```mermaid); the HTML loads assets/mermaid.min.js, so it works offline.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
TITLE = "Spillway, Relay e Forecast"
SUBTITLE = "Documentação geral para o dono do projeto"
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

md = MarkdownIt("commonmark", {"html": True}).enable("table")
_default_fence = md.renderer.rules["fence"]  # type: ignore[attr-defined]


def fence(tokens, idx, options, env):  # type: ignore[no-untyped-def]
    token = tokens[idx]
    if token.info.strip() == "mermaid":
        return f'<figure class="diagram"><pre class="mermaid">{html.escape(token.content)}</pre></figure>\n'
    return _default_fence(tokens, idx, options, env)


md.renderer.rules["fence"] = fence  # type: ignore[attr-defined]

CALLOUTS = {
    "Por quê?": "why",
    "Decisão:": "why",
    "Atenção:": "warn",
    "Dica:": "tip",
    "Em resumo:": "sum",
    "Honestidade:": "warn",
}


def slug(text: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower().encode("ascii", "ignore").decode()).strip("-")
    base = base or "secao"
    candidate, n = base, 2
    while candidate in used:
        candidate, n = f"{base}-{n}", n + 1
    used.add(candidate)
    return candidate


def render() -> tuple[str, list[tuple[int, str, str]]]:
    used: set[str] = set()
    toc: list[tuple[int, str, str]] = []
    chapters: list[str] = []
    for path in sorted(SRC.glob("*.md")):
        body = md.render(path.read_text(encoding="utf-8"))

        def heading(match: re.Match[str]) -> str:
            level, inner = int(match.group(1)), match.group(2)
            ident = slug(inner, used)
            if level <= 2:
                toc.append((level, ident, re.sub(r"<[^>]+>", "", inner)))
            return f'<h{level} id="{ident}">{inner}</h{level}>'

        body = re.sub(r"<h([1-3])>(.*?)</h\1>", heading, body, flags=re.S)
        for lead, cls in CALLOUTS.items():
            body = body.replace(f"<blockquote>\n<p><strong>{lead}", f'<blockquote class="{cls}">\n<p><strong>{lead}')
        chapters.append(f'<section class="chapter">{body}</section>')
    return "\n".join(chapters), toc


def toc_html(toc: list[tuple[int, str, str]]) -> str:
    items = []
    for level, ident, text in toc:
        items.append(f'<li class="l{level}"><a href="#{ident}">{html.escape(text)}</a></li>')
    return '<nav class="toc"><h2 class="toc-title">Sumário</h2><ul>' + "".join(items) + "</ul></nav>"


CSS = """
@page { size: A4; margin: 18mm 15mm 18mm 15mm; @bottom-center { content: counter(page); font: 9pt 'Segoe UI', sans-serif; color: #52667a; } }
:root { --ink:#0e1b2c; --ink2:#34495e; --muted:#52667a; --accent:#0f766e; --soft:#e9f1ef; --line:#c5d5d1; --amber:#b45309; --amber-soft:#fef3c7; --blue:#1d4ed8; --blue-soft:#dbeafe; }
* { box-sizing: border-box; }
html { font-family: 'Segoe UI', system-ui, -apple-system, Arial, sans-serif; color: var(--ink); font-size: 11pt; line-height: 1.55; }
body { margin: 0 auto; max-width: 960px; padding: 0 24px; }
.cover { min-height: 92vh; display: flex; flex-direction: column; justify-content: center; border-left: 10px solid var(--accent); padding-left: 28px; page-break-after: always; break-after: page; }
.cover .kicker { color: var(--accent); font-weight: 700; letter-spacing: .14em; text-transform: uppercase; font-size: 10pt; }
.cover h1 { font-size: 34pt; line-height: 1.1; margin: .2em 0 .1em; border: 0; }
.cover p { color: var(--ink2); font-size: 13pt; margin: .2em 0; }
.cover .meta { margin-top: 2.4em; font-size: 10pt; color: var(--muted); }
.toc { page-break-after: always; break-after: page; }
.toc ul { list-style: none; padding: 0; margin: 0; }
.toc li.l1 { margin-top: .9em; font-weight: 700; font-size: 11.5pt; }
.toc li.l2 { margin-left: 1.4em; font-size: 10pt; color: var(--ink2); }
.toc a { color: inherit; text-decoration: none; }
.toc-title { border: 0; }
.chapter { page-break-before: always; break-before: page; }
h1 { font-size: 24pt; line-height: 1.15; margin: 0 0 .6em; padding-bottom: .25em; border-bottom: 3px solid var(--accent); }
h2 { font-size: 16pt; margin: 1.6em 0 .5em; color: var(--ink); break-after: avoid; }
h3 { font-size: 12.5pt; margin: 1.3em 0 .4em; color: var(--accent); break-after: avoid; }
p { margin: .55em 0; }
ul, ol { padding-left: 1.4em; margin: .5em 0; }
li { margin: .2em 0; }
a { color: var(--accent); }
code { font-family: Consolas, 'Courier New', monospace; font-size: 9.2pt; background: var(--soft); padding: .1em .35em; border-radius: 4px; }
pre { background: #0e1b2c; color: #e8f0f4; padding: 10px 12px; border-radius: 8px; overflow-x: auto; font-size: 8.8pt; line-height: 1.45; break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; margin: .8em 0; font-size: 9.6pt; break-inside: auto; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: #0e1b2c; color: #fff; text-align: left; padding: 6px 8px; }
td { padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
tr:nth-child(even) td { background: #f6faf9; }
blockquote { margin: 1em 0; padding: .6em 1em; border-left: 5px solid var(--accent); background: var(--soft); border-radius: 0 8px 8px 0; break-inside: avoid; }
blockquote p { margin: .3em 0; }
blockquote.why { border-color: var(--accent); background: var(--soft); }
blockquote.warn { border-color: var(--amber); background: var(--amber-soft); }
blockquote.tip { border-color: var(--blue); background: var(--blue-soft); }
blockquote.sum { border-color: #0e1b2c; background: #eef2f7; }
figure.diagram { margin: 1em 0; padding: 10px; border: 1px solid var(--line); border-radius: 10px; background: #fff; break-inside: avoid; text-align: center; }
figure.diagram svg { max-width: 100%; height: auto; }
.mermaid { background: none !important; color: inherit !important; font-size: 10pt; white-space: pre; }
.mermaid[data-processed] { white-space: normal; }
hr { border: 0; border-top: 1px solid var(--line); margin: 1.5em 0; }
@media print { body { max-width: none; padding: 0; } a { color: inherit; text-decoration: none; } }
"""

JS = """
<script src="../assets/mermaid.min.js"></script>
<script>
mermaid.initialize({
  startOnLoad: true, securityLevel: 'loose', theme: 'base',
  themeVariables: { primaryColor: '#e9f1ef', primaryBorderColor: '#0f766e', primaryTextColor: '#0e1b2c',
    lineColor: '#34495e', secondaryColor: '#dbeafe', tertiaryColor: '#fef3c7', fontFamily: 'Segoe UI, Arial, sans-serif', fontSize: '13px' },
  flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },
  sequence: { useMaxWidth: true, wrap: true, mirrorActors: false, messageFontSize: 12 },
});
</script>
"""


def build() -> Path:
    DIST.mkdir(exist_ok=True)
    chapters, toc = render()
    today = date.today().strftime("%d/%m/%Y")
    cover = (
        '<header class="cover"><div class="kicker">Documentação do projeto</div>'
        f"<h1>{TITLE}</h1><p>{SUBTITLE}</p>"
        "<p>Arquitetura, serviços, fluxos e as decisões por trás de cada escolha.</p>"
        f'<div class="meta">Versão de {today} · Leonardo Matos</div></header>'
    )
    page = (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{TITLE}</title><style>{CSS}</style></head><body>"
        f"{cover}{toc_html(toc)}{chapters}{JS}</body></html>"
    )
    out = DIST / "spillway-docs.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page) // 1024} KB, {len(toc)} sections)")
    return out


def pdf(source: Path) -> None:
    browser = next((b for b in BROWSERS if Path(b).exists()), None)
    if browser is None:
        sys.exit("no Chrome or Edge found; open the HTML and use Print > Save as PDF")
    target = DIST / "spillway-docs.pdf"
    subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--allow-file-access-from-files",
            "--virtual-time-budget=60000",
            f"--print-to-pdf={target}",
            source.resolve().as_uri(),
        ],
        check=True,
        timeout=300,
    )
    print(f"wrote {target} ({target.stat().st_size // 1024} KB)")


def check_diagrams(source: Path) -> None:
    """Renders the page in the browser and reports any diagram Mermaid could not draw."""
    browser = next((b for b in BROWSERS if Path(b).exists()), None)
    if browser is None:
        return
    result = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
         "--virtual-time-budget=60000", "--dump-dom", source.resolve().as_uri()],
        capture_output=True, timeout=300, check=True,
    )
    dom = result.stdout.decode("utf-8", errors="replace")
    total = dom.count('class="mermaid"') + dom.count("data-processed")
    failed = len(re.findall(r"Syntax error in text|mermaid version", dom))
    drawn = len(re.findall(r"<svg[^>]*id=\"mermaid-", dom))
    print(f"diagrams drawn: {drawn}; syntax errors: {failed}")
    for match in re.finditer(r"Syntax error in text", dom):
        print("  syntax error near:", re.sub(r"<[^>]+>", " ", dom[max(0, match.start() - 300): match.start()])[-160:])
    del total


if __name__ == "__main__":
    html_path = build()
    if "--check" in sys.argv:
        check_diagrams(html_path)
    if "--pdf" in sys.argv:
        pdf(html_path)

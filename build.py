#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador estático del portfolio del módulo "Puesta en Producción Segura".

Lee los documentos de  ../prod_segura_ejercicios/  (fuente, NO se modifica) y genera:
  - index.html                              portada con tarjetas por ejercicio
  - ejercicios/ejercicio-XX.html            una página por ejercicio (documento completo)
  - assets/img/ejercicio-XX/                imágenes extraídas de los docx
  - assets/audio/                           recurso de audio (.m4a)

Todo el HTML se genera a partir de una ÚNICA plantilla (PAGE_TEMPLATE) para no
duplicar lógica (head, sidebar, footer, menú) en cada página.

Dependencias en tiempo de ejecución del sitio: NINGUNA. HTML + CSS + JS vanilla.
"""

from __future__ import annotations

import html as ihtml
import os
import re
import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table

# -----------------------------------------------------------------------------
# Rutas
# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent          # portfolio_puesta_prod_segura/
SRC = ROOT.parent / "prod_segura_ejercicios"    # fuente de contenido
DST = ROOT
EJ_DIR = DST / "ejercicios"
ASSETS_IMG = DST / "assets" / "img"
ASSETS_AUDIO = DST / "assets" / "audio"

CSS_NAME = "assets/css/style.css"
JS_NAME = "assets/js/app.js"

# -----------------------------------------------------------------------------
# Ejercicios en el orden lógico indicado por el docente:
# 5.1.1 → 5.1.2 → 5.1.3 → reto colaborativo → owasp → asvs → video → docker
# -----------------------------------------------------------------------------
EXERCISES = [
    ("Ariketa_5.1.1.docx",                  "ejercicio-01"),
    ("Ariketa_5.1.2_v2.docx",               "ejercicio-02"),
    ("Ariketa_5.1.3.docx",                  "ejercicio-03"),
    ("Github-Reto colaborativo.docx",       "ejercicio-04"),
    ("Tarea 1 - OWASP10 - Omar Akhamlich.docx", "ejercicio-05"),
    ("asvs-ejercicio_Omar_Akhamlich.docx",  "ejercicio-06"),
    ("Protege_tu_código_de_dependencias_vulnerables.m4a", "ejercicio-07"),
    ("Docker1.docx",                        "ejercicio-08"),
]

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

MONO_FONTS = {
    "Consolas", "Courier New", "Courier", "Roboto Mono", "Lucida Console",
    "Lucida Sans Typewriter", "monospace",
}

# -----------------------------------------------------------------------------
# Sanitización de datos sensibles (no secretos, IPs reales ni datos de terceros)
# -----------------------------------------------------------------------------
SANITIZE = [
    (re.compile(r"(?i)\badmin123\b"), "[CONTRASEÑA_EJEMPLO]"),
    (re.compile(r"(?i)\b(api_token|access_token|token|clave|contraseña|password|pwd|secret)\s*[:=]\s*\S+"),
     lambda m: m.group(1) + "=[VALOR_OCULTO]"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "[IP_EJEMPLO]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL_OCULTO]"),
    (re.compile(r"Jon\s+Nieto"), "[ALUMNO A]"),
]

def sanitize(text: str) -> str:
    for rx, repl in SANITIZE:
        text = rx.sub(repl, text)
    return text


# -----------------------------------------------------------------------------
# Utilidades de escape
# -----------------------------------------------------------------------------
def esc_text(text: str) -> str:
    return ihtml.escape(text, quote=False)


def esc_attr(text: str) -> str:
    return ihtml.escape(text, quote=True)


# -----------------------------------------------------------------------------
# Detección de bloques de código (fuente monoespaciada en todo el párrafo)
# -----------------------------------------------------------------------------
def guess_lang(text: str):
    """Heurística ligera para elegir el lenguaje del resaltado."""
    t = text.strip()
    if not t:
        return None
    if t.lstrip().startswith(("{", "[")):
        return "json"
    low = t.lower()
    if re.search(r"\b(FROM|WORKDIR|COPY|RUN|CMD|EXPOSE|ENTRYPOINT|ENV|ARG|VOLUME|LABEL|HEALTHCHECK|docker\b|docker-compose)\b", t):
        return "dockerfile"
    if re.search(r"\b(def |class |import |from |session\.get|render_template|@app\.route|True|False|None)\b", t):
        return "python"
    if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|FROM|WHERE|JOIN)\b", t):
        return "sql"
    if re.search(r"<[a-zA-Z][^>]*>", t):
        return "html"
    if re.search(r"\b(git\b|docker\b|cd |ls |rm |mkdir|cp |mv |chmod|chown|sudo|apt|apt-get|echo|export|cat |ssh |git stash|git revert|git commit)\b", low):
        return "bash"
    if re.search(r"^\s*[a-z_][a-z_0-9]*\s*:", t, re.M) and "\n" in t:
        return "yaml"
    return None

KW = {
    "python": ["def", "class", "import", "from", "as", "return", "if", "elif", "else",
               "try", "except", "finally", "with", "for", "while", "in", "is", "not",
               "and", "or", "True", "False", "None", "self", "cls", "lambda", "yield",
               "async", "await", "break", "continue", "raise", "pass", "global", "del", "assert"],
    "bash": ["git", "docker", "cd", "ls", "rm", "mkdir", "cp", "mv", "chmod", "chown",
             "sudo", "apt", "apt-get", "echo", "cat", "export", "source", "ssh", "scp",
             "service", "systemctl", "grep", "find", "sed", "awk", "touch"],
    "dockerfile": ["FROM", "WORKDIR", "COPY", "RUN", "CMD", "EXPOSE", "ENTRYPOINT",
                   "ENV", "ARG", "VOLUME", "LABEL", "HEALTHCHECK", "ONBUILD", "MAINTAINER"],
    "sql": ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "FROM", "WHERE",
            "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AND", "OR", "NOT", "IN",
            "LIKE", "IS", "NULL", "INTO", "VALUES", "SET", "ORDER", "GROUP", "BY",
            "HAVING", "AS", "DATABASE", "INDEX"],
}


def highlight_code(text: str, lang: str) -> str:
    """Resaltado sintáctico estático (lado servidor) sobre texto YA escapado."""
    if lang in ("python", "bash", "dockerfile", "sql", "yaml"):
        text = re.sub(r"(?m)^[ \t]*#.*$",
                      lambda m: f'<span class="hl-cmt">{m.group(0)}</span>', text)
    text = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'',
                  lambda m: f'<span class="hl-str">{m.group(0)}</span>', text)
    if lang == "html":
        text = re.sub(r'&lt;(\/?[a-zA-Z][a-zA-Z0-9]*)\b',
                      r'<span class="hl-tag">&lt;\1</span>', text)
    kws = KW.get(lang, [])
    if kws:
        flags = re.I if lang in ("dockerfile", "sql", "bash") else 0
        pat = r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b"
        token_re = re.compile(
            r'<span class="hl-(?:cmt|str|tag)">.*?</span>|' + pat, flags)
        text = token_re.sub(
            lambda m: m.group(0) if m.group(0).startswith("<span")
            else f'<span class="hl-kw">{m.group(0)}</span>', text)
    return text


# -----------------------------------------------------------------------------
# Extracción de contenido de un docx
# -----------------------------------------------------------------------------
class Ctx:
    def __init__(self, doc, ej_num, img_dir, img_base):
        self.doc = doc
        self.ej_num = ej_num
        self.img_dir = img_dir
        self.img_base = img_base
        self.img_idx = 0
        self.rel_cache = {}  # rId -> ruta relativa de la imagen
        img_dir.mkdir(parents=True, exist_ok=True)

    def image_for(self, r_id: str) -> str | None:
        if r_id in self.rel_cache:
            return self.rel_cache[r_id]
        part = self.doc.part.related_parts.get(r_id)
        if part is None or not hasattr(part, "blob"):
            return None
        ctype = getattr(part, "content_type", "") or ""
        ext = ".png"
        if "jpeg" in ctype:
            ext = ".jpg"
        elif "gif" in ctype:
            ext = ".gif"
        elif "svg" in ctype:
            ext = ".svg"
        self.img_idx += 1
        name = f"ej-{self.ej_num:02d}-{self.img_idx:02d}{ext}"
        path = self.img_dir / name
        path.write_bytes(part.blob)
        rel = f"{self.img_base}{name}"
        self.rel_cache[r_id] = rel
        return rel


def q(tag_ns: str) -> str:
    return f"{{{tag_ns}}}"


def run_props(r_elem):
    bold = italic = False
    font = None
    rPr = r_elem.find(q(W) + "rPr")
    if rPr is not None:
        b = rPr.find(q(W) + "b")
        if b is not None and b.get(q(W) + "val") in (None, "true", "1"):
            bold = True
        i = rPr.find(q(W) + "i")
        if i is not None and i.get(q(W) + "val") in (None, "true", "1"):
            italic = True
        rf = rPr.find(q(W) + "rFonts")
        if rf is not None:
            font = rf.get(q(W) + "ascii") or rf.get(q(W) + "hAnsi") or rf.get(q(W) + "cs")
    return bold, italic, font


def run_inline_html(r_elem, ctx) -> str:
    bold, italic, font = run_props(r_elem)
    raw = r_elem.text or ""
    if not raw:
        return ""
    raw = sanitize(raw)
    mono = bool(font and font in MONO_FONTS)
    html = esc_text(raw)
    if mono:
        html = f"<code>{html}</code>"
    if bold:
        html = f"<strong>{html}</strong>"
    if italic:
        html = f"<em>{html}</em>"
    return html


def drawing_url_for(elem, ctx):
    """Busca un a:blip con r:embed dentro de elem y devuelve la URL de la imagen."""
    for blip in elem.findall(".//" + q(A) + "blip"):
        rel = blip.get(q(R) + "embed")
        if rel:
            return ctx.image_for(rel)
    return None


def paragraph_html(p_elem, ctx):
    style_el = p_elem.find(q(W) + "pStyle")
    style = style_el.get(q(W) + "val") if style_el is not None else "Normal"

    infos = []
    for child in p_elem:
        tag = child.tag
        if tag == q(W) + "r":
            html = run_inline_html(child, ctx)
            raw = sanitize(child.text or "")
            infos.append(("RUN", html, raw))
            # Las imágenes embebidas van anidadas en w:r > w:drawing > a:blip
            url = drawing_url_for(child, ctx)
            if url:
                infos.append(("IMG", url, ""))
        elif tag == q(W) + "br":
            infos.append(("BR", "<br>", ""))
        elif tag == q(W) + "drawing":
            url = drawing_url_for(child, ctx)
            if url:
                infos.append(("IMG", url, ""))
        elif tag == q(W) + "pict":
            url = drawing_url_for(child, ctx)
            if url:
                infos.append(("IMG", url, ""))

    text_runs = []
    for child in p_elem:
        if child.tag == q(W) + "r":
            _, _, f = run_props(child)
            text_runs.append((child.text or "", f))
    text_runs = [(t, f) for t, f in text_runs if t.strip()]
    all_mono = bool(text_runs) and all(f in MONO_FONTS for _, f in text_runs)

    inner_parts = []
    raw_text_chunks = []
    for kind, html, raw in infos:
        if kind == "RUN":
            raw_text_chunks.append(raw)
            if all_mono:
                inner_parts.append(esc_text(raw))
            else:
                inner_parts.append(html)
        elif kind == "BR":
            inner_parts.append("<br>")
        elif kind == "IMG":
            inner_parts.append(
                f'<img src="{esc_attr(html)}" alt="Imagen del ejercicio" loading="lazy">'
            )

    inner = "".join(inner_parts)
    if not inner.strip():
        return ""

    if style == "Title":
        tag = "h2"
    elif style == "Heading 1":
        tag = "h2"
    elif style == "Heading 2":
        tag = "h3"
    elif style == "Heading 3":
        tag = "h4"
    else:
        tag = "p"

    raw_text = "".join(raw_text_chunks)
    if all_mono and tag == "p":
        lang = guess_lang(raw_text)
        highlighted = highlight_code(inner, lang) if lang else inner
        lang_attr = f' data-lang="{lang}"' if lang else ""
        return (
            '<figure class="code-block">'
            '<button type="button" class="copy-btn" data-copy>Copiar</button>'
            f"<pre><code{lang_attr}>{highlighted}</code></pre>"
            "</figure>"
        )
    return f"<{tag}>{inner}</{tag}>"


def cell_is_bold(cell) -> bool:
    for p in cell.paragraphs:
        for r in p.runs:
            if r.font.bold:
                return True
    return False


def cell_images(cell, ctx) -> str:
    """Devuelve las  de las imágenes embebidas en una celda de tabla."""
    out = []
    tc = cell._tc
    for drawing in tc.findall(".//" + q(W) + "drawing"):
        url = drawing_url_for(drawing, ctx)
        if url:
            out.append(
                f'<div class="cell-img"><img src="{esc_attr(url)}" '
                'alt="Captura de la tabla" loading="lazy"></div>'
            )
    return "\n".join(out)


def table_html(tbl_elem, doc, ctx) -> str:
    table = Table(tbl_elem, doc)
    rows_html = []
    for i, row in enumerate(table.rows):
        cells_html = []
        header = (i == 0) and any(cell_is_bold(c) for c in row.cells)
        tag = "th" if header else "td"
        for cell in row.cells:
            text = (cell.text or "").strip()
            text = sanitize(text)
            parts = [esc_text(part) for part in text.split("\n") if part != ""]
            inner = "<br>".join(parts) if parts else ""
            imgs = cell_images(cell, ctx)
            cells_html.append(f"<{tag}>{inner}{imgs}</{tag}>")
        rows_html.append("<tr>" + "".join(cells_html) + "</tr>")
    return '<table class="doc-table"><tbody>' + "".join(rows_html) + "</tbody></table>"


def iter_body_blocks(doc):
    for child in doc.element.body.iterchildren():
        tag = child.tag
        if tag == q(W) + "p":
            yield ("p", child)
        elif tag == q(W) + "tbl":
            yield ("tbl", child)


def extract_document(doc, ej_num, img_dir, img_base):
    ctx = Ctx(doc, ej_num, img_dir, img_base)
    blocks = []
    title = None
    summary = None
    for kind, obj in iter_body_blocks(doc):
        if kind == "p":
            html = paragraph_html(obj, ctx)
            if not html:
                continue
            style_el = obj.find(q(W) + "pStyle")
            style = style_el.get(q(W) + "val") if style_el is not None else "Normal"
            text = ihtml.unescape(re.sub(r"<[^>]+>", " ", html))
            text = " ".join(text.split())
            if title is None and style == "Title" and text:
                title = text
            if summary is None and style in ("Normal", "Title") and len(text) > 40:
                summary = text[:220] + ("…" if len(text) > 220 else "")
            blocks.append(html)
        else:
            blocks.append(table_html(obj, doc, ctx))

    if title is None:
        title = f"Ejercicio {ej_num:02d}"
    return title, "\n".join(blocks), summary or ""


# -----------------------------------------------------------------------------
# Plantilla HTML única
# -----------------------------------------------------------------------------
TITLES: dict[str, str] = {}

# Títulos descriptivos reales de cada documento (fallback si el estilo "Title"
# del docx no se captura automáticamente).
TITLES_MANUAL = {
    "ejercicio-01": "GIT Ariketa 5.1.1",
    "ejercicio-02": "GIT Ariketa 5.1.2",
    "ejercicio-03": "GIT Ariketa 5.1.3",
    "ejercicio-04": "GIT Ariketa 5.1.4 · Reto colaborativo",
    "ejercicio-05": "OWASP Top 10 · Tarea 1 (Sesión 1)",
    "ejercicio-06": "ASVS de OWASP · Aplicación a una aplicación web",
    "ejercicio-07": "Recurso de audio · Protege tu código de dependencias vulnerables",
    "ejercicio-08": "Práctica Docker 1 · Nginx e imagen Node.js",
}

def menu_html(active_key: str, base: str) -> str:
    items = []
    for (_, key), (src_file, _) in zip(EXERCISES, EXERCISES):
        title = TITLES.get(key, key)
        cls = ' class="active"' if key == active_key else ""
        items.append(
            f'<li><a href="{base}{key}.html" data-ex="{key}"{cls}>{esc_attr(title)}</a></li>'
        )
    return "<ul>" + "".join(items) + "</ul>"


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="es" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; media-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'none';">
<meta name="referrer" content="no-referrer">
<title>{title}</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<a class="skip-link" href="#contenido">Saltar al contenido</a>

<div class="wrapper">
<aside class="sidebar" id="sidebar">
  <div class="sidebar-wrap">
    <button class="menu-toggle" id="menu-toggle" aria-expanded="false"
            aria-controls="menu-list" aria-label="Abrir menú de ejercicios">☰</button>
    <div class="brand">
      <a href="{index_href}">Portfolio</a>
      <div class="brand-sub">Puesta en Producción Segura · Omar Akhamlich Cotado</div>
    </div>
    <nav id="menu-list">{menu}</nav>
    <div class="theme-wrap">
      <button class="theme-toggle" id="theme-toggle" aria-pressed="false"
              aria-label="Cambiar entre tema claro y oscuro">🌓</button>
    </div>
  </div>
</aside>

<main id="contenido" tabindex="-1">
  {header}
  {body}
  {prevnext}
</main>
</div>

<footer class="site-footer">
  <p>Sitio 100 % estático generado con <code>build.py</code>. HTML, CSS y JS vanilla,
  sin dependencias externas ni CDNs.</p>
</footer>

<script src="{js}"></script>
</body>
</html>"""


def exercise_header(ej_num: int, key: str, src_file: str) -> str:
    return (
        '<header class="exercise-header">'
        f'<div class="ej-meta"><span class="badge">Ejercicio {ej_num:02d}</span>'
        f'<span class="source">Fuente: {esc_attr(src_file)}</span></div>'
        f"<h1>{esc_attr(TITLES[key])}</h1>"
        '<p class="lead">Contenido completo del documento original del ejercicio.</p>'
        "</header>"
    )


def prev_next(idx: int, base: str) -> str:
    links = []
    if idx > 0:
        p_key = EXERCISES[idx - 1][1]
        links.append(
            f'<a href="{base}{p_key}.html" class="nav-link nav-prev">← Anterior: '
            f'{esc_attr(TITLES[p_key])}</a>'
        )
    else:
        links.append('<span class="nav-link nav-prev disabled">Anterior: —</span>')
    links.append('<span class="nav-sep">·</span>')
    if idx < len(EXERCISES) - 1:
        n_key = EXERCISES[idx + 1][1]
        links.append(
            f'<a href="{base}{n_key}.html" class="nav-link nav-next">Siguiente: '
            f'{esc_attr(TITLES[n_key])} →</a>'
        )
    else:
        links.append('<span class="nav-link nav-next disabled">Siguiente: —</span>')
    return '<nav class="nav-prev-next" aria-label="Navegación entre ejercicios">' + "".join(links) + "</nav>"


# -----------------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------------
def main() -> None:
    global TITLES

    for d in (EJ_DIR, ASSETS_IMG, ASSETS_AUDIO):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    (DST / "assets" / "css").mkdir(parents=True, exist_ok=True)
    (DST / "assets" / "js").mkdir(parents=True, exist_ok=True)

    # Copiar archivo de audio si existe
    audio_src = SRC / "Protege_tu_código_de_dependencias_vulnerables.m4a"
    if audio_src.exists():
        shutil.copy2(audio_src, ASSETS_AUDIO / audio_src.name)

    exercised_data = []
    for idx, (src_file, key) in enumerate(EXERCISES, start=1):
        if src_file.lower().endswith(".m4a"):
            # Archivo de audio: página con reproductor, sin documento de texto.
            title = TITLES_MANUAL.get(key, f"Ejercicio {idx:02d} · Recurso de audio")
            summary = "Recurso complementario: Protege tu código de dependencias vulnerables."
            body = (
                '<section class="recurso-audio">'
                "<h2>Recurso complementario</h2>"
                '<p>Audio del curso: “Protege tu código de dependencias vulnerables” '
                "(recurso complementario, no transcrito).</p>"
                f'<audio controls preload="none" src="../assets/audio/{os.path.basename(src_file)}"></audio>'
                "</section>"
            )
            src_rel = f"../assets/audio/{os.path.basename(src_file)}"
        else:
            doc = Document(SRC / src_file)
            img_dir = ASSETS_IMG / key
            title, body, summary = extract_document(doc, idx, img_dir, f"../assets/img/{key}/")
            src_rel = src_file

        if title == f"Ejercicio {idx:02d}":
            title = TITLES_MANUAL.get(key, title)
        TITLES[key] = title
        exercised_data.append({
            "key": key, "num": idx, "title": title, "src": src_file,
            "body": body, "summary": summary,
        })

    css_rel_index = CSS_NAME
    js_rel_index = JS_NAME
    css_rel_ej = "../" + CSS_NAME
    js_rel_ej = "../" + JS_NAME

    # ---------- Portada ----------
    cards = []
    for ed in exercised_data:
        cards.append(
            '<article class="card">'
            f'<h3><a href="ejercicios/{ed["key"]}.html">{esc_attr(ed["title"])}</a></h3>'
            f'<p class="card-sum">{esc_text(ed["summary"])}</p>'
            f'<a class="card-link" href="ejercicios/{ed["key"]}.html">Ver ejercicio {ed["num"]:02d} →</a>'
            "</article>"
        )
    intro = (
        "<p>Portfolio estático del módulo <strong>Puesta en Producción Segura</strong>. "
        "Aquí se recogen los ejercicios realizados: flujo seguro con Git y GitHub "
        "(ramas, Pull Requests, revisión de código, resolución de conflictos, secretos), "
        "contenedores con Docker (Nginx y Node.js), OWASP Top 10 y aplicación del estándar "
        "ASVS de OWASP como lista de verificación de auditoría.</p>"
        "<p>Cada ejercicio tiene su propia página con el contenido íntegro de su documento "
        "original: texto, tablas, capturas de pantalla y bloques de código.</p>"
    )
    index_html = PAGE_TEMPLATE.format(
        title="Portfolio · Puesta en Producción Segura",
        css=css_rel_index,
        js=js_rel_index,
        index_href="index.html",
        menu=menu_html("portada", "ejercicios/"),
        header=(
            '<header class="exercise-header">'
            "<h1>Portfolio · Puesta en Producción Segura</h1>"
            '<p class="lead">Omar Akhamlich Cotado — ejercicios del módulo de despliegue y producción segura.</p>'
            "</header>"
        ),
        body=intro + '<div class="cards-grid">' + "".join(cards) + "</div>",
        prevnext="",
    )
    (DST / "index.html").write_text(index_html, encoding="utf-8")

    # ---------- Páginas de ejercicios ----------
    for idx, ed in enumerate(exercised_data):
        key = ed["key"]
        prevnext = prev_next(idx, "")
        page_html = PAGE_TEMPLATE.format(
            title=f"{TITLES[key]} — Portfolio · Puesta en Producción Segura",
            css=css_rel_ej,
            js=js_rel_ej,
            index_href="../index.html",
            menu=menu_html(key, ""),
            header=exercise_header(ed["num"], key, ed["src"]),
            body=ed["body"],
            prevnext=prevnext,
        )
        (EJ_DIR / f"{key}.html").write_text(page_html, encoding="utf-8")

    print(f"Build completado: {len(exercised_data)} ejercicios generados en {EJ_DIR}")
    for ed in exercised_data:
        print(f"  - {ed['key']}: {ed['title']}")


if __name__ == "__main__":
    main()

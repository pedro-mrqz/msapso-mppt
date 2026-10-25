"""
construir_reporte_V4.py — Compila el PDF final de la corrida V4 a partir de:
  * bitacora_V4.md                    (paso a paso con el razonamiento de cada paso; fuente unica)
  * reporte_frag_V4/*.html               (resumen ejecutivo, respuestas al profesor, conclusiones, limitaciones; escritos a mano)
  * resultados_V4/*.png               (figuras; se insertan despues del paso correspondiente)
  * codigo clave (anexo)
Genera reporte_V4.html y, con Chrome headless, Reporte_Corrida_V4.pdf (el indice se rellena con las paginas reales en 2 pasadas).
"""
import base64, html, re, subprocess, sys, os
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
RES = ROOT / "resultados_V4"
FRAG = ROOT / "reporte_frag_V4"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# figuras que se insertan DESPUES de cada paso (clave = numero de paso)
FIGS = {
    4: [("fig_mediciones_V4.png", "Figura B. Costo (mediciones, escala logarítmica) contra exactitud final y energía, en 100 patrones sintéticos nuevos sin ruido. Azul = con muestreo gaussiano; gris = sin muestreo; naranja = MSAPSO fiel del paper.")],
    8: [("fig_entrenamiento_largo_V4.png", "Figura C. REINFORCE con 15 veces más entrenamiento (media de 3 semillas): la eficiencia final apenas sube y solo iguala a la referencia sin aprendizaje; el punto μ casi no mejora.")],
}


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def fig_html(name, cap):
    p = RES / name
    if not p.exists():
        return ""
    return f'<figure><img src="data:image/png;base64,{b64(p)}" alt="{html.escape(cap[:60])}"/><figcaption>{cap}</figcaption></figure>'


def highlight(code_text):
    esc = html.escape(code_text)
    kw = r'\b(def|class|import|from|return|if|else|elif|for|while|as|with|in|not|and|or|True|False|None|self|try|except|raise|lambda|yield|break|continue|is)\b'
    out, in_tr = [], False
    for line in esc.split("\n"):
        if '"""' in line:
            parts = line.split('"""')
            if in_tr:
                line = f'<span class="cs">{parts[0]}"""</span>' + '"""'.join(parts[1:]); in_tr = (len(parts) % 2 == 0)
            else:
                line = parts[0] + '<span class="cs">"""' + '"""'.join(parts[1:]) + ('</span>' if len(parts) % 2 == 0 else ''); in_tr = not (len(parts) % 2 == 0)
        elif in_tr:
            line = f'<span class="cs">{line}</span>'
        elif "#" in line:
            i = line.index("#"); line = re.sub(kw, r'<span class="ck">\1</span>', line[:i]) + f'<span class="cc">{line[i:]}</span>'
        else:
            line = re.sub(kw, r'<span class="ck">\1</span>', line)
        out.append(line)
    return "\n".join(out)


def md(text):
    text = re.sub(r"(?<!\n)\n(?=\*\*)", "\n\n", text)      # cada etiqueta en negrita («Qué hice.», «Por qué.»...) abre un parrafo nuevo
    text = re.sub(r"(?m)^([^|\n][^\n]*)\n(?=\|)", r"\1\n\n", text)      # una tabla necesita una linea en blanco antes
    return markdown.markdown(text, extensions=["tables", "sane_lists"])


def split_bitacora():
    txt = (ROOT / "bitacora_V4.md").read_text()
    parts = re.split(r"\n---\n## PASO ", txt)
    head = parts[0]
    steps = []
    for p in parts[1:]:
        m = re.match(r"(\d+) — (.*?)\n(.*)", p, re.S)
        steps.append((int(m.group(1)), m.group(2).strip(), m.group(3)))
    return head, steps


CSS = (ROOT / "reporte_frag_V4" / "estilo.css").read_text()


def build(page_numbers=None):
    page_numbers = page_numbers or {}
    head, steps = split_bitacora()
    toc_items = [("resumen", "1. Resumen ejecutivo", 1), ("pasos", "2. Paso a paso de la corrida V4", 1)]
    for n, title, _ in steps:
        toc_items.append((f"paso{n}", f"   Paso {n} — {title}", 2))
    toc_items += [("conclusiones", "3. Conclusiones", 1), ("siguientes", "4. Siguientes pasos y preguntas para el profesor", 1),
                  ("limites", "5. Limitaciones y supuestos declarados", 1), ("archivos", "6. Mapa de archivos y cómo reproducir", 1),
                  ("anexo", "Anexo. Código clave", 1)]
    toc = "".join(f'<div class="toc-row l{lv}"><span>{html.escape(t)}</span><span class="dots"></span><span class="p">{page_numbers.get(i, "·")}</span></div>' for i, t, lv in toc_items)

    def frag(name): return (FRAG / name).read_text() if (FRAG / name).exists() else f"<p>[falta {name}]</p>"

    resumen = frag("resumen.html").replace("{{FIG:comparacion}}", fig_html("fig_comparacion_V4.png",
        "Figura A. Comparación en 100 patrones sintéticos nuevos y en los 4 casos reales (N = 7, K = 5; 12 mediciones salvo el MSAPSO, que usa 175). Eficiencia final = potencia en el punto elegido / GMPP; energía = promedio en una ventana de 200 mediciones. Las barras tenues son una cota de diagnóstico que usa el GMPP como etiqueta."))
    body = []
    body.append(f'<div class="page cover">{frag("portada.html")}</div>')
    body.append(f'<div class="page toc"><h2>Índice</h2>{toc}</div>')
    body.append(f'<div class="page"><section id="resumen"><span class="eyebrow">01</span><h2>1. Resumen ejecutivo</h2>{resumen}</section></div>')
    ctx = md(head.replace("# Bitácora de trabajo — Corrida V4 (proponer el máximo a partir de N potencias medidas, nivel 1)", "").replace("## ", "### "))
    body.append(f'<div class="page"><section id="pasos"><span class="eyebrow">02</span><h2>2. Paso a paso de la corrida V4</h2>'
                f'<p>Cada paso indica <strong>qué se hizo</strong>, <strong>por qué</strong> (el razonamiento), cómo se <strong>verificó</strong>, el <strong>resultado</strong> y los <strong>archivos</strong> que lo respaldan.</p>{ctx}</section></div>')
    for n, title, text in steps:
        figs = "".join(fig_html(f, c) for f, c in FIGS.get(n, []))
        body.append(f'<div class="page"><section id="paso{n}" class="step"><span class="eyebrow">Paso {n}</span><h2>Paso {n} — {html.escape(title)}</h2>{md(text)}{figs}</section></div>')
    body.append(f'<div class="page"><section id="conclusiones"><span class="eyebrow">03</span><h2>3. Conclusiones</h2>{frag("conclusiones.html")}</section></div>')
    body.append(f'<div class="page"><section id="siguientes"><span class="eyebrow">04</span><h2>4. Siguientes pasos y preguntas para el profesor</h2>{frag("siguientes.html")}</section></div>')
    body.append(f'<div class="page"><section id="limites"><span class="eyebrow">05</span><h2>5. Limitaciones y supuestos declarados</h2>{frag("limites.html")}</section></div>')
    body.append(f'<div class="page"><section id="archivos"><span class="eyebrow">06</span><h2>6. Mapa de archivos y cómo reproducir</h2>{frag("archivos.html")}</section></div>')
    annex = ['<section id="anexo"><span class="eyebrow">Anexo</span><h2>Anexo. Código clave</h2>']
    for f in ["pvsim_V4/medicion_V4.py", "pvsim_V4/static_plant_V4.py", "pvsim_V4/gym_env_V4.py", "reinforce_nn_V4.py", "ppo_nivel1_V4.py", "baselines_nivel1_V4.py"]:
        code = (ROOT / f).read_text()
        annex.append(f'<div class="filecard"><span class="fname">{f}</span><span class="flines">{len(code.splitlines())} líneas</span></div><pre class="code">{highlight(code)}</pre>')
    annex.append("</section>")
    body.append(f'<div class="page">{"".join(annex)}</div>')
    doc = f"<title>Reporte corrida V4</title><style>{CSS}</style>" \
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">' + "".join(body)
    (ROOT / "reporte_V4.html").write_text(doc)
    return toc_items


def render(pdf):
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "--print-to-pdf-no-header",
                    "--virtual-time-budget=20000", "--run-all-compositor-stages-before-draw", f"file://{ROOT}/reporte_V4.html"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)


def find_pages(pdf, items):
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    pages = txt.split("\f")
    out = {}
    for sid, title, lv in items:
        key = title.strip()
        key = re.sub(r"^\d+\.\s*", "", key)
        key = re.sub(r"^Paso (\d+) — ", r"Paso \1 — ", key)
        for pi, pg in enumerate(pages[2:], start=3):          # salta portada e indice
            if key[:40] in re.sub(r"\s+", " ", pg):
                out[sid] = pi; break
    return out


if __name__ == "__main__":
    items = build()
    pdf = ROOT / "Reporte_Corrida_V4.pdf"
    render(pdf)
    pages = find_pages(pdf, items)
    build(pages)
    render(pdf)
    print("PDF listo:", pdf, "| paginas indice:", len(pages), "/", len(items))

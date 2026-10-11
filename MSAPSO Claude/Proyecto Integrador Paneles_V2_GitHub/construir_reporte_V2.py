"""
construir_reporte_V2.py — Compila el PDF final de la corrida V2 a partir de:
  * bitacora_V2.md                    (paso a paso con el razonamiento de cada paso; fuente unica)
  * reporte_frag/*.html               (resumen ejecutivo, respuestas al profesor, conclusiones, limitaciones; escritos a mano)
  * resultados_V2/*.png               (figuras; se insertan despues del paso correspondiente)
  * codigo clave (anexo)
Genera reporte_V2.html y, con Chrome headless, Reporte_Corrida_V2.pdf (el indice se rellena con las paginas reales en 2 pasadas).
"""
import base64, html, re, subprocess, sys, os
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
RES = ROOT / "resultados_V2"
FRAG = ROOT / "reporte_frag"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# figuras que se insertan DESPUES de cada paso (clave = numero de paso)
FIGS = {
    2: [("fig_beta_convergencia_msapso_5ms.png", "Figura A. MSAPSO fiel: β (Eq. 14), dispersión de las partículas, Gbest y potencia por pasada, en los 4 casos reales (t_wait = 5 ms). Responde a la petición de graficar β conforme las partículas se acercan al MPP: Gbest se fija en las 1–3 primeras pasadas y la dispersión llega a ~0 hacia la pasada 12; de la 13 a la 25 el enjambre está colapsado."),
        ("fig_escalera_5ms.png", "Figura B. Barrido escalonado alternante (Caso 2, t_wait = 5 ms): un conjunto se prueba de menor a mayor corriente, el siguiente de mayor a menor. Se muestra la referencia I_ref (escalera), la corriente real del inductor que entrega el Super-Twisting simulado y la potencia del panel.")],
    3: [("fig_escalera_0.5ms.png", "Figura C. Mismo barrido con t_wait = 0.5 ms: la corriente del inductor no alcanza a seguir los escalones (el convertidor está limitado por la pendiente de corriente con L = 10 mH)."),
        ("fig_slew_controlador.png", "Figura D. Re-sintonizar el Super-Twisting: con ganancias ×10 el convertidor ya satura en su límite físico; ×100 y ×1000 no mejoran (Caso 1, escalón 6.7 ↔ 0.7 A).")],
    5: [("fig_reinforce_malla.png", "Figura E. REINFORCE gaussiano: energía % en sombras de entrenamiento según tasa de aprendizaje y σ (mejor normalización de recompensa por celda). La región buena es σ pequeña con paso efectivo c = lr/σ² moderado (0.3–1).")],
    6: [("fig_agente_vs_msapso_s0.png", "Figura F. Qué hace el agente PPO (semilla 0) frente al MSAPSO del paper: β elegido por pasada, dispersión de partículas, reinicios y potencia, en tres casos estáticos y tres transiciones."),
        ("fig_curva_aprendizaje.png", "Figura G. Curva de aprendizaje de PPO por semilla (energía % en los tres conjuntos de prueba vs pasos de entrenamiento) y referencia del MSAPSO fiel.")],
    8: [("fig_comparacion_5ms.png", "Figura H. Comparación de métodos, t_wait = 5 ms (régimen principal). Barras de error y puntos = desviación y valores por semilla de PPO. Las reglas «post-hoc» se probaron después de ver al agente."),
        ("fig_comparacion_05ms.png", "Figura I. Comparación en el régimen literal del paper (t_wait = 0.5 ms).")],
    10: [("fig_ablacion_senales.png", "Figura J. Ablación de señales de observación (PPO, 5 ms; media de 2 semillas; puntos = semillas).")],
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
    text = re.sub(r"(?<!\n)\n(?=\|)", "\n\n", text) if False else text
    return markdown.markdown(text, extensions=["tables", "sane_lists"])


def split_bitacora():
    txt = (ROOT / "bitacora_V2.md").read_text()
    parts = re.split(r"\n---\n## PASO ", txt)
    head = parts[0]
    steps = []
    for p in parts[1:]:
        m = re.match(r"(\d+) — (.*?)\n(.*)", p, re.S)
        steps.append((int(m.group(1)), m.group(2).strip(), m.group(3)))
    return head, steps


CSS = (ROOT / "reporte_frag" / "estilo.css").read_text()


def build(page_numbers=None):
    page_numbers = page_numbers or {}
    head, steps = split_bitacora()
    toc_items = [("resgen", "Resumen General y recomendaciones", 1), ("resumen", "1. Resumen ejecutivo", 1), ("respuestas", "2. Respuesta punto por punto a las observaciones del profesor", 1),
                 ("erratas", "3. Qué estaba mal en la V1 y cómo se corrigió", 1), ("pasos", "4. Paso a paso de la corrida V2", 1)]
    for n, title, _ in steps:
        toc_items.append((f"paso{n}", f"   Paso {n} — {title}", 2))
    toc_items += [("conclusiones", "5. Conclusiones", 1), ("limites", "6. Limitaciones, supuestos declarados y preguntas para el profesor", 1),
                  ("archivos", "7. Mapa de archivos y cómo reproducir", 1), ("anexo", "Anexo. Código clave y especificación del MSAPSO implementado", 1)]
    toc = "".join(f'<div class="toc-row l{lv}"><span>{html.escape(t)}</span><span class="dots"></span><span class="p">{page_numbers.get(i, "·")}</span></div>' for i, t, lv in toc_items)

    def frag(name): return (FRAG / name).read_text() if (FRAG / name).exists() else f"<p>[falta {name}]</p>"

    body = []
    body.append(f'<div class="page cover">{frag("portada.html")}</div>')
    body.append(f'<div class="page toc"><h2>Índice</h2>{toc}</div>')
    body.append(f'<div class="page"><section id="resgen"><span class="eyebrow">Resumen</span><h2>Resumen General y recomendaciones</h2>{frag("resumen_general.html")}</section></div>')
    body.append(f'<div class="page"><section id="resumen"><span class="eyebrow">01</span><h2>1. Resumen ejecutivo</h2>{frag("resumen.html")}</section></div>')
    body.append(f'<div class="page"><section id="respuestas"><span class="eyebrow">02</span><h2>2. Respuesta punto por punto a las observaciones del profesor</h2>{frag("respuestas.html")}</section></div>')
    body.append(f'<div class="page"><section id="erratas"><span class="eyebrow">03</span><h2>3. Qué estaba mal en la V1 y cómo se corrigió</h2>{frag("erratas.html")}</section></div>')
    # paso a paso
    ctx = md(head.replace("# Bitácora de trabajo — Corrida V2 (corrección y re-validación de las Fases 0–3)", "").replace("## ", "### "))
    body.append(f'<div class="page"><section id="pasos"><span class="eyebrow">04</span><h2>4. Paso a paso de la corrida V2</h2>'
                f'<p>Cada paso indica <strong>qué se hizo</strong>, <strong>por qué</strong> (el razonamiento), <strong>cómo se verificó</strong>, el <strong>resultado</strong> y los <strong>archivos</strong> que lo respaldan. '
                f'Es el registro cronológico de lo realizado; las figuras se insertan después del paso donde se generaron.</p>{ctx}</section></div>')
    for n, title, text in steps:
        figs = "".join(fig_html(f, c) for f, c in FIGS.get(n, []))
        body.append(f'<div class="page"><section id="paso{n}" class="step"><span class="eyebrow">Paso {n}</span><h2>Paso {n} — {html.escape(title)}</h2>{md(text)}{figs}</section></div>')
    body.append(f'<div class="page"><section id="conclusiones"><span class="eyebrow">05</span><h2>5. Conclusiones</h2>{frag("conclusiones.html")}</section></div>')
    body.append(f'<div class="page"><section id="limites"><span class="eyebrow">06</span><h2>6. Limitaciones, supuestos declarados y preguntas para el profesor</h2>{frag("limites.html")}</section></div>')
    body.append(f'<div class="page"><section id="archivos"><span class="eyebrow">07</span><h2>7. Mapa de archivos y cómo reproducir</h2>{frag("archivos.html")}</section></div>')
    # anexo de codigo
    annex = [f'<section id="anexo"><span class="eyebrow">Anexo</span><h2>Anexo. Código clave y especificación del MSAPSO implementado</h2>{frag("anexo_spec.html")}']
    for f in ["pvsim_V2/msapso_V2.py", "pvsim_V2/passrunner_V2.py", "pvsim_V2/gym_env_V2.py", "pvsim_V2/converter_V2.py", "pvsim_V2/reinforce_V2.py", "train_V2.py"]:
        code = (ROOT / f).read_text()
        annex.append(f'<div class="filecard"><span class="fname">{f}</span><span class="flines">{len(code.splitlines())} líneas</span></div><pre class="code">{highlight(code)}</pre>')
    annex.append("</section>")
    body.append(f'<div class="page">{"".join(annex)}</div>')
    doc = f"<title>Reporte corrida V2</title><style>{CSS}</style>" \
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">' + "".join(body)
    (ROOT / "reporte_V2.html").write_text(doc)
    return toc_items


def render(pdf):
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "--print-to-pdf-no-header",
                    "--virtual-time-budget=20000", "--run-all-compositor-stages-before-draw", f"file://{ROOT}/reporte_V2.html"],
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
    pdf = ROOT / "Reporte_Corrida_V2.pdf"
    render(pdf)
    pages = find_pages(pdf, items)
    build(pages)
    render(pdf)
    print("PDF listo:", pdf, "| paginas indice:", len(pages), "/", len(items))

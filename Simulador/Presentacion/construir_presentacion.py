"""Versión de presentación: 8 métodos sobre los 4 casos del manuscrito, sin selectores de caso/tramo, sin casillas ni «Condiciones de la campaña».
Uso: python construir_presentacion.py <simulador.html de los 4 casos> <salida.html> <salida_para_artefacto.html>  (ver README.md)"""
import json, re, sys
src, out_file, out_art = sys.argv[1:4]
L = open(src, encoding='utf-8').read().split('\n')
i = [k for k, l in enumerate(L) if l.startswith('const D=')][0]; D = json.loads(L[i][8:].rstrip(';'))
KEEP = ['msapso', 'v7', 'cem', 'mlp', 'mlp_pares', 'cedgo', 'decent', 'decent_alc']
D['metodos'] = [m for k in KEEP for m in D['metodos'] if m['id'] == k]
D['tabla'] = {k: v for k, v in D['tabla'].items() if k in KEEP}
D['runs'] = {k: v for k, v in D['runs'].items() if k.split('|')[3] in KEEP}
L[i] = 'const D=' + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + ';'
h = '\n'.join(L)

def rep(a, b):
    global h
    assert h.count(a) == 1, (h.count(a), a[:70]); h = h.replace(a, b)

TITLE = 'Simulador Métodos MPPT Sombras Parciales'
rep('<title>Comparador de métodos MPPT</title>', f'<title>{TITLE}</title>')
rep('<h1>Comparador MPPT bajo sombreado parcial</h1>', f'<h1>{TITLE}</h1>')
rep('</style>', '[hidden]{display:none!important}\n</style>')
rep("let si=0,wi=0,", "let si=0,wi=Math.max(0,D.waits.indexOf(0.005)),")
rep("fillSel($('tw'),D.waits,w=>(w*1000)+' ms');", "fillSel($('tw'),D.waits,w=>(+(w*1000).toFixed(2))+' ms');")
h = re.sub(r'<p class="sub">.*?</p>',
    '<p class="sub">Reproduce, medición por medición, cómo buscan el punto de máxima potencia los métodos evaluados en el proyecto. '
    'Toma como base el paper <i>Hybrid MPPT with Deterministic PSO and Super-Twisting</i>: su algoritmo MSAPSO es la referencia y sus cuatro curvas de sombreado parcial son los casos de prueba. '
    'Sirve como representación visual de los modelos: dos métodos a la vez, con la misma sombra y el mismo ruido, sobre el simulador dinámico del convertidor (Boost con control Super-Twisting). '
    'Elige el tipo de sombra y pulsa <b>Iniciar</b>; <b>ⓘ</b> explica cada método.</p>', h, count=1, flags=re.S)
# controles: solo tipo de sombra (los 4 casos), espera, ruido y velocidad; lo demás queda oculto y activo
rep('<div><label for="sc">Caso</label><select id="sc"></select></div>', '<div hidden><label for="sc">Caso</label><select id="sc"></select></div>')
rep('<div><label for="sg">Tramo de sombra</label><select id="sg"></select></div>', '<div hidden><label for="sg">Tramo de sombra</label><select id="sg"></select></div>')
for cid in ['fast', 'popc', 'reqc']:
    rep(f'<label class="chk"><input type="checkbox" id="{cid}" checked>', f'<label class="chk" hidden><input type="checkbox" id="{cid}" checked>')
rep('<button id="camp">Condiciones de la campaña</button>', '<button id="camp" hidden>Condiciones de la campaña</button>')
rep('const regOf=s=>s.meta.regimen', "D.scen.forEach(s=>{REG[s.meta.regimen]=[s.name,'']});const regOf=s=>s.meta.regimen")
rep("$('sctext').innerHTML='<b>'+regName(regOf(S))+' · '+S.name+'.</b> '", "$('sctext').innerHTML='<b>'+S.name+'.</b> '")
h = re.sub(r'<details><summary>¿Cómo se eligieron los escenarios\?</summary>.*?</details>',
    '<details><summary>¿Qué son los cuatro tipos de sombra?</summary><p>Son las cuatro curvas potencia–corriente del paper base: el <b>Caso 1</b> con irradiancia uniforme (un solo máximo) y los <b>Casos 2 a 4</b> con sombra parcial (varios máximos locales). '
    'Cada una se mantiene fija durante 600 mediciones, así que cada método hace una búsqueda y luego opera en la corriente que encontró. En el Caso 3 el máximo teórico cae en la zona que el convertidor no alcanza con la carga de 12 Ω. '
    'Las cifras de la pestaña Resultados no salen de estos cuatro casos: son las de las campañas con miles de escenarios aleatorios.</p></details>', h, count=1, flags=re.S)
rep("Ninguno lo logra: la candidata V14 es la que más energía gana, pero con una cola de hasta 23 pp; los demás no superan a la V7 o tienen colas peores.",
    "Entre estos métodos, solo el MLP + CEM gana energía a la V7 de forma demostrable (+1.01 pp), pero su cola no cumple; el DecentCEM tiene la cola más baja de los originales, pero su ventaja no es demostrable; el CEM puro, el CEDGO y las dos variantes nuevas pierden contra la V7.")
rep("la candidata V14 quedaría dentro del umbral de cola (media 0.41 pp, p99 1.4 pp); su peor caso dinámico sí existe. Las dos",
    "la candidata V14 (no incluida aquí) quedaría dentro del umbral de cola. Las dos")
open(out_file, 'w', encoding='utf-8').write(h)
# versión para artefacto: el host añade doctype/html/head/body
a = h
for x, y in [('<!doctype html>\n', ''), ('<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n', ''),
             ('</style></head><body><main>', '</style><main>'), ('</script></body></html>', '</script>')]:
    assert a.count(x) == 1, x; a = a.replace(x, y)
open(out_art, 'w', encoding='utf-8').write(a)
print(round(len(h) / 1e6, 2), 'MB')

"""
seleccion_V18.py — Aplica la regla de seleccion fijada en diseno_V18.md a los resultados de VALIDACION de las 40 variantes
(V18: estatico_val / dinamico_val; V18.1: estatico_val2 / dinamico_val2; mismos conjuntos y escenarios).
Regla: entre las variantes V18 con p99 <= 3 pp (b = 0.02) en los 5 conjuntos estaticos de validacion, la de mayor energia dinamica media en 600-1199;
empate (< 0.1 pp): la de menos mediciones estaticas (panel base). Si ninguna pasa el filtro: la de menor p99 maximo (y se reporta que falla el criterio 1).
-> resultados_V18/seleccion_V18.json|txt
"""
import json
import numpy as np

if __name__ == "__main__":
    S = json.load(open("resultados_V18/estatico_val_V18.json")) | json.load(open("resultados_V18/estatico_val2_V18.json"))
    D1, D2 = json.load(open("resultados_V18/dinamico_val_V18.json")), json.load(open("resultados_V18/dinamico_val2_V18.json"))
    assert [r["idx"] for r in D1] == [r["idx"] for r in D2]
    D = [a | b for a, b in zip(D1, D2)]                                   # las referencias se recalculan igual en ambas rondas (deterministas)
    conj = sorted({k.split("|")[0] for k in S}); base = [c for c in conj if c.startswith("base")][0]
    E = lambda n: np.array([r[n][0] for r in D])
    noms = [k for k in D[0] if k.startswith("NE ")]; filas = []
    for n in noms:
        p99 = {c: S[f"{c}|{n} b=0.02"]["p99"] for c in conj}
        filas.append(dict(variante=n, p99_max=max(p99.values()), p99=p99, media_base=S[f"{base}|{n} b=0.02"]["media"], med=S[f"{base}|{n} b=0.02"]["med"],
                          energia=float(E(n).mean()), vs_V7=float((E(n) - E("V7")).mean()), vs_V17=float((E(n) - E("V17")).mean()), vs_V11=float((E(n) - E("V11")).mean())))
    ok = [f for f in filas if f["p99_max"] <= 3.0]
    if ok:
        best = max(f["energia"] for f in ok); cand = [f for f in ok if best - f["energia"] < 0.1]; sel = min(cand, key=lambda f: f["med"]); regla = "pasa el filtro estatico; mayor energia dinamica"
    else:
        sel = min(filas, key=lambda f: f["p99_max"]); regla = "NINGUNA pasa el filtro estatico (p99 <= 3 pp): se elige la de menor p99 maximo"
    lines = ["SELECCION V18 (validacion). p99 max = peor p99 de los 5 conjuntos estaticos (b = 0.02); energia y diferencias: escenarios 600-1199",
             f"  {'variante':36s} | p99 max | perdida media base | med. | energia - V7 | - V17 | - V11"]
    for f in sorted(filas, key=lambda f: -f["energia"]):
        lines.append(f"  {f['variante']:36s} | {f['p99_max']:7.2f} | {f['media_base']:+.3f} | {f['med']:5.1f} | {f['vs_V7']:+.2f} | {f['vs_V17']:+.2f} | {f['vs_V11']:+.2f}" + ("  <- ELEGIDA" if f is sel else ""))
    for r in ("V11", "V14", "V17"):
        lines.append(f"  referencia {r:25s} | {max(S[f'{c}|{r} b=0.02']['p99'] for c in conj):7.2f} | {S[f'{base}|{r} b=0.02']['media']:+.3f} | {S[f'{base}|{r} b=0.02']['med']:5.1f} | {float((E(r) - E('V7')).mean()):+.2f}")
    lines.append(f"\nRegla: {regla}. Elegida: {sel['variante']}")
    print("\n".join(lines)); open("resultados_V18/seleccion_V18.txt", "w").write("\n".join(lines))
    json.dump(dict(elegida=sel["variante"], regla=regla, filas=filas), open("resultados_V18/seleccion_V18.json", "w"), indent=1)

"""
entrenar_mlp.py — Re-entrena el MLP de "MLP + CEM" y lo guarda en modelos/mlp_elegido.pkl.
Usalo si tu version de scikit-learn no puede abrir el modelo incluido (error al hacer pickle.load).
Misma receta que la V11: 30 000 sombras sinteticas (semilla 1111), capas (64, 64). Los resultados pueden cambiar ligeramente.
USO: python entrenar_mlp.py            -> modelos/mlp_elegido.pkl   (V11 original: solo potencias)
     python entrenar_mlp.py --pares    -> modelos/mlp_pares.pkl     (revision del profesor: pares corriente medida / potencia, con el borde de 12 ohm)
"""
import os, pickle, sys
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from algoritmos.mlp_cem import train_mlp, train_mlp_pares
if "--pares" in sys.argv:
    m = train_mlp_pares(n=30000, seed=1111, hidden=(64, 64)); ruta = os.path.join(ROOT, "modelos", "mlp_pares.pkl")
else:
    m = train_mlp(n=30000, seed=1111, hidden=(64, 64)); ruta = os.path.join(ROOT, "modelos", "mlp_elegido.pkl")
pickle.dump(m, open(ruta, "wb")); print("modelo guardado en", ruta)

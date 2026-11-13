"""
entrenar_mlp.py — Re-entrena el MLP de "MLP + CEM" y lo guarda en modelos/mlp_elegido.pkl.
Usalo si tu version de scikit-learn no puede abrir el modelo incluido (error al hacer pickle.load).
Misma receta que la V11: 30 000 sombras sinteticas (semilla 1111), capas (64, 64). Los resultados pueden cambiar ligeramente.
USO: python entrenar_mlp.py
"""
import os, pickle, sys
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from algoritmos.mlp_cem import train_mlp
m = train_mlp(n=30000, seed=1111, hidden=(64, 64))
pickle.dump(m, open(os.path.join(ROOT, "modelos", "mlp_elegido.pkl"), "wb")); print("modelo guardado en modelos/mlp_elegido.pkl")

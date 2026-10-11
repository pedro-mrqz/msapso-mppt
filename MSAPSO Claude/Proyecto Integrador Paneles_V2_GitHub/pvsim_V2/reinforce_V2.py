"""
reinforce_V2 — RAMA REINFORCE (gradiente de politica gaussiana) aplicada al MSAPSO, propuesta del profesor.

Idea: en vez de la actualizacion de MSAPSO x <- x + beta (Gbest - x), cada pasada se MUESTREAN K=7 corrientes candidatas de una
gaussiana N(mu, sigma^2) (en por unidad: corriente/Isc, asi sigma=0.3/0.5/0.8 son fracciones de Isc), se prueban en ESCALERA
(pasada ascendente, luego descendente, alternando; cada candidato se mantiene t_wait; Gbest se actualiza al instante), y se actualiza
mu con el gradiente del log de la gaussiana:  d/dmu log N(b; mu, sigma) = (b - mu)/sigma^2.
Parte «park» y regla de reinicio (|Pbest - Ppv| >= 5 W) IDENTICAS al MSAPSO fiel => se compara solo la regla de actualizacion.

Formas de la actualizacion (Delta_mu):
  form="B"  (forma del profesor):  lr_t * W * (G - mu) / sigma^2     con G = Gbest/Isc y W = R_G  (recompensa asociada a Gbest)
             (equivale a SAPSO con paso beta_eff = lr_t*W/sigma^2; el 'baseline' resta a W: none | V)
  form="A"  (estimador REINFORCE de libro): lr_t * (1/K) * sum_k w_k (b_k - mu)/sigma^2, con w_k = R_k - base_k
Recompensa R_k = P_k / P_norm,  P_norm = potencia nominal 250 W ("rated") o la mejor potencia vista en esta busqueda ("best").
Baselines (para la forma A):
  none : w = R                          V : w = R - V (V = media de R de las muestras previas de esta busqueda)
  Q    : w = R - Q^(b)                  QV: w = Q^(b) - V    (Q^ = regresion kernel gaussiana de R sobre b con las muestras previas)
Tasas de aprendizaje lr_t:  "fixed" (0.1 | 0.01 | 0.001),  "accel" (Eq.14: 0.1 -> 0.95),  "inv_t" (1/t, t = pasada desde el reinicio).
Paso efectivo c = lr*W/sigma^2: converge si 0 < c < 2 (sin sobrepaso si c <= 1); se registra para el analisis de estabilidad.
"""
import numpy as np

P_RATED = 250.0
BW = 0.1          # ancho de banda (por unidad) del regresor kernel Q^


class ReinforceController:
    def __init__(self, wait, form="A", baseline="none", lr="fixed", lr_value=0.01, sigma=0.5, rnorm="best",
                 K=7, t_max=25, thresh=5.0, mu0=0.5, rng=None, beta_min=0.1, beta_max=0.95):
        self.wait, self.form, self.baseline, self.lr, self.lr_value = wait, form, baseline, lr, lr_value
        self.sigma, self.rnorm, self.K, self.t_max, self.thresh, self.mu0 = sigma, rnorm, K, t_max, thresh, mu0
        self.beta_min, self.beta_max = beta_min, beta_max
        self.rng = rng or np.random.default_rng(0)
        self.started = False
        self.mode = "search"
        self.n_restarts = 0
        self.sw = self  # compatibilidad con run_scenario (usa ctrl.sw.n)
        self.n = K

    # ---------------- estado de una busqueda ----------------
    def _restart(self, plant, first=False):
        self.Isc = float(plant.curve.Isc)
        self.mu = self.mu0
        self.Pbest = 0.0
        self.Gbest = 0.0                      # corriente (A) del mejor punto medido
        self.t = 1
        self.direction = "ascending"
        self.hist_b, self.hist_R = [], []
        self.c_last = 0.0
        if not first:
            self.n_restarts += 1

    def _lr_t(self):
        if self.lr == "fixed":
            return self.lr_value
        if self.lr == "accel":
            return self.beta_min + (self.t / self.t_max) * (self.beta_max - self.beta_min)
        if self.lr == "inv_t":
            return 1.0 / self.t
        raise ValueError(self.lr)

    def _qhat(self, b, V):
        if not self.hist_b:
            return V
        hb, hR = np.array(self.hist_b), np.array(self.hist_R)
        w = np.exp(-0.5 * ((b - hb) / BW) ** 2)
        s = w.sum()
        return float((w * hR).sum() / s) if s > 1e-9 else V

    # ---------------- un paso de tiempo ----------------
    def step(self, plant):
        if not self.started:
            self._restart(plant, first=True)
            self.started = True
        if self.mode == "park":
            P, E = plant.run(self.K * self.wait, self.Gbest)
            restarted = False
            if abs(self.Pbest - P) >= self.thresh:
                self._restart(plant); self.mode = "search"; restarted = True
            return dict(E=E, P_end=P, P_max=P, beta=0.0, mode="park", disp=self.sigma, t=self.t, Gbest=self.Gbest,
                        Pbest=self.Pbest, restart=restarted)

        b = np.clip(self.rng.normal(self.mu, self.sigma, self.K), 0.02, 1.0)        # candidatos en por unidad
        order = np.argsort(b)
        if self.direction == "descending":
            order = order[::-1]
        P = np.zeros(self.K); E = 0.0
        for i in order:                                                              # escalera
            Pi, e = plant.run(self.wait, b[i] * self.Isc)
            P[i] = Pi; E += e
            if Pi >= self.Pbest:                                                     # Gbest inmediato (Ppv >= Pbest)
                self.Pbest, self.Gbest = Pi, plant.Ipv
        Pn = P_RATED if self.rnorm == "rated" else max(self.Pbest, 1e-6)
        R = P / Pn
        lr = self._lr_t()
        V = float(np.mean(self.hist_R)) if self.hist_R else float(R.mean())
        if self.form == "B":
            W = self.Pbest / Pn                                                      # recompensa asociada a Gbest
            if self.baseline == "V":
                W = W - V
            G = self.Gbest / self.Isc
            c = lr * W / self.sigma ** 2
            d_mu = c * (G - self.mu)
        else:
            if self.baseline == "none":
                w = R
            elif self.baseline == "V":
                w = R - V
            elif self.baseline == "Q":
                w = R - np.array([self._qhat(bk, V) for bk in b])
            elif self.baseline == "QV":
                w = np.array([self._qhat(bk, V) for bk in b]) - V
            else:
                raise ValueError(self.baseline)
            d_mu = lr * float(np.mean(w * (b - self.mu))) / self.sigma ** 2
            c = d_mu / max(abs(float(np.mean(b)) - self.mu), 1e-9)
        self.hist_b.extend(b.tolist()); self.hist_R.extend(R.tolist())
        self.mu = float(np.clip(self.mu + d_mu, 0.02, 1.0))
        self.c_last = float(c)
        t_now = self.t
        self.t += 1
        self.direction = "descending" if self.direction == "ascending" else "ascending"
        if self.t > self.t_max:
            self.mode = "park"
        return dict(E=E, P_end=float(P[order[-1]]), P_max=float(P.max()), beta=float(lr), mode="search", disp=self.sigma,
                    t=t_now, Gbest=self.Gbest, Pbest=self.Pbest, restart=False, mu=self.mu, c=float(c))

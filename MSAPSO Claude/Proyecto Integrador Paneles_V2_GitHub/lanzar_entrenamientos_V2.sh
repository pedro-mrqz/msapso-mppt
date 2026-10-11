#!/bin/bash
# Entrena en serie: (1) PPO principal a 5 ms, 3 semillas; (2) PPO a 0.5 ms (regimen literal del paper), 3 semillas;
# (3) ablacion de senales de observacion a 5 ms, 2 semillas por variante.   Cada corrida: 1,000,000 pasos, 4 entornos.
cd "$(dirname "$0")"
for s in 0 1 2; do python3 train_V2.py --wait 5e-3 --seed $s --timesteps 1000000 --n-envs 4 --obs full --tag ppo_5ms_full_s$s; done
for s in 0 1 2; do python3 train_V2.py --wait 5e-4 --seed $s --timesteps 1000000 --n-envs 4 --obs full --tag ppo_05ms_full_s$s; done
for v in no_disp no_time no_drop minimal; do
  for s in 0 1; do python3 train_V2.py --wait 5e-3 --seed $s --timesteps 1000000 --n-envs 4 --obs $v --tag ppo_5ms_${v}_s$s; done
done
echo TODO_LISTO

#!/bin/bash
# Extension: PPO con 3 M de pasos (3 semillas), y despues SAC y A2C (semilla 0) como otros metodos de RL.
cd "$(dirname "$0")"
for s in 0 1 2; do python3 train_V2.py --wait 5e-3 --seed $s --timesteps 3000000 --n-envs 4 --obs full --tag ppo_5ms_full3M_s$s; done
python3 train_V2.py --algo a2c --wait 5e-3 --seed 0 --timesteps 1000000 --n-envs 4 --obs full --tag a2c_5ms_full_s0
python3 train_V2.py --algo sac --wait 5e-3 --seed 0 --timesteps 300000 --n-envs 2 --obs full --tag sac_5ms_full_s0
echo EXT_LISTO

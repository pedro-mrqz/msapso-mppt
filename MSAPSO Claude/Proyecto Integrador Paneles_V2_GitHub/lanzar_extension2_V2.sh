#!/bin/bash
# Extension (version corta): PPO 3 M pasos semilla 1 (junto con la 0 = 2 semillas), y luego A2C y SAC (semilla 0) como otros metodos de RL.
cd "$(dirname "$0")"
python3 train_V2.py --wait 5e-3 --seed 1 --timesteps 3000000 --n-envs 4 --obs full --tag ppo_5ms_full3M_s1
python3 train_V2.py --algo a2c --wait 5e-3 --seed 0 --timesteps 1000000 --n-envs 4 --obs full --tag a2c_5ms_full_s0
python3 train_V2.py --algo sac --wait 5e-3 --seed 0 --timesteps 300000 --n-envs 2 --obs full --tag sac_5ms_full_s0
echo EXT2_LISTO

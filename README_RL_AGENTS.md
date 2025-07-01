# RL Agent System for Agent Tycoon

This directory contains scripts and modules for developing, training, evaluating, and extending reinforcement learning agents in the Agent Tycoon environment.

## Contents

- [`train_ppo_agent.py`](train_ppo_agent.py): Train a PPO agent using Stable-Baselines3.
- [`train_sac_agent.py`](train_sac_agent.py): Train a SAC agent using Stable-Baselines3.
- [`evaluate_agents.py`](evaluate_agents.py): Evaluate trained agents, HODL bot, and random agent.
- [`leaderboard.py`](leaderboard.py): Log and display agent performance results.
- [`tune_ppo_hyperparams.py`](tune_ppo_hyperparams.py): Hyperparameter tuning for PPO using Optuna.
- [`ensemble_agent.py`](ensemble_agent.py): Template for ensemble agent logic.
- [`advanced_rl_stubs.py`](advanced_rl_stubs.py): Stubs for meta-RL, multi-agent, hierarchical RL, and explainability.

## Quick Start

1. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Train an agent:**
   ```
   python train_ppo_agent.py
   python train_sac_agent.py
   ```

3. **Evaluate agents:**
   ```
   python evaluate_agents.py
   ```

4. **Log results to leaderboard:**
   - Use `leaderboard.py` to append and view results.

5. **Tune hyperparameters:**
   ```
   python tune_ppo_hyperparams.py
   ```

## Extending the System

- Use `ensemble_agent.py` to combine multiple agents for improved performance.
- Use `advanced_rl_stubs.py` as a starting point for research into meta-RL, multi-agent, hierarchical RL, and explainability.

## Notes

- All scripts assume the AgentTycoonEnv is available and gym-compatible.
- For best results, use a GPU-enabled environment for training.
- The system is modular and designed for rapid experimentation and extension.

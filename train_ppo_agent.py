import os
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback
from gym_environment import AgentTycoonEnv

def main():
    # Create vectorized environment for parallel training
    env = make_vec_env(lambda: AgentTycoonEnv(), n_envs=4)

    # Create evaluation environment
    eval_env = AgentTycoonEnv()

    # Set up PPO agent
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        n_steps=2048,
        batch_size=64,
        gae_lambda=0.95,
        gamma=0.99,
        learning_rate=3e-4,
        ent_coef=0.01,
        tensorboard_log="./ppo_agent_tensorboard/"
    )

    # Evaluation callback
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="./ppo_agent_best/",
        log_path="./ppo_agent_eval_logs/",
        eval_freq=5000,
        deterministic=True,
        render=False
    )

    # Train the agent
    model.learn(total_timesteps=200_000, callback=eval_callback)

    # Save the final model
    model.save("ppo_agent_final")

    print("Training complete. Model saved as 'ppo_agent_final'.")

if __name__ == "__main__":
    main()
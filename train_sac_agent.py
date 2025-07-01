import os
import gymnasium as gym
from stable_baselines3 import SAC
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback
from gym_environment import AgentTycoonEnv

def main():
    # Create vectorized environment for parallel training
    env = make_vec_env(lambda: AgentTycoonEnv(), n_envs=4)

    # Create evaluation environment
    eval_env = AgentTycoonEnv()

    # Set up SAC agent
    model = SAC(
        "MlpPolicy",
        env,
        verbose=1,
        buffer_size=100_000,
        learning_rate=3e-4,
        batch_size=256,
        tau=0.005,
        gamma=0.99,
        train_freq=1,
        gradient_steps=1,
        tensorboard_log="./sac_agent_tensorboard/"
    )

    # Evaluation callback
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="./sac_agent_best/",
        log_path="./sac_agent_eval_logs/",
        eval_freq=5000,
        deterministic=True,
        render=False
    )

    # Train the agent
    model.learn(total_timesteps=200_000, callback=eval_callback)

    # Save the final model
    model.save("sac_agent_final")

    print("Training complete. Model saved as 'sac_agent_final'.")

if __name__ == "__main__":
    main()
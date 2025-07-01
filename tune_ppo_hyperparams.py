import optuna
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from gym_environment import AgentTycoonEnv
import numpy as np

def optimize_agent(trial):
    n_envs = 2
    env = make_vec_env(lambda: AgentTycoonEnv(), n_envs=n_envs)

    # Hyperparameter search space
    learning_rate = trial.suggest_loguniform('learning_rate', 1e-5, 1e-3)
    n_steps = trial.suggest_categorical('n_steps', [512, 1024, 2048])
    batch_size = trial.suggest_categorical('batch_size', [32, 64, 128])
    gamma = trial.suggest_uniform('gamma', 0.95, 0.999)
    ent_coef = trial.suggest_loguniform('ent_coef', 1e-4, 0.1)

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        gamma=gamma,
        ent_coef=ent_coef,
        verbose=0
    )

    mean_rewards = []
    for _ in range(2):  # Run 2 short training/eval cycles per trial
        model.learn(total_timesteps=10_000)
        rewards = []
        for _ in range(2):
            obs, info = env.reset()
            done = [False] * n_envs
            total_reward = [0.0] * n_envs
            while not all(done):
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                for i in range(n_envs):
                    if not done[i]:
                        total_reward[i] += reward[i]
                        done[i] = terminated[i] or truncated[i]
            rewards.extend(total_reward)
        mean_rewards.append(np.mean(rewards))
    return np.mean(mean_rewards)

if __name__ == "__main__":
    study = optuna.create_study(direction="maximize")
    study.optimize(optimize_agent, n_trials=20)
    print("Best trial:")
    print(study.best_trial)
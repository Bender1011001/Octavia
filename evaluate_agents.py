import numpy as np
from stable_baselines3 import PPO, SAC
from gym_environment import AgentTycoonEnv
from hodl_bot import HODLBot
import random

def evaluate_rl_agent(model_path, agent_type="PPO", n_episodes=10):
    if agent_type == "PPO":
        model = PPO.load(model_path)
    elif agent_type == "SAC":
        model = SAC.load(model_path)
    else:
        raise ValueError("Unsupported agent type")
    env = AgentTycoonEnv()
    rewards = []
    for ep in range(n_episodes):
        obs, info = env.reset()
        done = False
        total_reward = 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
        rewards.append(total_reward)
    return np.mean(rewards), np.std(rewards)

def evaluate_random_agent(n_episodes=10):
    env = AgentTycoonEnv()
    rewards = []
    for ep in range(n_episodes):
        obs, info = env.reset()
        done = False
        total_reward = 0
        while not done:
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
        rewards.append(total_reward)
    return np.mean(rewards), np.std(rewards)

def evaluate_hodl_bot(n_episodes=10):
    env = AgentTycoonEnv()
    rewards = []
    for ep in range(n_episodes):
        obs, info = env.reset()
        hodl_bot = HODLBot(obs['cash'][0])
        done = False
        total_reward = 0
        while not done:
            # HODL bot logic: get_action expects an Observation object
            action = hodl_bot.get_action(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
        rewards.append(total_reward)
    return np.mean(rewards), np.std(rewards)

if __name__ == "__main__":
    print("Evaluating PPO agent...")
    ppo_mean, ppo_std = evaluate_rl_agent("ppo_agent_final.zip", agent_type="PPO")
    print(f"PPO Agent: Mean Reward = {ppo_mean:.2f}, Std = {ppo_std:.2f}")

    print("Evaluating SAC agent...")
    sac_mean, sac_std = evaluate_rl_agent("sac_agent_final.zip", agent_type="SAC")
    print(f"SAC Agent: Mean Reward = {sac_mean:.2f}, Std = {sac_std:.2f}")

    print("Evaluating Random agent...")
    rand_mean, rand_std = evaluate_random_agent()
    print(f"Random Agent: Mean Reward = {rand_mean:.2f}, Std = {rand_std:.2f}")

    print("Evaluating HODL bot...")
    hodl_mean, hodl_std = evaluate_hodl_bot()
    print(f"HODL Bot: Mean Reward = {hodl_mean:.2f}, Std = {hodl_std:.2f}")
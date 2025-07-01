"""
Example usage of the Agent Tycoon Gymnasium environment.
Demonstrates how to use the environment with standard RL libraries.
"""

import numpy as np
from gym_environment import AgentTycoonEnv


def random_agent_example():
    """Example of random agent interacting with environment."""
    print("=== Random Agent Example ===")
    env = AgentTycoonEnv(initial_cash=100000.0, max_episode_length=50, render_mode="human")
    
    # Run one episode
    obs, info = env.reset(seed=42)
    total_reward = 0
    
    print(f"Starting episode with ${obs['cash'][0]:,.2f} cash")
    
    for step in range(50):
        # Random action
        action = env.action_space.sample()
        
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        # Print progress every 10 steps
        if step % 10 == 0:
            print(f"\nStep {step + 1}:")
            env.render()
            print(f"Step reward: {reward:.2f}")
            print(f"Cumulative reward: {total_reward:.2f}")
            
        if terminated or truncated:
            print(f"\nEpisode ended at step {step + 1}")
            break
            
    print(f"\nEpisode finished. Total reward: {total_reward:.2f}")
    print(f"Final cash: ${obs['cash'][0]:,.2f}")
    print(f"Final NAV: ${obs['nav'][0]:,.2f}")
    env.close()


def simple_strategy_example():
    """Example of simple buy-and-hold strategy."""
    print("\n=== Simple Buy-and-Hold Strategy Example ===")
    env = AgentTycoonEnv(initial_cash=100000.0, max_episode_length=50, render_mode="human")
    
    obs, info = env.reset(seed=123)
    total_reward = 0
    
    print(f"Starting episode with ${obs['cash'][0]:,.2f} cash")
    print("Strategy: Buy stocks in first 5 steps, then hold")
    
    # Buy stocks in first few steps
    for step in range(5):
        action = {
            'action_type': np.array([1]),  # Allocate
            'asset_type': np.array([0]),   # Equity
            'asset_index': np.array([step % 5]),  # Cycle through stocks
            'amount_pct': np.array([0.2]),  # 20% of cash
            'cognition_cost': np.array([1.0])
        }
        
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        print(f"\nStep {step + 1} - Buying stocks:")
        print(f"  Cash remaining: ${obs['cash'][0]:,.2f}")
        print(f"  NAV: ${obs['nav'][0]:,.2f}")
        print(f"  Step reward: {reward:.2f}")
        
        if terminated or truncated:
            break
            
    # Hold for rest of episode
    for step in range(5, 50):
        action = {
            'action_type': np.array([0]),  # No action
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),
            'cognition_cost': np.array([0.0])
        }
        
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        # Print progress every 10 steps during holding period
        if step % 10 == 0:
            print(f"\nStep {step + 1} - Holding:")
            env.render()
            print(f"Step reward: {reward:.2f}")
            print(f"Cumulative reward: {total_reward:.2f}")
            
        if terminated or truncated:
            print(f"\nEpisode ended at step {step + 1}")
            break
            
    print(f"\nBuy-and-hold strategy completed.")
    print(f"Total reward: {total_reward:.2f}")
    print(f"Final cash: ${obs['cash'][0]:,.2f}")
    print(f"Final NAV: ${obs['nav'][0]:,.2f}")
    env.close()


def diversified_strategy_example():
    """Example of diversified investment strategy."""
    print("\n=== Diversified Investment Strategy Example ===")
    env = AgentTycoonEnv(initial_cash=100000.0, max_episode_length=30, render_mode="human")
    
    obs, info = env.reset(seed=456)
    total_reward = 0
    
    print(f"Starting episode with ${obs['cash'][0]:,.2f} cash")
    print("Strategy: Diversify across stocks, projects, and bonds")
    
    for step in range(30):
        # Diversified strategy: cycle through different asset types
        if obs['cash'][0] > 5000:  # Only invest if we have enough cash
            asset_type = step % 3  # 0=equity, 1=project, 2=bond
            
            if asset_type == 0:
                # Buy stocks
                action = {
                    'action_type': np.array([1]),
                    'asset_type': np.array([0]),
                    'asset_index': np.array([step % 5]),
                    'amount_pct': np.array([0.1]),  # 10% of cash
                    'cognition_cost': np.array([1.0])
                }
                action_desc = "Buying stocks"
            elif asset_type == 1:
                # Invest in projects
                action = {
                    'action_type': np.array([1]),
                    'asset_type': np.array([1]),
                    'asset_index': np.array([step % 3]),
                    'amount_pct': np.array([0.15]),  # 15% of cash
                    'cognition_cost': np.array([2.0])
                }
                action_desc = "Investing in projects"
            else:
                # Buy bonds
                action = {
                    'action_type': np.array([1]),
                    'asset_type': np.array([2]),
                    'asset_index': np.array([step % 5]),
                    'amount_pct': np.array([0.08]),  # 8% of cash
                    'cognition_cost': np.array([0.5])
                }
                action_desc = "Buying bonds"
        else:
            # Hold cash if running low
            action = {
                'action_type': np.array([0]),
                'asset_type': np.array([0]),
                'asset_index': np.array([0]),
                'amount_pct': np.array([0.0]),
                'cognition_cost': np.array([0.0])
            }
            action_desc = "Holding cash"
        
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        # Print progress every 5 steps
        if step % 5 == 0:
            print(f"\nStep {step + 1} - {action_desc}:")
            print(f"  Cash: ${obs['cash'][0]:,.2f}")
            print(f"  NAV: ${obs['nav'][0]:,.2f}")
            print(f"  Portfolio assets: {len([v for v in obs['portfolio_values'] if v > 0])}")
            print(f"  Step reward: {reward:.2f}")
            print(f"  Cumulative reward: {total_reward:.2f}")
            
            # Show news if any
            if np.any(obs['news_events'] > 0):
                print("  News events detected!")
        
        if terminated or truncated:
            print(f"\nEpisode ended at step {step + 1}")
            break
    
    print(f"\nDiversified strategy completed.")
    print(f"Total reward: {total_reward:.2f}")
    print(f"Final cash: ${obs['cash'][0]:,.2f}")
    print(f"Final NAV: ${obs['nav'][0]:,.2f}")
    
    # Show final portfolio composition
    portfolio_value = np.sum(obs['portfolio_values'])
    if portfolio_value > 0:
        print(f"Portfolio value: ${portfolio_value:,.2f}")
        print(f"Cash ratio: {obs['cash'][0] / obs['nav'][0] * 100:.1f}%")
        print(f"Investment ratio: {portfolio_value / obs['nav'][0] * 100:.1f}%")
    
    env.close()


def action_space_exploration():
    """Explore the action and observation spaces."""
    print("\n=== Action and Observation Space Exploration ===")
    env = AgentTycoonEnv()
    
    print("Action Space:")
    print(f"  Type: {type(env.action_space)}")
    for key, space in env.action_space.spaces.items():
        print(f"  {key}: {space}")
    
    print("\nObservation Space:")
    print(f"  Type: {type(env.observation_space)}")
    for key, space in env.observation_space.spaces.items():
        print(f"  {key}: {space}")
    
    # Sample some actions
    print("\nSample Actions:")
    for i in range(3):
        action = env.action_space.sample()
        print(f"  Action {i + 1}:")
        for key, value in action.items():
            if isinstance(value, np.ndarray):
                print(f"    {key}: {value}")
            else:
                print(f"    {key}: {value}")
    
    # Reset and show initial observation
    obs, info = env.reset()
    print("\nInitial Observation:")
    for key, value in obs.items():
        if isinstance(value, np.ndarray):
            if value.size <= 5:
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: shape={value.shape}, mean={np.mean(value):.2f}")
        else:
            print(f"  {key}: {value}")
    
    env.close()


def performance_comparison():
    """Compare different strategies over multiple episodes."""
    print("\n=== Strategy Performance Comparison ===")
    
    strategies = {
        'Random': random_strategy,
        'Conservative': conservative_strategy,
        'Aggressive': aggressive_strategy,
        'Balanced': balanced_strategy
    }
    
    results = {}
    num_episodes = 3
    
    for strategy_name, strategy_func in strategies.items():
        print(f"\nTesting {strategy_name} strategy...")
        
        episode_rewards = []
        final_navs = []
        
        for episode in range(num_episodes):
            env = AgentTycoonEnv(initial_cash=100000.0, max_episode_length=25)
            obs, info = env.reset(seed=episode * 100)
            
            total_reward = 0
            
            for step in range(25):
                action = strategy_func(obs, step)
                obs, reward, terminated, truncated, info = env.step(action)
                total_reward += reward
                
                if terminated or truncated:
                    break
            
            episode_rewards.append(total_reward)
            final_navs.append(obs['nav'][0])
            env.close()
        
        avg_reward = np.mean(episode_rewards)
        avg_nav = np.mean(final_navs)
        
        results[strategy_name] = {
            'avg_reward': avg_reward,
            'avg_nav': avg_nav,
            'rewards': episode_rewards,
            'navs': final_navs
        }
        
        print(f"  Average reward: {avg_reward:.2f}")
        print(f"  Average final NAV: ${avg_nav:,.2f}")
    
    # Print comparison
    print("\n=== Strategy Comparison Summary ===")
    print(f"{'Strategy':<12} {'Avg Reward':<12} {'Avg NAV':<15} {'ROI %':<8}")
    print("-" * 50)
    
    for strategy_name, result in results.items():
        roi = (result['avg_nav'] - 100000) / 100000 * 100
        print(f"{strategy_name:<12} {result['avg_reward']:<12.2f} ${result['avg_nav']:<14,.0f} {roi:<8.1f}")


def random_strategy(obs, step):
    """Random investment strategy."""
    if np.random.random() < 0.3:  # 30% chance to act
        return {
            'action_type': np.array([1]),
            'asset_type': np.array([np.random.randint(0, 3)]),
            'asset_index': np.array([np.random.randint(0, 5)]),
            'amount_pct': np.array([np.random.uniform(0.05, 0.2)]),
            'cognition_cost': np.array([np.random.uniform(0.5, 2.0)])
        }
    else:
        return {
            'action_type': np.array([0]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),
            'cognition_cost': np.array([0.0])
        }


def conservative_strategy(obs, step):
    """Conservative strategy - bonds and cash."""
    if step < 5 and obs['cash'][0] > 10000:
        return {
            'action_type': np.array([1]),
            'asset_type': np.array([2]),  # Bonds
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.1]),
            'cognition_cost': np.array([0.5])
        }
    else:
        return {
            'action_type': np.array([0]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),
            'cognition_cost': np.array([0.0])
        }


def aggressive_strategy(obs, step):
    """Aggressive strategy - stocks and projects."""
    if obs['cash'][0] > 5000:
        if step % 2 == 0:
            return {
                'action_type': np.array([1]),
                'asset_type': np.array([0]),  # Stocks
                'asset_index': np.array([step % 5]),
                'amount_pct': np.array([0.25]),
                'cognition_cost': np.array([2.0])
            }
        else:
            return {
                'action_type': np.array([1]),
                'asset_type': np.array([1]),  # Projects
                'asset_index': np.array([step % 3]),
                'amount_pct': np.array([0.2]),
                'cognition_cost': np.array([3.0])
            }
    else:
        return {
            'action_type': np.array([0]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),
            'cognition_cost': np.array([0.0])
        }


def balanced_strategy(obs, step):
    """Balanced strategy - mix of all assets."""
    if obs['cash'][0] > 8000:
        asset_type = step % 3
        return {
            'action_type': np.array([1]),
            'asset_type': np.array([asset_type]),
            'asset_index': np.array([step % 5]),
            'amount_pct': np.array([0.12]),
            'cognition_cost': np.array([1.5])
        }
    else:
        return {
            'action_type': np.array([0]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),
            'cognition_cost': np.array([0.0])
        }


if __name__ == "__main__":
    print("Agent Tycoon Gymnasium Environment Examples")
    print("=" * 50)
    
    # Run all examples
    action_space_exploration()
    random_agent_example()
    simple_strategy_example()
    diversified_strategy_example()
    performance_comparison()
    
    print("\n" + "=" * 50)
    print("All examples completed successfully!")
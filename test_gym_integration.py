"""
Integration tests for the Agent Tycoon Gymnasium Environment.
Tests full episodes and compatibility with RL libraries.
"""

import pytest
import numpy as np
from decimal import Decimal

from gym_environment import AgentTycoonEnv


class TestGymIntegration:
    """Integration test suite for AgentTycoonEnv."""
    
    def test_full_episode(self):
        """Test complete episode with random actions."""
        env = AgentTycoonEnv(initial_cash=100000.0, max_episode_length=50)
        
        # Reset environment
        obs, info = env.reset(seed=42)
        
        initial_cash = obs['cash'][0]
        assert initial_cash == 100000.0
        
        total_reward = 0.0
        step_count = 0
        
        # Run full episode
        while True:
            # Generate random action
            action = env.action_space.sample()
            
            # Take step
            obs, reward, terminated, truncated, info = env.step(action)
            
            total_reward += reward
            step_count += 1
            
            # Validate observation
            assert isinstance(obs, dict)
            assert obs['tick'][0] == step_count + 1
            assert obs['cash'][0] >= 0.0  # Cash should never go negative
            assert obs['nav'][0] >= 0.0   # NAV should never go negative
            
            # Check episode termination
            if terminated or truncated:
                break
                
            # Safety check to prevent infinite loops
            if step_count >= 100:
                break
        
        # Verify episode completed properly
        assert step_count <= 50  # Should not exceed max episode length
        assert isinstance(total_reward, float)
        
        print(f"Episode completed in {step_count} steps")
        print(f"Total reward: {total_reward:.2f}")
        print(f"Final cash: ${obs['cash'][0]:,.2f}")
        print(f"Final NAV: ${obs['nav'][0]:,.2f}")
        
        env.close()
    
    def test_stable_baselines_compatibility(self):
        """Test compatibility with stable-baselines3 (if available)."""
        try:
            import stable_baselines3 as sb3
            from stable_baselines3.common.env_checker import check_env
            
            env = AgentTycoonEnv(initial_cash=50000.0, max_episode_length=20)
            
            # Check environment compatibility
            try:
                check_env(env)
                print("Environment is compatible with stable-baselines3")
            except Exception as e:
                pytest.fail(f"Environment failed stable-baselines3 compatibility check: {e}")
            
            env.close()
            
        except ImportError:
            pytest.skip("stable-baselines3 not available, skipping compatibility test")
    
    def test_multiple_episodes(self):
        """Test running multiple episodes."""
        env = AgentTycoonEnv(initial_cash=75000.0, max_episode_length=25)
        
        episode_rewards = []
        episode_lengths = []
        
        # Run 5 episodes
        for episode in range(5):
            obs, info = env.reset(seed=episode * 10)  # Different seed each episode
            
            episode_reward = 0.0
            episode_length = 0
            
            while True:
                # Use a simple strategy: occasionally buy stocks
                if np.random.random() < 0.3:  # 30% chance to take action
                    action = {
                        'action_type': np.array([1]),      # Allocate
                        'asset_type': np.array([0]),       # Equity
                        'asset_index': np.array([episode % 5]),  # Cycle through stocks
                        'amount_pct': np.array([0.1]),     # 10% of cash
                        'cognition_cost': np.array([1.0])
                    }
                else:
                    action = {
                        'action_type': np.array([0]),      # No action
                        'asset_type': np.array([0]),
                        'asset_index': np.array([0]),
                        'amount_pct': np.array([0.0]),
                        'cognition_cost': np.array([0.0])
                    }
                
                obs, reward, terminated, truncated, info = env.step(action)
                
                episode_reward += reward
                episode_length += 1
                
                if terminated or truncated:
                    break
            
            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            
            print(f"Episode {episode + 1}: Length={episode_length}, Reward={episode_reward:.2f}, Final NAV=${obs['nav'][0]:,.2f}")
        
        # Verify all episodes completed
        assert len(episode_rewards) == 5
        assert len(episode_lengths) == 5
        assert all(length <= 25 for length in episode_lengths)
        
        # Calculate statistics
        avg_reward = np.mean(episode_rewards)
        avg_length = np.mean(episode_lengths)
        
        print(f"Average reward: {avg_reward:.2f}")
        print(f"Average episode length: {avg_length:.1f}")
        
        env.close()
    
    def test_different_strategies(self):
        """Test different investment strategies."""
        env = AgentTycoonEnv(initial_cash=100000.0, max_episode_length=30)
        
        strategies = {
            'conservative': self._conservative_strategy,
            'aggressive': self._aggressive_strategy,
            'balanced': self._balanced_strategy
        }
        
        results = {}
        
        for strategy_name, strategy_func in strategies.items():
            obs, info = env.reset(seed=123)  # Same seed for fair comparison
            
            total_reward = 0.0
            final_nav = 0.0
            
            for step in range(30):
                action = strategy_func(obs, step)
                obs, reward, terminated, truncated, info = env.step(action)
                
                total_reward += reward
                
                if terminated or truncated:
                    break
            
            final_nav = obs['nav'][0]
            
            results[strategy_name] = {
                'total_reward': total_reward,
                'final_nav': final_nav,
                'final_cash': obs['cash'][0]
            }
            
            print(f"{strategy_name.capitalize()} strategy:")
            print(f"  Total reward: {total_reward:.2f}")
            print(f"  Final NAV: ${final_nav:,.2f}")
            print(f"  Final cash: ${obs['cash'][0]:,.2f}")
        
        # Verify all strategies completed
        assert len(results) == 3
        for strategy_name, result in results.items():
            assert isinstance(result['total_reward'], float)
            assert result['final_nav'] > 0
            assert result['final_cash'] >= 0
        
        env.close()
    
    def _conservative_strategy(self, obs, step):
        """Conservative investment strategy - mostly bonds and cash."""
        if step < 5 and obs['cash'][0] > 10000:
            # Buy bonds early
            return {
                'action_type': np.array([1]),
                'asset_type': np.array([2]),       # Bond
                'asset_index': np.array([0]),      # First bond
                'amount_pct': np.array([0.05]),    # 5% of cash
                'cognition_cost': np.array([0.5])
            }
        else:
            # Hold cash
            return {
                'action_type': np.array([0]),
                'asset_type': np.array([0]),
                'asset_index': np.array([0]),
                'amount_pct': np.array([0.0]),
                'cognition_cost': np.array([0.0])
            }
    
    def _aggressive_strategy(self, obs, step):
        """Aggressive investment strategy - mostly stocks and projects."""
        if obs['cash'][0] > 5000:
            if step % 3 == 0:
                # Buy stocks
                return {
                    'action_type': np.array([1]),
                    'asset_type': np.array([0]),       # Equity
                    'asset_index': np.array([step % 5]),  # Cycle through stocks
                    'amount_pct': np.array([0.2]),     # 20% of cash
                    'cognition_cost': np.array([2.0])
                }
            elif step % 3 == 1:
                # Invest in projects
                return {
                    'action_type': np.array([1]),
                    'asset_type': np.array([1]),       # Project
                    'asset_index': np.array([step % 3]),  # Cycle through projects
                    'amount_pct': np.array([0.15]),    # 15% of cash
                    'cognition_cost': np.array([3.0])
                }
        
        # No action
        return {
            'action_type': np.array([0]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),
            'cognition_cost': np.array([0.0])
        }
    
    def _balanced_strategy(self, obs, step):
        """Balanced investment strategy - mix of all asset types."""
        if obs['cash'][0] > 8000:
            asset_type = step % 3  # Cycle through asset types
            
            return {
                'action_type': np.array([1]),
                'asset_type': np.array([asset_type]),
                'asset_index': np.array([step % 5]),
                'amount_pct': np.array([0.1]),     # 10% of cash
                'cognition_cost': np.array([1.5])
            }
        
        # No action
        return {
            'action_type': np.array([0]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),
            'cognition_cost': np.array([0.0])
        }
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        env = AgentTycoonEnv(initial_cash=1000.0, max_episode_length=10)  # Low cash
        
        obs, info = env.reset(seed=42)
        
        # Test action with invalid asset index
        invalid_action = {
            'action_type': np.array([1]),
            'asset_type': np.array([0]),
            'asset_index': np.array([99]),     # Invalid index
            'amount_pct': np.array([0.5]),
            'cognition_cost': np.array([1.0])
        }
        
        # Should not crash, just return None action
        obs, reward, terminated, truncated, info = env.step(invalid_action)
        assert isinstance(reward, float)
        
        # Test action with 0% amount
        zero_action = {
            'action_type': np.array([1]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),     # 0% amount
            'cognition_cost': np.array([1.0])
        }
        
        obs, reward, terminated, truncated, info = env.step(zero_action)
        assert isinstance(reward, float)
        
        # Test action with more cash than available
        large_action = {
            'action_type': np.array([1]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([2.0]),     # 200% of cash (invalid)
            'cognition_cost': np.array([1.0])
        }
        
        # Should handle gracefully
        obs, reward, terminated, truncated, info = env.step(large_action)
        assert isinstance(reward, float)
        
        env.close()
    
    def test_observation_consistency(self):
        """Test that observations remain consistent across steps."""
        env = AgentTycoonEnv(initial_cash=50000.0, max_episode_length=20)
        
        obs, info = env.reset(seed=42)
        
        previous_tick = obs['tick'][0]
        
        for step in range(10):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            
            # Tick should increment by 1 each step
            assert obs['tick'][0] == previous_tick + 1
            previous_tick = obs['tick'][0]
            
            # Cash + portfolio value should equal NAV (approximately)
            portfolio_value = np.sum(obs['portfolio_values'])
            nav_calculated = obs['cash'][0] + portfolio_value
            nav_reported = obs['nav'][0]
            
            # Allow small floating point differences
            assert abs(nav_calculated - nav_reported) < 1.0, f"NAV mismatch: calculated={nav_calculated}, reported={nav_reported}"
            
            # All arrays should have correct shapes
            assert obs['stock_prices'].shape == (5,)
            assert obs['project_info'].shape == (15,)
            assert obs['bond_prices'].shape == (5,)
            assert obs['news_events'].shape == (10,)
            
            if terminated or truncated:
                break
        
        env.close()


if __name__ == "__main__":
    pytest.main([__file__])
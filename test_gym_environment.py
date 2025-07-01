"""
Unit tests for the Agent Tycoon Gymnasium Environment.
"""

import pytest
import numpy as np
import gymnasium as gym
from decimal import Decimal

from gym_environment import AgentTycoonEnv
from models import CapitalAllocationAction, EquityAlloc, ProjectAlloc, BondAlloc


class TestAgentTycoonEnv:
    """Test suite for AgentTycoonEnv."""
    
    def test_environment_initialization(self):
        """Test environment initializes correctly."""
        env = AgentTycoonEnv(initial_cash=50000.0, max_episode_length=50)
        
        assert env.initial_cash == Decimal('50000.00')
        assert env.max_episode_length == 50
        assert env.render_mode is None
        assert env.episode_length == 0
        
        # Check that backends are initialized
        assert env.trade_backend is not None
        assert env.project_backend is not None
        assert env.debt_backend is not None
        assert env.ledger is not None
        assert env.allocation_manager is not None
        assert env.engine is not None
        
        env.close()
    
    def test_action_space_structure(self):
        """Test action space has correct structure."""
        env = AgentTycoonEnv()
        
        assert isinstance(env.action_space, gym.spaces.Dict)
        
        # Check action space components
        assert 'action_type' in env.action_space.spaces
        assert 'asset_type' in env.action_space.spaces
        assert 'asset_index' in env.action_space.spaces
        assert 'amount_pct' in env.action_space.spaces
        assert 'cognition_cost' in env.action_space.spaces
        
        # Check discrete spaces
        assert env.action_space['action_type'].n == 2  # no action, allocate
        assert env.action_space['asset_type'].n == 3   # equity, project, bond
        assert env.action_space['asset_index'].n == 10 # max 10 assets
        
        # Check box spaces
        assert env.action_space['amount_pct'].shape == (1,)
        assert env.action_space['amount_pct'].low[0] == 0.0
        assert env.action_space['amount_pct'].high[0] == 1.0
        
        assert env.action_space['cognition_cost'].shape == (1,)
        assert env.action_space['cognition_cost'].low[0] == 0.0
        assert env.action_space['cognition_cost'].high[0] == 100.0
        
        env.close()
    
    def test_observation_space_structure(self):
        """Test observation space has correct structure."""
        env = AgentTycoonEnv(max_episode_length=50)
        
        assert isinstance(env.observation_space, gym.spaces.Dict)
        
        # Check observation space components
        expected_keys = [
            'tick', 'cash', 'nav', 'portfolio_values', 'stock_prices',
            'project_info', 'bond_prices', 'news_events'
        ]
        
        for key in expected_keys:
            assert key in env.observation_space.spaces
        
        # Check specific shapes
        assert env.observation_space['tick'].n == 51  # max_episode_length + 1
        assert env.observation_space['cash'].shape == (1,)
        assert env.observation_space['nav'].shape == (1,)
        assert env.observation_space['portfolio_values'].shape == (20,)
        assert env.observation_space['stock_prices'].shape == (5,)
        assert env.observation_space['project_info'].shape == (15,)  # 5 projects * 3 features
        assert env.observation_space['bond_prices'].shape == (5,)
        assert env.observation_space['news_events'].shape == (10,)
        
        env.close()
    
    def test_reset_functionality(self):
        """Test reset returns valid observation."""
        env = AgentTycoonEnv(initial_cash=75000.0, max_episode_length=30)
        
        obs, info = env.reset(seed=42)
        
        # Check observation structure
        assert isinstance(obs, dict)
        assert 'tick' in obs
        assert 'cash' in obs
        assert 'nav' in obs
        
        # Check initial values
        assert obs['tick'][0] == 1  # First tick after reset
        assert obs['cash'][0] == 75000.0
        assert obs['nav'][0] == 75000.0  # Should equal cash initially
        
        # Check info structure
        assert isinstance(info, dict)
        assert 'failed_allocations' in info
        assert 'episode_length' in info
        assert info['episode_length'] == 0
        
        # Check environment state
        assert env.episode_length == 0
        assert env.current_observation is not None
        
        env.close()
    
    def test_step_functionality(self):
        """Test step with valid action."""
        env = AgentTycoonEnv(initial_cash=100000.0)
        
        obs, info = env.reset(seed=42)
        
        # Create a valid action (buy equity)
        action = {
            'action_type': np.array([1]),      # Allocate
            'asset_type': np.array([0]),       # Equity
            'asset_index': np.array([0]),      # First stock (AAPL)
            'amount_pct': np.array([0.1]),     # 10% of cash
            'cognition_cost': np.array([5.0])
        }
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Check return types
        assert isinstance(obs, dict)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)
        
        # Check observation structure
        assert 'tick' in obs
        assert 'cash' in obs
        assert 'nav' in obs
        
        # Check episode progression
        assert env.episode_length == 1
        assert obs['tick'][0] == 2  # Second tick
        
        # Cash should be reduced (bought stocks)
        assert obs['cash'][0] < 100000.0
        
        env.close()
    
    def test_action_conversion(self):
        """Test conversion from gym action to CapitalAllocationAction."""
        env = AgentTycoonEnv()
        
        # Test no action
        no_action = {
            'action_type': np.array([0]),
            'asset_type': np.array([0]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.0]),
            'cognition_cost': np.array([0.0])
        }
        
        result = env._convert_action(no_action)
        assert result is None
        
        # Test equity action
        equity_action = {
            'action_type': np.array([1]),
            'asset_type': np.array([0]),
            'asset_index': np.array([1]),
            'amount_pct': np.array([0.2]),
            'cognition_cost': np.array([10.0])
        }
        
        result = env._convert_action(equity_action)
        assert result is not None
        assert isinstance(result, CapitalAllocationAction)
        assert result.action_type == "ALLOCATE_CAPITAL"
        assert len(result.allocations) == 1
        assert isinstance(result.allocations[0], EquityAlloc)
        assert result.cognition_cost == Decimal('10.0')
        
        # Test project action
        project_action = {
            'action_type': np.array([1]),
            'asset_type': np.array([1]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.15]),
            'cognition_cost': np.array([15.0])
        }
        
        result = env._convert_action(project_action)
        assert result is not None
        assert len(result.allocations) == 1
        assert isinstance(result.allocations[0], ProjectAlloc)
        
        # Test bond action
        bond_action = {
            'action_type': np.array([1]),
            'asset_type': np.array([2]),
            'asset_index': np.array([0]),
            'amount_pct': np.array([0.05]),
            'cognition_cost': np.array([2.0])
        }
        
        result = env._convert_action(bond_action)
        assert result is not None
        assert len(result.allocations) == 1
        assert isinstance(result.allocations[0], BondAlloc)
        
        env.close()
    
    def test_observation_conversion(self):
        """Test conversion from Observation to gym format."""
        env = AgentTycoonEnv()
        obs, info = env.reset(seed=42)
        
        # Get the internal observation
        internal_obs = env.current_observation
        
        # Convert to gym format
        gym_obs = env._convert_observation(internal_obs)
        
        # Check structure
        assert isinstance(gym_obs, dict)
        assert 'tick' in gym_obs
        assert 'cash' in gym_obs
        assert 'nav' in gym_obs
        assert 'portfolio_values' in gym_obs
        assert 'stock_prices' in gym_obs
        assert 'project_info' in gym_obs
        assert 'bond_prices' in gym_obs
        assert 'news_events' in gym_obs
        
        # Check data types and shapes
        assert gym_obs['tick'].dtype == np.int32
        assert gym_obs['tick'].shape == (1,)
        
        assert gym_obs['cash'].dtype == np.float32
        assert gym_obs['cash'].shape == (1,)
        
        assert gym_obs['portfolio_values'].dtype == np.float32
        assert gym_obs['portfolio_values'].shape == (20,)
        
        assert gym_obs['stock_prices'].dtype == np.float32
        assert gym_obs['stock_prices'].shape == (5,)
        
        assert gym_obs['project_info'].dtype == np.float32
        assert gym_obs['project_info'].shape == (15,)
        
        assert gym_obs['bond_prices'].dtype == np.float32
        assert gym_obs['bond_prices'].shape == (5,)
        
        assert gym_obs['news_events'].dtype == np.float32
        assert gym_obs['news_events'].shape == (10,)
        
        env.close()
    
    def test_episode_termination(self):
        """Test episode ends at max length."""
        env = AgentTycoonEnv(max_episode_length=5)
        
        obs, info = env.reset()
        
        # Run for max episode length
        for i in range(5):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            
            if i < 4:  # Not the last step
                assert not truncated
            else:  # Last step
                assert truncated
        
        assert env.episode_length == 5
        
        env.close()
    
    def test_rendering(self):
        """Test rendering functionality."""
        env = AgentTycoonEnv(render_mode="human")
        
        obs, info = env.reset()
        
        # Test human rendering (should not raise exception)
        try:
            env.render()
        except Exception as e:
            pytest.fail(f"Human rendering failed: {e}")
        
        env.close()
        
        # Test RGB array rendering
        env = AgentTycoonEnv(render_mode="rgb_array")
        obs, info = env.reset()
        
        rgb_array = env.render()
        assert isinstance(rgb_array, np.ndarray)
        assert rgb_array.shape == (400, 600, 3)
        assert rgb_array.dtype == np.uint8
        
        env.close()
    
    def test_action_space_sampling(self):
        """Test that action space sampling works correctly."""
        env = AgentTycoonEnv()
        
        # Sample multiple actions
        for _ in range(10):
            action = env.action_space.sample()
            
            # Check action structure
            assert isinstance(action, dict)
            assert 'action_type' in action
            assert 'asset_type' in action
            assert 'asset_index' in action
            assert 'amount_pct' in action
            assert 'cognition_cost' in action
            
            # Check value ranges
            assert 0 <= action['action_type'] < 2
            assert 0 <= action['asset_type'] < 3
            assert 0 <= action['asset_index'] < 10
            assert 0.0 <= action['amount_pct'][0] <= 1.0
            assert 0.0 <= action['cognition_cost'][0] <= 100.0
        
        env.close()
    
    def test_multiple_steps(self):
        """Test running multiple steps in sequence."""
        env = AgentTycoonEnv(initial_cash=100000.0, max_episode_length=20)
        
        obs, info = env.reset(seed=123)
        
        total_reward = 0.0
        
        for step in range(10):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            
            total_reward += reward
            
            # Check that observation is valid
            assert isinstance(obs, dict)
            assert obs['tick'][0] == step + 2  # Tick starts at 1 after reset
            
            # Check that episode hasn't ended prematurely
            assert not terminated
            assert not truncated
        
        assert env.episode_length == 10
        assert isinstance(total_reward, float)
        
        env.close()
    
    def test_price_provider_functionality(self):
        """Test that price provider works correctly."""
        env = AgentTycoonEnv()
        
        price_provider = env._get_price_provider()
        
        # Test equity price
        equity_price = price_provider.get_price("AAPL")
        assert equity_price is not None
        assert isinstance(equity_price, Decimal)
        
        # Test bond price
        bond_price = price_provider.get_bond_price("BOND-001")
        assert bond_price is not None
        assert isinstance(bond_price, Decimal)
        
        # Test unknown equity
        unknown_equity_price = price_provider.get_price("UNKNOWN")
        assert unknown_equity_price is None
        
        # Test unknown bond
        unknown_bond_price = price_provider.get_bond_price("UNKNOWN")
        assert unknown_bond_price is None
        
        env.close()


if __name__ == "__main__":
    pytest.main([__file__])
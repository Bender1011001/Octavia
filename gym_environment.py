"""
Agent Tycoon Gymnasium Environment

A sophisticated financial simulation environment where agents learn to make
intelligent capital allocation decisions across stocks, projects, and bonds.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, Any, Tuple, Optional
from decimal import Decimal

from models import CapitalAllocationAction, Observation, EquityAlloc, ProjectAlloc, BondAlloc
from engine import SimulationEngine
from ledger import Ledger
from router import AllocationManager
from backends import TradeBackend, ProjectBackend, DebtBackend


class AgentTycoonEnv(gym.Env):
    """
    Agent Tycoon Gymnasium Environment
    
    A sophisticated financial simulation environment where agents learn to make
    intelligent capital allocation decisions across stocks, projects, and bonds.
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 4}
    
    def __init__(self, initial_cash: float = 100000.0, max_episode_length: int = 100,
                 render_mode: Optional[str] = None):
        super().__init__()
        
        self.initial_cash = Decimal(str(initial_cash))
        self.max_episode_length = max_episode_length
        self.render_mode = render_mode
        
        # Initialize backends
        self.trade_backend = TradeBackend()
        self.project_backend = ProjectBackend()
        self.debt_backend = DebtBackend()
        
        # Initialize core components
        self.ledger = Ledger(self.initial_cash, price_provider=self._get_price_provider())
        self.allocation_manager = AllocationManager(
            self.ledger, self.trade_backend, self.project_backend, self.debt_backend
        )
        self.engine = SimulationEngine(self.ledger, self.allocation_manager)
        
        # Define action space
        # Action space: [action_type, asset_type, asset_id, amount, cognition_cost]
        # Simplified to discrete actions for easier RL training
        self.action_space = spaces.Dict({
            'action_type': spaces.Discrete(2),  # 0: no action, 1: allocate
            'asset_type': spaces.Discrete(3),   # 0: equity, 1: project, 2: bond
            'asset_index': spaces.Discrete(10), # Index into available assets
            'amount_pct': spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32),  # Percentage of cash
            'cognition_cost': spaces.Box(low=0.0, high=100.0, shape=(1,), dtype=np.float32)
        })
        
        # Define observation space
        self.observation_space = spaces.Dict({
            'tick': spaces.Discrete(self.max_episode_length + 1),
            'cash': spaces.Box(low=0.0, high=np.inf, shape=(1,), dtype=np.float32),
            'nav': spaces.Box(low=0.0, high=np.inf, shape=(1,), dtype=np.float32),
            'portfolio_values': spaces.Box(low=0.0, high=np.inf, shape=(20,), dtype=np.float32),  # Max 20 assets
            'stock_prices': spaces.Box(low=0.0, high=np.inf, shape=(5,), dtype=np.float32),  # 5 stocks
            'project_info': spaces.Box(low=0.0, high=1.0, shape=(15,), dtype=np.float32),  # 5 projects * 3 features
            'bond_prices': spaces.Box(low=0.0, high=np.inf, shape=(5,), dtype=np.float32),  # 5 bonds
            'news_events': spaces.Box(low=0.0, high=1.0, shape=(10,), dtype=np.float32)  # One-hot encoded news
        })
        
        self.current_observation = None
        self.episode_length = 0
        
    def _get_price_provider(self):
        """Create price provider function for ledger."""
        class PriceProvider:
            def __init__(self, trade_backend, debt_backend):
                self.trade_backend = trade_backend
                self.debt_backend = debt_backend
            
            def get_price(self, identifier: str) -> Optional[Decimal]:
                return self.trade_backend.get_price(identifier)
            
            def get_bond_price(self, identifier: str) -> Optional[Decimal]:
                return self.debt_backend.get_bond_price(identifier)
        
        return PriceProvider(self.trade_backend, self.debt_backend)
        
    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """Reset the environment to initial state."""
        super().reset(seed=seed)
        
        if seed is not None:
            np.random.seed(seed)
            
        # Reset all components
        self.ledger = Ledger(self.initial_cash, price_provider=self._get_price_provider())
        self.allocation_manager = AllocationManager(
            self.ledger, self.trade_backend, self.project_backend, self.debt_backend
        )
        self.engine = SimulationEngine(self.ledger, self.allocation_manager)
        
        # Get initial observation
        obs, _, _, _, info = self.engine.tick()
        self.current_observation = obs
        self.episode_length = 0
        
        return self._convert_observation(obs), self._convert_info(info)
        
    def step(self, action: Dict[str, np.ndarray]) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict[str, Any]]:
        """Execute one step in the environment."""
        self.episode_length += 1
        
        # Convert action to CapitalAllocationAction
        capital_action = self._convert_action(action)
        
        # Execute step in simulation engine
        obs, reward, terminated, truncated, info = self.engine.tick(capital_action)
        
        # Check if episode should end
        if self.episode_length >= self.max_episode_length:
            truncated = True
            
        self.current_observation = obs
        
        return (
            self._convert_observation(obs),
            float(reward),
            terminated,
            truncated,
            self._convert_info(info)
        )
        
    def _convert_action(self, action: Dict[str, np.ndarray]) -> Optional[CapitalAllocationAction]:
        """Convert gym action to CapitalAllocationAction."""
        # Handle both scalar and array inputs
        action_type = int(action['action_type'].item() if hasattr(action['action_type'], 'item') else action['action_type'])
        
        if action_type == 0:  # No action
            return None
            
        asset_type = int(action['asset_type'].item() if hasattr(action['asset_type'], 'item') else action['asset_type'])
        asset_index = int(action['asset_index'].item() if hasattr(action['asset_index'], 'item') else action['asset_index'])
        amount_pct = float(action['amount_pct'][0] if hasattr(action['amount_pct'], '__getitem__') else action['amount_pct'])
        cognition_cost = Decimal(str(float(action['cognition_cost'][0] if hasattr(action['cognition_cost'], '__getitem__') else action['cognition_cost']))).quantize(Decimal('0.01'))
        
        # Calculate USD amount based on percentage of cash and quantize to 2 decimal places
        usd_amount = (self.ledger.cash * Decimal(str(amount_pct))).quantize(Decimal('0.01'))
        
        allocations = []
        
        if asset_type == 0:  # Equity
            tickers = list(self.trade_backend.stocks.keys())
            if asset_index < len(tickers):
                ticker = tickers[asset_index]
                allocations.append(EquityAlloc(
                    asset_type="EQUITY",
                    ticker=ticker,
                    usd=usd_amount
                ))
                
        elif asset_type == 1:  # Project
            projects = self.project_backend.get_available_projects()
            if asset_index < len(projects):
                project = projects[asset_index]
                allocations.append(ProjectAlloc(
                    asset_type="PROJECT",
                    project_id=project.project_id,
                    usd=usd_amount
                ))
                
        elif asset_type == 2:  # Bond
            bonds = list(self.debt_backend.bonds.keys())
            if asset_index < len(bonds):
                bond_id = bonds[asset_index]
                allocations.append(BondAlloc(
                    asset_type="BOND",
                    bond_id=bond_id,
                    usd=usd_amount
                ))
        
        if not allocations:
            return None
            
        return CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Gym environment action",
            allocations=allocations,
            cognition_cost=cognition_cost
        )
        
    def _convert_observation(self, obs: Observation) -> Dict[str, np.ndarray]:
        """Convert Observation to gym observation format."""
        # Portfolio values (pad to 20)
        portfolio_values = np.zeros(20, dtype=np.float32)
        for i, holding in enumerate(obs.portfolio[:20]):
            portfolio_values[i] = float(holding.current_value)
            
        # Stock prices
        stock_prices = np.zeros(5, dtype=np.float32)
        for i, ticker in enumerate(list(self.trade_backend.stocks.keys())[:5]):
            price = self.trade_backend.get_price(ticker)
            stock_prices[i] = float(price) if price else 0.0
            
        # Project info (5 projects * 3 features: investment, return, weeks)
        project_info = np.zeros(15, dtype=np.float32)
        for i, project in enumerate(obs.projects_available[:5]):
            base_idx = i * 3
            project_info[base_idx] = float(project.required_investment) / 100000.0  # Normalize
            project_info[base_idx + 1] = float(project.expected_return_pct)
            project_info[base_idx + 2] = float(project.weeks_to_completion) / 20.0  # Normalize
            
        # Bond prices
        bond_prices = np.zeros(5, dtype=np.float32)
        for i, bond_id in enumerate(list(self.debt_backend.bonds.keys())[:5]):
            price = self.debt_backend.get_bond_price(bond_id)
            bond_prices[i] = float(price) if price else 0.0
            
        # News events (one-hot encoding for common event types)
        news_events = np.zeros(10, dtype=np.float32)
        for event in obs.news:
            if event.event_type == "RATE_SHOCK":
                news_events[0] = 1.0
            elif event.event_type == "MARKET_VOLATILITY":
                news_events[1] = 1.0
            elif event.event_type == "PROJECT_COMPLETION":
                news_events[2] = 1.0
                
        return {
            'tick': np.array([obs.tick], dtype=np.int32),
            'cash': np.array([float(obs.cash)], dtype=np.float32),
            'nav': np.array([float(obs.nav)], dtype=np.float32),
            'portfolio_values': portfolio_values,
            'stock_prices': stock_prices,
            'project_info': project_info,
            'bond_prices': bond_prices,
            'news_events': news_events
        }
        
    def _convert_info(self, info) -> Dict[str, Any]:
        """Convert InfoDict to standard dict."""
        return {
            'failed_allocations': len(info.failed_allocations),
            'episode_length': self.episode_length
        }
        
    def render(self):
        """Render the environment."""
        if self.render_mode == "human":
            self._render_human()
        elif self.render_mode == "rgb_array":
            return self._render_rgb_array()
            
    def _render_human(self):
        """Render in human-readable format."""
        if self.current_observation is None:
            return
            
        print(f"\n=== Agent Tycoon - Tick {self.current_observation.tick} ===")
        print(f"Cash: ${self.current_observation.cash:,.2f}")
        print(f"NAV: ${self.current_observation.nav:,.2f}")
        print(f"Portfolio ({len(self.current_observation.portfolio)} assets):")
        for holding in self.current_observation.portfolio:
            print(f"  {holding.asset_type} {holding.identifier}: {holding.quantity:.4f} units = ${holding.current_value:,.2f}")
        
        if self.current_observation.news:
            print("News:")
            for event in self.current_observation.news:
                print(f"  {event.event_type}: {event.description}")
                
    def _render_rgb_array(self):
        """Render as RGB array (placeholder)."""
        # This would typically create a visual representation
        # For now, return a simple placeholder
        return np.zeros((400, 600, 3), dtype=np.uint8)
        
    def close(self):
        """Clean up resources."""
        pass
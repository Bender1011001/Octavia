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
import json
import os
from sklearn.preprocessing import StandardScaler

from models import CapitalAllocationAction, Observation, EquityAlloc, ProjectAlloc, BondAlloc
from engine import SimulationEngine
from ledger import Ledger
from router import AllocationManager
from backends import TradeBackend, ProjectBackend, DebtBackend

# Load dynamic config for bonds and news events
def load_bond_count():
    with open(os.path.join("config", "bonds.json"), "r") as f:
        data = json.load(f)
    return len(data.get("bonds", []))

def load_news_event_types():
    with open(os.path.join("config", "news_events.json"), "r") as f:
        data = json.load(f)
    return data.get("news_events", [])

NUM_BONDS = load_bond_count()
NEWS_EVENT_TYPES = load_news_event_types()
NUM_NEWS_EVENTS = len(NEWS_EVENT_TYPES)

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
        # New: action_type, asset_type, asset_weights (continuous allocation), cognition_cost
        num_assets = num_stocks + num_projects + num_bonds
        self.action_space = spaces.Dict({
            'action_type': spaces.Discrete(2),  # 0: no action, 1: allocate
            'asset_type': spaces.Discrete(3),   # 0: equity, 1: project, 2: bond
            'asset_weights': spaces.Box(low=0.0, high=1.0, shape=(num_assets,), dtype=np.float32),  # Allocation weights
            'cognition_cost': spaces.Box(low=0.0, high=100.0, shape=(1,), dtype=np.float32)
        })
        
        # Determine dynamic observation space sizes
        num_stocks = len(self.trade_backend.stocks)
        num_projects = len(self.project_backend.available_projects)
        num_bonds = NUM_BONDS
        num_project_features = 3  # required_investment, expected_return_pct, weeks_to_completion
        max_portfolio_assets = num_stocks + num_projects + num_bonds
        num_news_events = NUM_NEWS_EVENTS

        # Define observation space
        self.observation_space = spaces.Dict({
            'tick': spaces.Discrete(self.max_episode_length + 1),
            'cash': spaces.Box(low=0.0, high=np.inf, shape=(1,), dtype=np.float32),
            'nav': spaces.Box(low=0.0, high=np.inf, shape=(1,), dtype=np.float32),
            'portfolio_values': spaces.Box(low=0.0, high=np.inf, shape=(max_portfolio_assets,), dtype=np.float32),
            'stock_prices': spaces.Box(low=0.0, high=np.inf, shape=(num_stocks,), dtype=np.float32),
            'project_info': spaces.Box(low=0.0, high=1.0, shape=(num_projects * num_project_features,), dtype=np.float32),
            'bond_prices': spaces.Box(low=0.0, high=np.inf, shape=(num_bonds,), dtype=np.float32),
            'news_events': spaces.Box(low=0.0, high=1.0, shape=(num_news_events,), dtype=np.float32)
        })

        # StandardScaler for observation normalization
        self.scaler = StandardScaler()
        # Fit scaler on initial observation (could be extended to use historical data)
        initial_obs = np.concatenate([
            np.zeros(max_portfolio_assets),
            np.zeros(num_stocks),
            np.zeros(num_projects * num_project_features),
            np.zeros(num_bonds),
            np.zeros(num_news_events)
        ]).reshape(1, -1)
        self.scaler.fit(initial_obs)
        
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
        """Convert gym action to CapitalAllocationAction using continuous asset_weights."""
        action_type = int(action['action_type'].item() if hasattr(action['action_type'], 'item') else action['action_type'])
        if action_type == 0:
            return None

        asset_type = int(action['asset_type'].item() if hasattr(action['asset_type'], 'item') else action['asset_type'])
        asset_weights = action['asset_weights']
        cognition_cost = Decimal(str(float(action['cognition_cost'][0] if hasattr(action['cognition_cost'], '__getitem__') else action['cognition_cost']))).quantize(Decimal('0.01'))

        # Normalize weights to sum to 1
        weights = np.clip(asset_weights, 0, 1)
        if np.sum(weights) > 0:
            weights = weights / np.sum(weights)
        else:
            return None

        # Get asset lists
        tickers = list(self.trade_backend.stocks.keys())
        projects = self.project_backend.get_available_projects()
        bonds = list(self.debt_backend.bonds.keys())
        all_assets = (
            [("EQUITY", t) for t in tickers] +
            [("PROJECT", p.project_id) for p in projects] +
            [("BOND", b) for b in bonds]
        )

        allocations = []
        cash = self.ledger.cash
        for i, (atype, aid) in enumerate(all_assets):
            usd_amount = (cash * Decimal(str(weights[i]))).quantize(Decimal('0.01'))
            if usd_amount > 0:
                if atype == "EQUITY":
                    allocations.append(EquityAlloc(asset_type="EQUITY", ticker=aid, usd=usd_amount))
                elif atype == "PROJECT":
                    allocations.append(ProjectAlloc(asset_type="PROJECT", project_id=aid, usd=usd_amount))
                elif atype == "BOND":
                    allocations.append(BondAlloc(asset_type="BOND", bond_id=aid, usd=usd_amount))

        if not allocations:
            return None

        return CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Gym environment action",
            allocations=allocations,
            cognition_cost=cognition_cost
        )
        
    def _convert_observation(self, obs: Observation) -> Dict[str, np.ndarray]:
        """Convert Observation to gym observation format, with normalization."""
        num_stocks = len(self.trade_backend.stocks)
        num_projects = len(self.project_backend.available_projects)
        num_bonds = NUM_BONDS
        max_portfolio_assets = num_stocks + num_projects + num_bonds
        portfolio_values = np.zeros(max_portfolio_assets, dtype=np.float32)
        for i, holding in enumerate(obs.portfolio[:max_portfolio_assets]):
            portfolio_values[i] = float(holding.current_value)

        stock_prices = np.zeros(num_stocks, dtype=np.float32)
        for i, ticker in enumerate(list(self.trade_backend.stocks.keys())[:num_stocks]):
            price = self.trade_backend.get_price(ticker)
            stock_prices[i] = float(price) if price else 0.0

        num_project_features = 3
        project_info = np.zeros(num_projects * num_project_features, dtype=np.float32)
        for i, project in enumerate(obs.projects_available[:num_projects]):
            base_idx = i * 3
            project_info[base_idx] = float(project.required_investment)
            project_info[base_idx + 1] = float(project.expected_return_pct)
            project_info[base_idx + 2] = float(project.weeks_to_completion)

        bond_prices = np.zeros(num_bonds, dtype=np.float32)
        for i, bond_id in enumerate(list(self.debt_backend.bonds.keys())[:num_bonds]):
            price = self.debt_backend.get_bond_price(bond_id)
            bond_prices[i] = float(price) if price else 0.0

        news_events = np.zeros(NUM_NEWS_EVENTS, dtype=np.float32)
        for event in obs.news:
            if event.event_type in NEWS_EVENT_TYPES:
                idx = NEWS_EVENT_TYPES.index(event.event_type)
                news_events[idx] = 1.0

        # Concatenate for normalization
        obs_vector = np.concatenate([
            portfolio_values,
            stock_prices,
            project_info,
            bond_prices,
            news_events
        ]).reshape(1, -1)
        norm_obs_vector = self.scaler.transform(obs_vector).flatten()

        return {
            'tick': np.array([obs.tick], dtype=np.int32),
            'cash': np.array([float(obs.cash)], dtype=np.float32),
            'nav': np.array([float(obs.nav)], dtype=np.float32),
            'portfolio_values': norm_obs_vector[:max_portfolio_assets],
            'stock_prices': norm_obs_vector[max_portfolio_assets:max_portfolio_assets+num_stocks],
            'project_info': norm_obs_vector[max_portfolio_assets+num_stocks:max_portfolio_assets+num_stocks+num_projects*num_project_features],
            'bond_prices': norm_obs_vector[-(num_bonds+NUM_NEWS_EVENTS):-NUM_NEWS_EVENTS] if NUM_NEWS_EVENTS > 0 else norm_obs_vector[-num_bonds:],
            'news_events': norm_obs_vector[-NUM_NEWS_EVENTS:]
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
        """Render as RGB array: visualize portfolio and prices as colored bars."""
        height, width = 400, 600
        img = np.ones((height, width, 3), dtype=np.uint8) * 255  # White background

        obs = self.current_observation
        if obs is None:
            return img

        # Portfolio composition (top half)
        portfolio = obs.get('portfolio_values', None)
        if portfolio is not None:
            n_assets = len(portfolio)
            max_val = np.max(portfolio) if np.max(portfolio) > 0 else 1
            bar_width = width // max(n_assets, 1)
            for i, val in enumerate(portfolio):
                bar_height = int((val / max_val) * (height // 2 - 20))
                color = (50 + 40 * (i % 5), 100 + 30 * (i % 3), 200 - 30 * (i % 7))
                x0 = i * bar_width
                x1 = x0 + bar_width - 2
                y0 = (height // 2) - bar_height
                y1 = (height // 2)
                img[y0:y1, x0:x1] = color

        # Stock prices (bottom half)
        stock_prices = obs.get('stock_prices', None)
        if stock_prices is not None:
            n_stocks = len(stock_prices)
            max_price = np.max(stock_prices) if np.max(stock_prices) > 0 else 1
            bar_width = width // max(n_stocks, 1)
            for i, price in enumerate(stock_prices):
                bar_height = int((price / max_price) * (height // 2 - 20))
                color = (200 - 30 * (i % 7), 50 + 40 * (i % 5), 100 + 30 * (i % 3))
                x0 = i * bar_width
                x1 = x0 + bar_width - 2
                y0 = height - bar_height
                y1 = height
                img[y0:y1, x0:x1] = color

        return img
        
    def close(self):
        """Clean up resources."""
        pass
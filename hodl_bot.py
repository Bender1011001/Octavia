from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from copy import deepcopy

from models import CapitalAllocationAction, Observation, EquityAlloc


class HODLBot:
    """
    HODL (Hold On for Dear Life) Bot - A baseline strategy that freezes
    its portfolio when shocks occur and does nothing.
    """
    
    def __init__(self, initial_cash: Decimal = Decimal('100000.00')):
        self.initial_cash = initial_cash
        self.is_hodling = False
        self.hodl_start_tick = 0
        self.pre_shock_nav = Decimal('0.00')
        
    def should_hodl(self, observation: Observation) -> bool:
        """Determine if bot should start HODLing based on news events."""
        for event in observation.news:
            if event.event_type in ["RATE_SHOCK", "MARKET_VOLATILITY"]:
                return True
        return False
        
    def get_action(self, observation: Observation) -> Optional[CapitalAllocationAction]:
        """
        Get HODL bot action. Returns None (no action) when HODLing,
        or simple diversification action when not HODLing.
        """
        # Check if we should start HODLing
        if not self.is_hodling and self.should_hodl(observation):
            self.is_hodling = True
            self.hodl_start_tick = observation.tick
            self.pre_shock_nav = observation.nav
            
        # If HODLing, do nothing
        if self.is_hodling:
            return None
            
        # Simple initial diversification strategy (only in first few ticks)
        if observation.tick <= 5 and observation.cash > Decimal('10000.00'):
            # Invest 20% of cash in first available stock
            if observation.tick == 1:
                return CapitalAllocationAction(
                    action_type="ALLOCATE_CAPITAL",
                    comment="HODL Bot initial diversification",
                    allocations=[
                        EquityAlloc(
                            asset_type="EQUITY",
                            ticker="AAPL",
                            usd=observation.cash * Decimal('0.2')
                        )
                    ],
                    cognition_cost=Decimal('0.50')
                )
                
        return None  # Do nothing most of the time


class AdaptabilityMeasurer:
    """
    Measures agent adaptability by comparing performance against HODL bot
    after shock events.
    """
    
    def __init__(self):
        self.shock_events: List[Dict] = []
        self.measurement_window = 5  # Ticks to measure after shock
        
    def record_shock(self, tick: int, shock_type: str, agent_nav: Decimal, hodl_nav: Decimal):
        """Record a shock event for later adaptability measurement."""
        self.shock_events.append({
            'tick': tick,
            'shock_type': shock_type,
            'agent_nav_at_shock': agent_nav,
            'hodl_nav_at_shock': hodl_nav,
            'agent_nav_history': [agent_nav],
            'hodl_nav_history': [hodl_nav],
            'measurement_complete': False
        })
        
    def update_post_shock_performance(self, tick: int, agent_nav: Decimal, hodl_nav: Decimal):
        """Update post-shock performance for ongoing measurements."""
        for shock in self.shock_events:
            if not shock['measurement_complete']:
                ticks_since_shock = tick - shock['tick']
                if 0 < ticks_since_shock <= self.measurement_window:
                    shock['agent_nav_history'].append(agent_nav)
                    shock['hodl_nav_history'].append(hodl_nav)
                elif ticks_since_shock > self.measurement_window:
                    shock['measurement_complete'] = True
                    
    def calculate_adaptability_score(self) -> Dict[str, float]:
        """Calculate overall adaptability score based on completed measurements."""
        if not self.shock_events:
            return {'adaptability_score': 0.0, 'shock_count': 0, 'outperformed_count': 0}
            
        completed_shocks = [s for s in self.shock_events if s['measurement_complete']]
        if not completed_shocks:
            return {'adaptability_score': 0.0, 'shock_count': 0, 'outperformed_count': 0}
            
        outperformed_count = 0
        total_relative_performance = 0.0
        
        for shock in completed_shocks:
            # Calculate performance over measurement window
            agent_start = shock['agent_nav_history'][0]
            agent_end = shock['agent_nav_history'][-1]
            hodl_start = shock['hodl_nav_history'][0]
            hodl_end = shock['hodl_nav_history'][-1]
            
            # Calculate percentage returns
            agent_return = float((agent_end - agent_start) / agent_start) if agent_start > 0 else 0.0
            hodl_return = float((hodl_end - hodl_start) / hodl_start) if hodl_start > 0 else 0.0
            
            # Relative performance
            relative_performance = agent_return - hodl_return
            total_relative_performance += relative_performance
            
            if relative_performance > 0:
                outperformed_count += 1
                
        # Adaptability score: average relative performance + bonus for consistency
        avg_relative_performance = total_relative_performance / len(completed_shocks)
        consistency_bonus = (outperformed_count / len(completed_shocks)) * 0.1
        adaptability_score = avg_relative_performance + consistency_bonus
        
        return {
            'adaptability_score': adaptability_score,
            'shock_count': len(completed_shocks),
            'outperformed_count': outperformed_count,
            'avg_relative_performance': avg_relative_performance,
            'consistency_ratio': outperformed_count / len(completed_shocks)
        }
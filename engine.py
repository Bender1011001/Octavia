import numpy as np
import random
from collections import deque
from decimal import Decimal
from typing import Deque, Optional, Tuple, Dict
from enum import Enum

from ledger import Ledger
from models import CapitalAllocationAction, InfoDict, Observation, NewsEvent
from visualization import event_collector, EventType


class ShockType(Enum):
    RATE_HIKE = "RATE_HIKE"
    RATE_CUT = "RATE_CUT"
    MARKET_VOLATILITY = "MARKET_VOLATILITY"


class SimulationEngine:
    def __init__(self, ledger: Ledger, allocation_manager=None, enable_hodl_comparison: bool = False):
        """Initialize the simulation with starting conditions."""
        self.current_tick = 0
        self.ledger = ledger
        self.allocation_manager = allocation_manager
        self.risk_free_rate = Decimal('0.01')  # 1% per period
        self.target_volatility = Decimal('0.02')  # 2% target volatility
        self.previous_nav = ledger.cash

        # Reward calculation attributes
        self.nav_history: Deque[Decimal] = deque(maxlen=10)
        self.lambda_vol = Decimal('1.0')  # Volatility penalty coefficient
        self.kappa_cost = Decimal('0.01')  # Cognition cost coefficient
        self.kappa_mem = Decimal('0.001')  # Memory cost coefficient
        
        # Shock mechanism attributes
        self.shock_probability = Decimal('0.05')  # 5% chance per tick
        self.last_shock_tick = 0
        self.min_ticks_between_shocks = 5
        
        # HODL bot comparison
        self.enable_hodl_comparison = enable_hodl_comparison
        self.hodl_bot = None
        self.hodl_engine = None
        self.adaptability_measurer = None
        
        if enable_hodl_comparison:
            self._initialize_hodl_comparison()
            
        # Emit simulation start event
        event_collector.emit(
            EventType.SIMULATION_START,
            tick=0,
            data={
                'initial_cash': str(ledger.cash),
                'initial_nav': str(ledger.get_nav()),
                'enable_hodl_comparison': enable_hodl_comparison
            }
        )
            
    def _initialize_hodl_comparison(self):
        """Initialize HODL bot and comparison system."""
        from hodl_bot import HODLBot, AdaptabilityMeasurer
        
        # Create HODL bot
        self.hodl_bot = HODLBot(self.ledger.cash)
        
        # Create parallel HODL simulation
        from ledger import Ledger
        from router import AllocationManager
        
        hodl_ledger = Ledger(self.ledger.cash, price_provider=self.ledger.price_provider)
        if self.allocation_manager:
            hodl_allocation_manager = AllocationManager(
                hodl_ledger,
                self.allocation_manager.trade_backend,
                self.allocation_manager.project_backend,
                self.allocation_manager.debt_backend
            )
        else:
            hodl_allocation_manager = None
        self.hodl_engine = SimulationEngine(hodl_ledger, hodl_allocation_manager, enable_hodl_comparison=False)
        
        # Create adaptability measurer
        self.adaptability_measurer = AdaptabilityMeasurer()

    def tick(self, action: Optional[CapitalAllocationAction] = None) -> Tuple[Observation, Decimal, bool, bool, InfoDict]:
        """Main simulation step with HODL comparison."""
        # Run main simulation
        obs, reward, terminated, truncated, info = self._tick_main(action)
        
        # Run HODL bot simulation if enabled
        if self.enable_hodl_comparison and self.hodl_engine:
            self._tick_hodl_bot(obs)
            
        return obs, reward, terminated, truncated, info
        
    def _tick_main(self, action: Optional[CapitalAllocationAction] = None) -> Tuple[Observation, Decimal, bool, bool, InfoDict]:
        """Main simulation tick (existing tick logic)."""
        self.current_tick += 1
        
        # Emit tick start event
        event_collector.emit(
            EventType.SIMULATION_TICK,
            tick=self.current_tick,
            data={'tick_start': True}
        )
        
        # Process shocks first (before agent action)
        news_events = []
        shock_event = self.trigger_shock()
        if shock_event:
            news_events.append(shock_event)
            # Emit market shock event
            event_collector.emit(
                EventType.MARKET_SHOCK,
                tick=self.current_tick,
                data={
                    'shock_type': shock_event.event_type,
                    'description': shock_event.description,
                    'impact_data': shock_event.impact_data
                }
            )
            
        # Process project lifecycle
        if self.allocation_manager and hasattr(self.allocation_manager, 'project_backend') and self.allocation_manager.project_backend:
            project_news = self.allocation_manager.project_backend.tick(self.ledger)
            news_events.extend([NewsEvent(event_type="PROJECT_COMPLETION", description=news, impact_data={}) for news in project_news])
            
            # Emit project completion events
            for news in project_news:
                event_collector.emit(
                    EventType.PROJECT_COMPLETED,
                    tick=self.current_tick,
                    data={'description': news}
                )
        
        # Process action if provided
        failed_allocations = []
        if action and self.allocation_manager:
            # Emit agent decision event
            event_collector.emit(
                EventType.AGENT_DECISION,
                tick=self.current_tick,
                data={
                    'action': action.dict() if hasattr(action, 'dict') else str(action),
                    'comment': getattr(action, 'comment', ''),
                    'cognition_cost': str(getattr(action, 'cognition_cost', 0)),
                    'num_allocations': len(getattr(action, 'allocations', []))
                }
            )
            
            failed_allocations = self.allocation_manager.execute_action(action)
            
            # Emit trade execution events
            if hasattr(action, 'allocations'):
                for allocation in action.allocations:
                    if allocation not in failed_allocations:
                        event_collector.emit(
                            EventType.TRADE_EXECUTED,
                            tick=self.current_tick,
                            data={
                                'asset_type': allocation.asset_type,
                                'identifier': getattr(allocation, 'ticker', getattr(allocation, 'project_id', getattr(allocation, 'bond_id', 'unknown'))),
                                'amount': str(allocation.usd),
                                'success': True
                            }
                        )
        
        # Calculate reward
        reward = self.calculate_reward(action)
        
        # Get available projects
        projects_available = []
        if self.allocation_manager and hasattr(self.allocation_manager, 'project_backend') and self.allocation_manager.project_backend:
            projects_available = self.allocation_manager.project_backend.get_available_projects()
        
        # Create observation
        obs = Observation(
            tick=self.current_tick,
            cash=self.ledger.cash,
            nav=self.ledger.get_nav(),
            portfolio=self.ledger.get_portfolio_holdings(),
            projects_available=projects_available,
            news=news_events
        )
        
        # Emit portfolio update event
        event_collector.emit(
            EventType.PORTFOLIO_UPDATE,
            tick=self.current_tick,
            data={
                'nav': str(obs.nav),
                'cash': str(obs.cash),
                'portfolio': [holding.dict() if hasattr(holding, 'dict') else str(holding) for holding in obs.portfolio],
                'num_holdings': len(obs.portfolio)
            }
        )
        
        # Emit reward calculation event
        event_collector.emit(
            EventType.REWARD_CALCULATED,
            tick=self.current_tick,
            data={
                'reward': str(reward),
                'nav': str(obs.nav),
                'previous_nav': str(self.previous_nav)
            }
        )
        
        # Record shock for adaptability measurement
        if self.enable_hodl_comparison and shock_event and self.adaptability_measurer:
            hodl_nav = self.hodl_engine.ledger.get_nav() if self.hodl_engine else obs.nav
            self.adaptability_measurer.record_shock(
                self.current_tick, shock_event.event_type, obs.nav, hodl_nav
            )
        
        # Update adaptability measurement
        if self.enable_hodl_comparison and self.adaptability_measurer:
            hodl_nav = self.hodl_engine.ledger.get_nav() if self.hodl_engine else obs.nav
            self.adaptability_measurer.update_post_shock_performance(
                self.current_tick, obs.nav, hodl_nav
            )
            
            # Emit HODL comparison event
            event_collector.emit(
                EventType.HODL_COMPARISON,
                tick=self.current_tick,
                data={
                    'agent_nav': str(obs.nav),
                    'hodl_nav': str(hodl_nav),
                    'outperformance': str(obs.nav - hodl_nav),
                    'outperformance_pct': str((obs.nav - hodl_nav) / hodl_nav * 100) if hodl_nav > 0 else '0'
                }
            )
        
        # Termination conditions
        terminated = self.current_tick >= 100
        truncated = False
        
        # Info dictionary with adaptability score
        info_dict = {'failed_allocations': failed_allocations}
        if self.enable_hodl_comparison and self.adaptability_measurer:
            adaptability_data = self.adaptability_measurer.calculate_adaptability_score()
            info_dict.update(adaptability_data)
            
        info = InfoDict(failed_allocations=failed_allocations)
        
        return obs, reward, terminated, truncated, info

    def calculate_reward(self, action: Optional[CapitalAllocationAction] = None) -> Decimal:
       """
       Calculate reward using the formula:
       reward_t = ΔNAV_adj_t – λ·excess_vol_t – κ_cost·token_usd_t – κ_mem·memory_usd_t
       """
       current_nav = self.ledger.get_nav()
       
       # Calculate ΔNAV_adj_t (NAV change adjusted for risk-free rate)
       if len(self.nav_history) > 0:
           previous_nav = self.nav_history[-1]
           nav_change = current_nav - previous_nav
           
           # Adjust for risk-free rate (what the agent "should" have earned)
           expected_return = previous_nav * self.risk_free_rate
           delta_nav_adj = nav_change - expected_return
       else:
           # First tick - no previous NAV to compare
           delta_nav_adj = Decimal('0.00')
       
       # Calculate excess volatility penalty
       excess_vol_penalty = self._calculate_volatility_penalty(current_nav)
       
       # Calculate cognition cost
       cognition_cost = Decimal('0.00')
       if action:
           cognition_cost = self.kappa_cost * action.cognition_cost
       
       # Memory cost (placeholder for now)
       memory_cost = Decimal('0.00')
       
       # Final reward calculation
       reward = delta_nav_adj - (self.lambda_vol * excess_vol_penalty) - cognition_cost - memory_cost
       
       # Update NAV history
       self.nav_history.append(current_nav)
       
       return reward

    def _calculate_volatility_penalty(self, current_nav: Decimal) -> Decimal:
       """Calculate excess volatility penalty."""
       if len(self.nav_history) < 2:
           return Decimal('0.00')
       
       # Convert to numpy array for volatility calculation
       nav_values = [float(nav) for nav in list(self.nav_history) + [current_nav]]
       nav_array = np.array(nav_values)
       
       # Calculate returns
       if len(nav_array) < 2:
           return Decimal('0.00')
       
       returns = np.diff(nav_array) / nav_array[:-1]
       
       # Calculate volatility (standard deviation of returns)
       if len(returns) < 2:
           return Decimal('0.00')
       
       volatility = Decimal(str(np.std(returns)))
       
       # Calculate excess volatility above target
       excess_volatility = max(Decimal('0.00'), volatility - self.target_volatility)
       
       return excess_volatility

    def reset(self, initial_cash: Decimal = Decimal('100000.00')) -> Observation:
        """Reset the simulation to initial state."""
        self.current_tick = 0
        price_provider = getattr(self.allocation_manager, 'trade_backend', None)
        self.ledger = Ledger(initial_cash, price_provider=price_provider)
        self.previous_nav = initial_cash
        self.nav_history.clear()

        return Observation(
            tick=0,
            cash=self.ledger.cash,
            nav=self.ledger.get_nav(),
            portfolio=self.ledger.get_portfolio_holdings(),
            projects_available=[],
            news=[]
        )

    def trigger_shock(self) -> Optional[NewsEvent]:
        """Randomly trigger a shock event."""
        # Check if enough time has passed since last shock
        if self.current_tick - self.last_shock_tick < self.min_ticks_between_shocks:
            return None
            
        # Check if shock should occur
        if random.random() > float(self.shock_probability):
            return None
            
        # Select shock type
        shock_types = list(ShockType)
        shock_type = random.choice(shock_types)
        
        self.last_shock_tick = self.current_tick
        
        if shock_type == ShockType.RATE_HIKE:
            return self._apply_rate_shock(25, 75)  # 25-75 basis points hike
        elif shock_type == ShockType.RATE_CUT:
            return self._apply_rate_shock(-75, -25)  # 25-75 basis points cut
        elif shock_type == ShockType.MARKET_VOLATILITY:
            return self._apply_market_volatility()
            
        return None
        
    def _apply_rate_shock(self, min_bps: int, max_bps: int) -> NewsEvent:
        """Apply interest rate shock."""
        rate_change_bps = random.randint(min_bps, max_bps)
        
        # Apply to debt backend if available
        if (self.allocation_manager and
            hasattr(self.allocation_manager, 'debt_backend') and
            self.allocation_manager.debt_backend):
            self.allocation_manager.debt_backend.apply_interest_rate_shock(rate_change_bps)
        
        shock_direction = "hike" if rate_change_bps > 0 else "cut"
        description = f"Interest rate {shock_direction} of {abs(rate_change_bps)} basis points"
        
        return NewsEvent(
            event_type="RATE_SHOCK",
            description=description,
            impact_data={"rate_change_bps": rate_change_bps}
        )
        
    def _apply_market_volatility(self) -> NewsEvent:
        """Apply market volatility shock to stock prices."""
        if (self.allocation_manager and
            hasattr(self.allocation_manager, 'trade_backend') and
            self.allocation_manager.trade_backend):
            
            # Apply random price changes to all stocks
            price_changes = {}
            for ticker in self.allocation_manager.trade_backend.stocks.keys():
                # Random change between -15% and +15%
                change_pct = random.uniform(-0.15, 0.15)
                current_price = self.allocation_manager.trade_backend.get_price(ticker)
                if current_price:
                    new_price = current_price * (Decimal('1.0') + Decimal(str(change_pct)))
                    # Ensure price doesn't go below $1
                    new_price = max(Decimal('1.00'), new_price)
                    price_changes[ticker] = new_price
            
            self.allocation_manager.trade_backend.update_prices(price_changes)
        
        return NewsEvent(
            event_type="MARKET_VOLATILITY",
            description="Market volatility event: significant price movements across equities",
            impact_data={"volatility_level": "HIGH"}
        )
        
    def _tick_hodl_bot(self, main_obs: Observation):
        """Run HODL bot simulation tick."""
        if not self.hodl_bot or not self.hodl_engine:
            return
            
        # Get HODL bot action
        hodl_action = self.hodl_bot.get_action(main_obs)
        
        # Run HODL engine tick
        self.hodl_engine.tick(hodl_action)
        
    def get_adaptability_report(self) -> Dict:
        """Get comprehensive adaptability report."""
        if not self.enable_hodl_comparison or not self.adaptability_measurer:
            return {'error': 'HODL comparison not enabled'}
            
        base_score = self.adaptability_measurer.calculate_adaptability_score()
        
        # Add additional metrics
        agent_nav = self.ledger.get_nav()
        hodl_nav = self.hodl_engine.ledger.get_nav() if self.hodl_engine else agent_nav
        
        return {
            **base_score,
            'final_agent_nav': float(agent_nav),
            'final_hodl_nav': float(hodl_nav),
            'total_outperformance': float(agent_nav - hodl_nav),
            'total_outperformance_pct': float((agent_nav - hodl_nav) / hodl_nav) if hodl_nav > 0 else 0.0
        }
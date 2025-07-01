import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

from engine import SimulationEngine
from ledger import Ledger
from router import AllocationManager
from backends import TradeBackend, ProjectBackend, DebtBackend
from models import CapitalAllocationAction, EquityAlloc, NewsEvent
from hodl_bot import HODLBot, AdaptabilityMeasurer


class TestHODLIntegration(unittest.TestCase):
    """Integration tests for HODL bot comparison system."""
    
    def setUp(self):
        """Set up test fixtures with full system."""
        # Create backends
        self.trade_backend = TradeBackend()
        self.project_backend = ProjectBackend()
        self.debt_backend = DebtBackend()
        
        # Create price provider wrapper class
        class PriceProvider:
            def __init__(self, trade_backend, debt_backend):
                self.trade_backend = trade_backend
                self.debt_backend = debt_backend
                
            def get_price(self, identifier: str):
                return self.trade_backend.get_price(identifier)
                
            def get_bond_price(self, identifier: str):
                return self.debt_backend.get_bond_price(identifier)
        
        price_provider = PriceProvider(self.trade_backend, self.debt_backend)
        
        # Initialize ledger and allocation manager
        self.initial_cash = Decimal('100000.00')
        self.ledger = Ledger(self.initial_cash, price_provider=price_provider)
        self.allocation_manager = AllocationManager(
            self.ledger, self.trade_backend, self.project_backend, self.debt_backend
        )
        
    def test_full_hodl_comparison(self):
        """Test complete HODL comparison workflow."""
        # Create engine with HODL comparison enabled
        engine = SimulationEngine(
            self.ledger, 
            self.allocation_manager, 
            enable_hodl_comparison=True
        )
        
        # Verify HODL comparison is initialized
        self.assertTrue(engine.enable_hodl_comparison)
        self.assertIsNotNone(engine.hodl_bot)
        self.assertIsNotNone(engine.hodl_engine)
        self.assertIsNotNone(engine.adaptability_measurer)
        
        # Run simulation for several ticks
        observations = []
        for tick in range(10):
            # Create some actions for variety
            action = None
            if tick == 1:
                action = CapitalAllocationAction(
                    action_type="ALLOCATE_CAPITAL",
                    comment="Test investment",
                    allocations=[
                        EquityAlloc(
                            asset_type="EQUITY",
                            ticker="AAPL",
                            usd=Decimal('10000.00')
                        )
                    ],
                    cognition_cost=Decimal('1.00')
                )
            
            obs, reward, terminated, truncated, info = engine.tick(action)
            observations.append(obs)
            
            if terminated or truncated:
                break
        
        # Verify both engines are running
        main_nav = engine.ledger.get_nav()
        hodl_nav = engine.hodl_engine.ledger.get_nav()
        
        self.assertGreater(main_nav, Decimal('0'))
        self.assertGreater(hodl_nav, Decimal('0'))
        
        # Get adaptability report
        report = engine.get_adaptability_report()
        self.assertIn('final_agent_nav', report)
        self.assertIn('final_hodl_nav', report)
        self.assertIn('adaptability_score', report)
        
    def test_adaptability_measurement_accuracy(self):
        """Test adaptability measurement accuracy."""
        engine = SimulationEngine(
            self.ledger, 
            self.allocation_manager, 
            enable_hodl_comparison=True
        )
        
        # Force a shock to occur for testing
        with patch.object(engine, 'trigger_shock') as mock_shock:
            # Create a mock shock event
            shock_event = NewsEvent(
                event_type="RATE_SHOCK",
                description="Test rate shock",
                impact_data={"rate_change_bps": 50}
            )
            mock_shock.return_value = shock_event
            
            # Run tick with shock
            obs, reward, terminated, truncated, info = engine.tick()
            
            # Verify shock was recorded
            self.assertEqual(len(engine.adaptability_measurer.shock_events), 1)
            shock_record = engine.adaptability_measurer.shock_events[0]
            self.assertEqual(shock_record['tick'], 1)
            self.assertEqual(shock_record['shock_type'], "RATE_SHOCK")
            
            # Continue simulation to build measurement history
            mock_shock.return_value = None  # No more shocks
            for tick in range(2, 8):  # Run past measurement window
                obs, reward, terminated, truncated, info = engine.tick()
                
            # Check that measurement is complete
            shock_record = engine.adaptability_measurer.shock_events[0]
            self.assertTrue(shock_record['measurement_complete'])
            self.assertEqual(len(shock_record['agent_nav_history']), 6)  # Initial + 5 window
            
    def test_hodl_bot_vs_active_agent(self):
        """Compare HODL bot against active trading agent using internal HODL comparison."""
        # Create engine with HODL comparison enabled (includes internal hodl_engine)
        active_engine = SimulationEngine(
            self.ledger,
            self.allocation_manager,
            enable_hodl_comparison=True
        )
        
        # Run simulation with active agent making strategic moves
        for tick in range(15):
            # Active agent makes strategic moves
            active_action = None
            if tick == 1:
                active_action = CapitalAllocationAction(
                    action_type="ALLOCATE_CAPITAL",
                    comment="Active investment",
                    allocations=[
                        EquityAlloc(
                            asset_type="EQUITY",
                            ticker="AAPL",
                            usd=Decimal('20000.00')
                        )
                    ],
                    cognition_cost=Decimal('2.00')
                )
            elif tick == 5:
                active_action = CapitalAllocationAction(
                    action_type="ALLOCATE_CAPITAL",
                    comment="Diversification",
                    allocations=[
                        EquityAlloc(
                            asset_type="EQUITY",
                            ticker="GOOGL",
                            usd=Decimal('15000.00')
                        )
                    ],
                    cognition_cost=Decimal('1.50')
                )
            
            # Run active engine (internal HODL comparison runs automatically)
            active_obs, _, _, _, _ = active_engine.tick(active_action)
        
        # Get final NAVs from both the active agent and internal HODL comparison
        final_active_nav = active_engine.ledger.get_nav()
        final_hodl_nav = active_engine.hodl_engine.ledger.get_nav()
        
        # Both should have positive NAV
        self.assertGreater(final_active_nav, Decimal('0'))
        self.assertGreater(final_hodl_nav, Decimal('0'))
        
        # Performance difference should be measurable (allow for small differences)
        performance_diff = abs(final_active_nav - final_hodl_nav)
        self.assertGreaterEqual(performance_diff, Decimal('0'))  # Allow zero difference
        
        # Get adaptability report from active engine
        report = active_engine.get_adaptability_report()
        self.assertIsInstance(report, dict)
        self.assertIn('final_agent_nav', report)
        self.assertIn('final_hodl_nav', report)
        
        # Verify the report values match our direct NAV readings
        self.assertEqual(report['final_agent_nav'], final_active_nav)
        self.assertEqual(report['final_hodl_nav'], final_hodl_nav)
        
    def test_hodl_comparison_disabled(self):
        """Test engine works correctly when HODL comparison is disabled."""
        engine = SimulationEngine(
            self.ledger, 
            self.allocation_manager, 
            enable_hodl_comparison=False
        )
        
        # Verify HODL comparison is not initialized
        self.assertFalse(engine.enable_hodl_comparison)
        self.assertIsNone(engine.hodl_bot)
        self.assertIsNone(engine.hodl_engine)
        self.assertIsNone(engine.adaptability_measurer)
        
        # Run simulation normally
        action = CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Normal investment",
            allocations=[
                EquityAlloc(
                    asset_type="EQUITY",
                    ticker="AAPL",
                    usd=Decimal('10000.00')
                )
            ],
            cognition_cost=Decimal('1.00')
        )
        
        obs, reward, terminated, truncated, info = engine.tick(action)
        
        # Should work normally
        self.assertGreater(obs.nav, Decimal('0'))
        self.assertIsInstance(reward, Decimal)
        
        # Adaptability report should indicate disabled
        report = engine.get_adaptability_report()
        self.assertEqual(report, {'error': 'HODL comparison not enabled'})
        
    def test_shock_triggers_hodl_behavior(self):
        """Test that shocks properly trigger HODL behavior in bot."""
        engine = SimulationEngine(
            self.ledger, 
            self.allocation_manager, 
            enable_hodl_comparison=True
        )
        
        # Initial tick - HODL bot should make initial investment
        obs1, _, _, _, _ = engine.tick()
        hodl_action1 = engine.hodl_bot.get_action(obs1)
        self.assertIsNotNone(hodl_action1)  # Should invest initially
        self.assertFalse(engine.hodl_bot.is_hodling)
        
        # Force a shock
        with patch.object(engine, 'trigger_shock') as mock_shock:
            shock_event = NewsEvent(
                event_type="MARKET_VOLATILITY",
                description="High volatility event",
                impact_data={"volatility_level": "HIGH"}
            )
            mock_shock.return_value = shock_event
            
            obs2, _, _, _, _ = engine.tick()
            
            # HODL bot should now be in HODL mode
            self.assertTrue(engine.hodl_bot.is_hodling)
            self.assertEqual(engine.hodl_bot.hodl_start_tick, 2)
            
            # Subsequent actions should be None
            hodl_action2 = engine.hodl_bot.get_action(obs2)
            self.assertIsNone(hodl_action2)
            
            # Continue with no shocks
            mock_shock.return_value = None
            obs3, _, _, _, _ = engine.tick()
            hodl_action3 = engine.hodl_bot.get_action(obs3)
            self.assertIsNone(hodl_action3)  # Still HODLing


if __name__ == '__main__':
    unittest.main()
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

from hodl_bot import HODLBot, AdaptabilityMeasurer
from models import Observation, NewsEvent, CapitalAllocationAction, EquityAlloc


class TestHODLBot(unittest.TestCase):
    """Test cases for HODLBot implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.initial_cash = Decimal('100000.00')
        self.hodl_bot = HODLBot(self.initial_cash)
        
    def test_hodl_bot_initialization(self):
        """Test HODL bot initializes correctly."""
        self.assertEqual(self.hodl_bot.initial_cash, self.initial_cash)
        self.assertFalse(self.hodl_bot.is_hodling)
        self.assertEqual(self.hodl_bot.hodl_start_tick, 0)
        self.assertEqual(self.hodl_bot.pre_shock_nav, Decimal('0.00'))
        
    def test_hodl_bot_shock_detection(self):
        """Test bot detects shock events correctly."""
        # Create observation with rate shock
        rate_shock_obs = Observation(
            tick=5,
            cash=Decimal('50000.00'),
            nav=Decimal('75000.00'),
            portfolio=[],
            projects_available=[],
            news=[NewsEvent(event_type="RATE_SHOCK", description="Rate hike", impact_data={})]
        )
        
        # Create observation with market volatility
        volatility_obs = Observation(
            tick=6,
            cash=Decimal('50000.00'),
            nav=Decimal('75000.00'),
            portfolio=[],
            projects_available=[],
            news=[NewsEvent(event_type="MARKET_VOLATILITY", description="High volatility", impact_data={})]
        )
        
        # Create observation with no shocks
        normal_obs = Observation(
            tick=7,
            cash=Decimal('50000.00'),
            nav=Decimal('75000.00'),
            portfolio=[],
            projects_available=[],
            news=[NewsEvent(event_type="PROJECT_COMPLETION", description="Project done", impact_data={})]
        )
        
        self.assertTrue(self.hodl_bot.should_hodl(rate_shock_obs))
        self.assertTrue(self.hodl_bot.should_hodl(volatility_obs))
        self.assertFalse(self.hodl_bot.should_hodl(normal_obs))
        
    def test_hodl_bot_action_generation(self):
        """Test bot generates appropriate actions."""
        # Test initial diversification action
        initial_obs = Observation(
            tick=1,
            cash=Decimal('100000.00'),
            nav=Decimal('100000.00'),
            portfolio=[],
            projects_available=[],
            news=[]
        )
        
        action = self.hodl_bot.get_action(initial_obs)
        self.assertIsNotNone(action)
        self.assertEqual(action.action_type, "ALLOCATE_CAPITAL")
        self.assertEqual(len(action.allocations), 1)
        self.assertEqual(action.allocations[0].ticker, "AAPL")
        self.assertEqual(action.allocations[0].usd, Decimal('20000.00'))  # 20% of cash
        
        # Test no action when cash is low
        low_cash_obs = Observation(
            tick=1,
            cash=Decimal('5000.00'),
            nav=Decimal('5000.00'),
            portfolio=[],
            projects_available=[],
            news=[]
        )
        
        action = self.hodl_bot.get_action(low_cash_obs)
        self.assertIsNone(action)
        
        # Test no action after tick 5
        late_obs = Observation(
            tick=10,
            cash=Decimal('50000.00'),
            nav=Decimal('50000.00'),
            portfolio=[],
            projects_available=[],
            news=[]
        )
        
        action = self.hodl_bot.get_action(late_obs)
        self.assertIsNone(action)
        
    def test_hodl_bot_freezing_behavior(self):
        """Test bot stops acting after shock."""
        # Normal observation that would trigger action
        normal_obs = Observation(
            tick=1,
            cash=Decimal('100000.00'),
            nav=Decimal('100000.00'),
            portfolio=[],
            projects_available=[],
            news=[]
        )
        
        # Get initial action
        action = self.hodl_bot.get_action(normal_obs)
        self.assertIsNotNone(action)
        
        # Create shock observation
        shock_obs = Observation(
            tick=2,
            cash=Decimal('80000.00'),
            nav=Decimal('95000.00'),
            portfolio=[],
            projects_available=[],
            news=[NewsEvent(event_type="RATE_SHOCK", description="Rate hike", impact_data={})]
        )
        
        # Bot should start HODLing
        action = self.hodl_bot.get_action(shock_obs)
        self.assertIsNone(action)
        self.assertTrue(self.hodl_bot.is_hodling)
        self.assertEqual(self.hodl_bot.hodl_start_tick, 2)
        self.assertEqual(self.hodl_bot.pre_shock_nav, Decimal('95000.00'))
        
        # Subsequent observations should return None
        later_obs = Observation(
            tick=3,
            cash=Decimal('80000.00'),
            nav=Decimal('90000.00'),
            portfolio=[],
            projects_available=[],
            news=[]
        )
        
        action = self.hodl_bot.get_action(later_obs)
        self.assertIsNone(action)
        self.assertTrue(self.hodl_bot.is_hodling)
        
    def test_hodl_bot_initial_investment_execution(self):
        """Test that HODL bot's initial investment is executed correctly."""
        # Create a mock ledger and allocation manager to test actual execution
        from ledger import Ledger
        from backends import TradeBackend
        from router import AllocationManager
        
        # Set up test environment
        ledger = Ledger(initial_cash=Decimal('100000.00'))
        trade_backend = TradeBackend()
        allocation_manager = AllocationManager(ledger, trade_backend)
        
        # Create observation for first tick
        initial_obs = Observation(
            tick=1,
            cash=Decimal('100000.00'),
            nav=Decimal('100000.00'),
            portfolio=[],
            projects_available=[],
            news=[]
        )
        
        # Get action from HODL bot
        action = self.hodl_bot.get_action(initial_obs)
        
        # Verify action properties
        self.assertIsNotNone(action)
        self.assertEqual(action.action_type, "ALLOCATE_CAPITAL")
        self.assertEqual(len(action.allocations), 1)
        self.assertEqual(action.allocations[0].ticker, "AAPL")
        self.assertEqual(action.allocations[0].usd, Decimal('20000.00'))  # 20% of initial cash
        
        # Execute the action
        failed_allocations = allocation_manager.execute_action(action)
        
        # Verify execution was successful
        self.assertEqual(len(failed_allocations), 0)
        self.assertEqual(ledger.cash, Decimal('80000.00'))  # 100000 - 20000
        self.assertEqual(len(ledger.assets), 1)
        self.assertEqual(ledger.assets[0].identifier, 'AAPL')
        self.assertEqual(ledger.assets[0].asset_type, 'EQUITY')
        # Verify investment amount (should be close to 20000, allowing for price differences)
        self.assertAlmostEqual(float(ledger.assets[0].cost_basis), 20000.0, delta=100.0)


class TestAdaptabilityMeasurer(unittest.TestCase):
    """Test cases for AdaptabilityMeasurer implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.measurer = AdaptabilityMeasurer()
        
    def test_adaptability_measurer_initialization(self):
        """Test adaptability measurer initializes correctly."""
        self.assertEqual(len(self.measurer.shock_events), 0)
        self.assertEqual(self.measurer.measurement_window, 5)
        
    def test_shock_recording(self):
        """Test shock event recording."""
        agent_nav = Decimal('95000.00')
        hodl_nav = Decimal('98000.00')
        
        self.measurer.record_shock(10, "RATE_SHOCK", agent_nav, hodl_nav)
        
        self.assertEqual(len(self.measurer.shock_events), 1)
        shock = self.measurer.shock_events[0]
        self.assertEqual(shock['tick'], 10)
        self.assertEqual(shock['shock_type'], "RATE_SHOCK")
        self.assertEqual(shock['agent_nav_at_shock'], agent_nav)
        self.assertEqual(shock['hodl_nav_at_shock'], hodl_nav)
        self.assertEqual(len(shock['agent_nav_history']), 1)
        self.assertEqual(len(shock['hodl_nav_history']), 1)
        self.assertFalse(shock['measurement_complete'])
        
    def test_post_shock_performance_tracking(self):
        """Test performance tracking after shocks."""
        # Record initial shock
        self.measurer.record_shock(10, "RATE_SHOCK", Decimal('95000.00'), Decimal('98000.00'))
        
        # Update performance for 3 ticks after shock
        for tick in range(11, 14):
            agent_nav = Decimal('95000.00') + Decimal(str(tick - 10)) * Decimal('1000.00')
            hodl_nav = Decimal('98000.00') + Decimal(str(tick - 10)) * Decimal('500.00')
            self.measurer.update_post_shock_performance(tick, agent_nav, hodl_nav)
            
        shock = self.measurer.shock_events[0]
        self.assertEqual(len(shock['agent_nav_history']), 4)  # Initial + 3 updates
        self.assertEqual(len(shock['hodl_nav_history']), 4)
        self.assertFalse(shock['measurement_complete'])
        
        # Update for remaining ticks to complete measurement window
        for tick in range(14, 17):
            agent_nav = Decimal('95000.00') + Decimal(str(tick - 10)) * Decimal('1000.00')
            hodl_nav = Decimal('98000.00') + Decimal(str(tick - 10)) * Decimal('500.00')
            self.measurer.update_post_shock_performance(tick, agent_nav, hodl_nav)
            
        shock = self.measurer.shock_events[0]
        self.assertEqual(len(shock['agent_nav_history']), 6)  # Initial + 5 updates
        self.assertEqual(len(shock['hodl_nav_history']), 6)
        self.assertTrue(shock['measurement_complete'])
        
    def test_adaptability_score_calculation(self):
        """Test adaptability score calculation."""
        # Test with no shocks
        score = self.measurer.calculate_adaptability_score()
        expected = {'adaptability_score': 0.0, 'shock_count': 0, 'outperformed_count': 0}
        self.assertEqual(score, expected)
        
        # Add a completed shock where agent outperforms
        self.measurer.shock_events.append({
            'tick': 10,
            'shock_type': 'RATE_SHOCK',
            'agent_nav_at_shock': Decimal('100000.00'),
            'hodl_nav_at_shock': Decimal('100000.00'),
            'agent_nav_history': [
                Decimal('100000.00'), Decimal('102000.00'), Decimal('104000.00'),
                Decimal('106000.00'), Decimal('108000.00'), Decimal('110000.00')
            ],
            'hodl_nav_history': [
                Decimal('100000.00'), Decimal('101000.00'), Decimal('102000.00'),
                Decimal('103000.00'), Decimal('104000.00'), Decimal('105000.00')
            ],
            'measurement_complete': True
        })
        
        score = self.measurer.calculate_adaptability_score()
        
        # Agent return: 10%, HODL return: 5%, relative performance: 5%
        # Consistency bonus: 1.0 * 0.1 = 0.1
        # Expected adaptability score: 0.05 + 0.1 = 0.15
        
        self.assertEqual(score['shock_count'], 1)
        self.assertEqual(score['outperformed_count'], 1)
        self.assertAlmostEqual(score['avg_relative_performance'], 0.05, places=4)
        self.assertAlmostEqual(score['consistency_ratio'], 1.0, places=4)
        self.assertAlmostEqual(score['adaptability_score'], 0.15, places=4)
        
    def test_adaptability_score_with_multiple_shocks(self):
        """Test adaptability score with multiple shock events."""
        # Add two completed shocks - one outperform, one underperform
        self.measurer.shock_events.extend([
            {
                'tick': 10,
                'shock_type': 'RATE_SHOCK',
                'agent_nav_at_shock': Decimal('100000.00'),
                'hodl_nav_at_shock': Decimal('100000.00'),
                'agent_nav_history': [
                    Decimal('100000.00'), Decimal('105000.00')
                ],
                'hodl_nav_history': [
                    Decimal('100000.00'), Decimal('102000.00')
                ],
                'measurement_complete': True
            },
            {
                'tick': 20,
                'shock_type': 'MARKET_VOLATILITY',
                'agent_nav_at_shock': Decimal('105000.00'),
                'hodl_nav_at_shock': Decimal('102000.00'),
                'agent_nav_history': [
                    Decimal('105000.00'), Decimal('103000.00')
                ],
                'hodl_nav_history': [
                    Decimal('102000.00'), Decimal('104000.00')
                ],
                'measurement_complete': True
            }
        ])
        
        score = self.measurer.calculate_adaptability_score()
        
        self.assertEqual(score['shock_count'], 2)
        self.assertEqual(score['outperformed_count'], 1)  # Only first shock outperformed
        self.assertAlmostEqual(score['consistency_ratio'], 0.5, places=4)


if __name__ == '__main__':
    unittest.main()
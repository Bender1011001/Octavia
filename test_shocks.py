"""Unit tests for the shock system in SimulationEngine."""

import pytest
import random
from decimal import Decimal
from unittest.mock import Mock, patch
from engine import SimulationEngine, ShockType
from ledger import Ledger
from backends import TradeBackend, DebtBackend
from router import AllocationManager
from models import NewsEvent


class TestShockSystem:
    """Test cases for the shock system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.ledger = Ledger(Decimal('100000.00'))
        self.trade_backend = TradeBackend()
        self.debt_backend = DebtBackend()
        self.allocation_manager = AllocationManager(
            self.ledger, 
            self.trade_backend, 
            debt_backend=self.debt_backend
        )
        self.engine = SimulationEngine(self.ledger, self.allocation_manager)
        
    def test_shock_probability_mechanism(self):
        """Test shock triggering mechanism."""
        # Set high probability for testing
        self.engine.shock_probability = Decimal('1.0')  # 100% chance
        self.engine.min_ticks_between_shocks = 0  # No cooldown
        
        # Should trigger a shock
        shock_event = self.engine.trigger_shock()
        assert shock_event is not None
        assert isinstance(shock_event, NewsEvent)
        
    def test_shock_probability_low_chance(self):
        """Test shock with low probability."""
        # Set very low probability
        self.engine.shock_probability = Decimal('0.0')  # 0% chance
        
        # Should not trigger a shock
        shock_event = self.engine.trigger_shock()
        assert shock_event is None
        
    def test_shock_cooldown_mechanism(self):
        """Test minimum time between shocks."""
        self.engine.shock_probability = Decimal('1.0')  # 100% chance
        self.engine.min_ticks_between_shocks = 5
        self.engine.current_tick = 10
        self.engine.last_shock_tick = 8  # Recent shock
        
        # Should not trigger due to cooldown
        shock_event = self.engine.trigger_shock()
        assert shock_event is None
        
        # Move forward enough ticks
        self.engine.current_tick = 15
        
        # Should trigger now
        shock_event = self.engine.trigger_shock()
        assert shock_event is not None
        
    def test_rate_hike_shock(self):
        """Test rate hike shock effects."""
        # Force a rate hike shock by calling the method directly
        initial_rate = self.debt_backend.base_interest_rate
        initial_prices = {bond_id: bond.current_price for bond_id, bond in self.debt_backend.bonds.items()}
        
        shock_event = self.engine._apply_rate_shock(25, 75)
        
        assert shock_event is not None
        assert shock_event.event_type == "RATE_SHOCK"
        assert "hike" in shock_event.description
        assert 25 <= shock_event.impact_data["rate_change_bps"] <= 75
        
        # Check rate increased
        assert self.debt_backend.base_interest_rate > initial_rate
        
        # Check bond prices changed
        for bond_id, bond in self.debt_backend.bonds.items():
            assert bond.current_price != initial_prices[bond_id]
                
    def test_rate_cut_shock(self):
        """Test rate cut shock effects."""
        # Force a rate cut shock by calling the method directly
        initial_rate = self.debt_backend.base_interest_rate
        
        shock_event = self.engine._apply_rate_shock(-75, -25)
        
        assert shock_event is not None
        assert shock_event.event_type == "RATE_SHOCK"
        assert "cut" in shock_event.description
        assert -75 <= shock_event.impact_data["rate_change_bps"] <= -25
        
        # Check rate decreased
        assert self.debt_backend.base_interest_rate < initial_rate
            
    def test_market_volatility_shock(self):
        """Test market volatility shock effects."""
        # Force a market volatility shock by calling the method directly
        initial_prices = {ticker: stock.price for ticker, stock in self.trade_backend.stocks.items()}
        
        shock_event = self.engine._apply_market_volatility()
        
        assert shock_event is not None
        assert shock_event.event_type == "MARKET_VOLATILITY"
        assert "volatility" in shock_event.description.lower()
        assert shock_event.impact_data["volatility_level"] == "HIGH"
        
        # Check stock prices changed (at least some should change due to random nature)
        prices_changed = False
        for ticker, stock in self.trade_backend.stocks.items():
            if stock.price != initial_prices[ticker]:
                prices_changed = True
            # Ensure price didn't go below $1
            assert stock.price >= Decimal('1.00')
        
        # At least some prices should have changed
        assert prices_changed
            
    def test_shock_news_events_format(self):
        """Test shock events generate proper news format."""
        self.engine.shock_probability = Decimal('1.0')
        self.engine.min_ticks_between_shocks = 0
        
        with patch('engine.random.choice') as mock_choice, \
             patch('engine.random.random', return_value=0.01), \
             patch('engine.random.randint', return_value=75):
            
            mock_choice.return_value = ShockType.RATE_HIKE
            
            shock_event = self.engine.trigger_shock()
            
            # Verify NewsEvent structure
            assert hasattr(shock_event, 'event_type')
            assert hasattr(shock_event, 'description')
            assert hasattr(shock_event, 'impact_data')
            
            assert isinstance(shock_event.event_type, str)
            assert isinstance(shock_event.description, str)
            assert isinstance(shock_event.impact_data, dict)
            
    def test_shock_integration_with_tick(self):
        """Test shock integration with main tick method."""
        self.engine.shock_probability = Decimal('1.0')  # Always trigger
        self.engine.min_ticks_between_shocks = 0
        
        with patch('engine.random.choice') as mock_choice, \
             patch('engine.random.random', return_value=0.01), \
             patch('engine.random.randint', return_value=100):
            
            mock_choice.return_value = ShockType.RATE_HIKE
            
            obs, reward, terminated, truncated, info = self.engine.tick()
            
            # Check that news events include shock
            assert len(obs.news) > 0
            shock_news = [news for news in obs.news if news.event_type == "RATE_SHOCK"]
            assert len(shock_news) == 1
            
    def test_shock_without_backends(self):
        """Test shock behavior when backends are not available."""
        # Create engine without allocation manager
        engine = SimulationEngine(self.ledger)
        engine.shock_probability = Decimal('1.0')
        engine.min_ticks_between_shocks = 0
        
        with patch('engine.random.choice') as mock_choice, \
             patch('engine.random.random', return_value=0.01), \
             patch('engine.random.randint', return_value=50):
            
            mock_choice.return_value = ShockType.RATE_HIKE
            
            # Should still generate news event even without backends
            shock_event = engine.trigger_shock()
            assert shock_event is not None
            assert shock_event.event_type == "RATE_SHOCK"
            
    def test_multiple_shock_types(self):
        """Test all shock types can be triggered."""
        self.engine.shock_probability = Decimal('1.0')
        self.engine.min_ticks_between_shocks = 0
        
        shock_types_triggered = set()
        
        # Try to trigger each shock type
        for shock_type in ShockType:
            with patch('engine.random.choice', return_value=shock_type), \
                 patch('engine.random.random', return_value=0.01), \
                 patch('engine.random.randint', return_value=50), \
                 patch('engine.random.uniform', return_value=0.05):
                
                shock_event = self.engine.trigger_shock()
                assert shock_event is not None
                shock_types_triggered.add(shock_event.event_type)
                
        # Should have triggered different types of shocks
        assert len(shock_types_triggered) > 0
        
    def test_shock_rate_bounds(self):
        """Test shock rate changes are within expected bounds."""
        self.engine.shock_probability = Decimal('1.0')
        self.engine.min_ticks_between_shocks = 0
        
        with patch('engine.random.choice') as mock_choice, \
             patch('engine.random.random', return_value=0.01):
            
            # Test rate hike bounds
            mock_choice.return_value = ShockType.RATE_HIKE
            with patch('engine.random.randint', return_value=75) as mock_randint:
                shock_event = self.engine.trigger_shock()
                mock_randint.assert_called_with(25, 75)
                assert shock_event.impact_data["rate_change_bps"] == 75
                
            # Test rate cut bounds
            mock_choice.return_value = ShockType.RATE_CUT
            with patch('engine.random.randint', return_value=-50) as mock_randint:
                shock_event = self.engine.trigger_shock()
                mock_randint.assert_called_with(-75, -25)
                assert shock_event.impact_data["rate_change_bps"] == -50
                
    def test_market_volatility_price_bounds(self):
        """Test market volatility respects price bounds."""
        self.engine.shock_probability = Decimal('1.0')
        self.engine.min_ticks_between_shocks = 0
        
        # Set a stock to very low price
        self.trade_backend.stocks['TEST'] = Mock()
        self.trade_backend.stocks['TEST'].price = Decimal('0.50')
        
        with patch('engine.random.choice', return_value=ShockType.MARKET_VOLATILITY), \
             patch('engine.random.random', return_value=0.01), \
             patch('engine.random.uniform', return_value=-0.8):  # Large negative change
            
            shock_event = self.engine.trigger_shock()
            
            # Price should not go below $1.00
            for stock in self.trade_backend.stocks.values():
                assert stock.price >= Decimal('1.00')
                
    def test_shock_last_tick_update(self):
        """Test that last_shock_tick is updated correctly."""
        self.engine.shock_probability = Decimal('1.0')
        self.engine.min_ticks_between_shocks = 0
        self.engine.current_tick = 42
        
        with patch('engine.random.choice', return_value=ShockType.RATE_HIKE), \
             patch('engine.random.random', return_value=0.01), \
             patch('engine.random.randint', return_value=50):
            
            initial_last_shock = self.engine.last_shock_tick
            shock_event = self.engine.trigger_shock()
            
            assert shock_event is not None
            assert self.engine.last_shock_tick == 42
            assert self.engine.last_shock_tick != initial_last_shock


class TestShockSystemEdgeCases:
    """Test edge cases for the shock system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.ledger = Ledger(Decimal('100000.00'))
        self.trade_backend = TradeBackend()
        self.debt_backend = DebtBackend()
        self.allocation_manager = AllocationManager(
            self.ledger, 
            self.trade_backend, 
            debt_backend=self.debt_backend
        )
        self.engine = SimulationEngine(self.ledger, self.allocation_manager)
        
    def test_shock_with_missing_debt_backend(self):
        """Test rate shock when debt backend is missing."""
        # Create allocation manager without debt backend
        allocation_manager = AllocationManager(self.ledger, self.trade_backend)
        engine = SimulationEngine(self.ledger, allocation_manager)
        engine.shock_probability = Decimal('1.0')
        engine.min_ticks_between_shocks = 0
        
        with patch('engine.random.choice', return_value=ShockType.RATE_HIKE), \
             patch('engine.random.random', return_value=0.01), \
             patch('engine.random.randint', return_value=50):
            
            # Should still generate news event
            shock_event = engine.trigger_shock()
            assert shock_event is not None
            assert shock_event.event_type == "RATE_SHOCK"
            
    def test_shock_with_missing_trade_backend(self):
        """Test market volatility shock when trade backend is missing."""
        # Create allocation manager without trade backend
        allocation_manager = Mock()
        allocation_manager.debt_backend = self.debt_backend
        allocation_manager.trade_backend = None
        
        engine = SimulationEngine(self.ledger, allocation_manager)
        engine.shock_probability = Decimal('1.0')
        engine.min_ticks_between_shocks = 0
        
        with patch('engine.random.choice', return_value=ShockType.MARKET_VOLATILITY), \
             patch('engine.random.random', return_value=0.01):
            
            # Should still generate news event
            shock_event = engine.trigger_shock()
            assert shock_event is not None
            assert shock_event.event_type == "MARKET_VOLATILITY"
            
    def test_extreme_rate_changes(self):
        """Test extreme rate changes don't break the system."""
        self.engine.shock_probability = Decimal('1.0')
        self.engine.min_ticks_between_shocks = 0
        
        with patch('engine.random.choice', return_value=ShockType.RATE_HIKE), \
             patch('engine.random.random', return_value=0.01), \
             patch('engine.random.randint', return_value=1000):  # 10% rate hike
            
            initial_prices = {bond_id: bond.current_price for bond_id, bond in self.debt_backend.bonds.items()}
            
            shock_event = self.engine.trigger_shock()
            
            # System should handle extreme changes gracefully
            assert shock_event is not None
            
            # All bonds should still have valid prices
            for bond in self.debt_backend.bonds.values():
                assert bond.current_price > 0
                assert bond.current_price >= bond.face_value * Decimal('0.1')
                assert bond.current_price <= bond.face_value * Decimal('2.0')
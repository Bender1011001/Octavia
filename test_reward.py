import pytest
from decimal import Decimal
from collections import deque

from engine import SimulationEngine
from models import CapitalAllocationAction, EquityAlloc

from ledger import Ledger


def test_reward_calculation_first_tick():
    """Test reward calculation on first tick (should be 0)."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    reward = engine.calculate_reward()
    assert reward == Decimal('0.00')

def test_reward_calculation_positive_nav_change():
    """Test reward when NAV increases above risk-free rate."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    engine.nav_history.append(Decimal('100000'))
    engine.ledger.cash = Decimal('102000') # NAV is now 102000
    
    # Expected return = 100000 * 0.01 = 1000
    # NAV change = 102000 - 100000 = 2000
    # Adjusted NAV change = 2000 - 1000 = 1000
    reward = engine.calculate_reward()
    assert reward == pytest.approx(Decimal('1000.00'))

def test_reward_calculation_negative_nav_change():
    """Test reward when NAV decreases."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    engine.nav_history.append(Decimal('100000'))
    engine.ledger.cash = Decimal('99000') # NAV is now 99000
    
    # Expected return = 100000 * 0.01 = 1000
    # NAV change = 99000 - 100000 = -1000
    # Adjusted NAV change = -1000 - 1000 = -2000
    reward = engine.calculate_reward()
    assert reward == pytest.approx(Decimal('-2000.00'))

def test_reward_calculation_with_cognition_cost():
    """Test that cognition cost reduces reward."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    engine.nav_history.append(Decimal('100000'))
    engine.ledger.cash = Decimal('102000')
    
    action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        allocations=[],
        cognition_cost=Decimal('50.00')
    )
    
    # Adjusted NAV change = 1000
    # Cognition cost = 0.01 * 50 = 0.5
    # Reward = 1000 - 0.5 = 999.5
    reward = engine.calculate_reward(action)
    assert reward == pytest.approx(Decimal('999.5'))

def test_volatility_penalty_calculation():
    """Test volatility penalty when volatility exceeds target."""
    ledger = Ledger(initial_cash=Decimal('100'))
    engine = SimulationEngine(ledger)
    engine.target_volatility = Decimal('0.01')
    engine.lambda_vol = Decimal('1.0')
    engine.nav_history = deque([Decimal('100'), Decimal('105'), Decimal('102'), Decimal('108')], maxlen=10)
    
    # This will create significant volatility
    engine.ledger.cash = Decimal('95')
    
    # Calculate expected volatility penalty manually
    import numpy as np
    nav_values = [100.0, 105.0, 102.0, 108.0, 95.0]
    nav_array = np.array(nav_values)
    returns = np.diff(nav_array) / nav_array[:-1]
    volatility = Decimal(str(np.std(returns)))
    excess_volatility = max(Decimal('0.00'), volatility - engine.target_volatility)
    expected_vol_penalty = engine.lambda_vol * excess_volatility
    
    # previous_nav = 108
    # current_nav = 95
    # nav_change = -13
    # expected_return = 108 * 0.01 = 1.08
    # delta_nav_adj = -13 - 1.08 = -14.08
    expected_delta_nav_adj = Decimal('-14.08')
    expected_reward = expected_delta_nav_adj - expected_vol_penalty
    
    reward = engine.calculate_reward()
    
    # Check that the reward matches our calculation (within small tolerance for floating point)
    assert abs(reward - expected_reward) < Decimal('0.01')
    # Also verify it's less than the adjusted NAV change (original assertion)
    assert reward < expected_delta_nav_adj

def test_volatility_penalty_below_target():
    """Test no penalty when volatility is below target."""
    ledger = Ledger(initial_cash=Decimal('1000'))
    engine = SimulationEngine(ledger)
    engine.target_volatility = Decimal('0.1') # High target
    engine.nav_history = deque([Decimal('1000'), Decimal('1001'), Decimal('1002')], maxlen=10)
    engine.ledger.cash = Decimal('1003')
    
    # previous_nav = 1002
    # current_nav = 1003
    # nav_change = 1
    # expected_return = 1002 * 0.01 = 10.02
    # delta_nav_adj = 1 - 10.02 = -9.02
    
    reward = engine.calculate_reward()
    assert reward == pytest.approx(Decimal('-9.02'))

def test_nav_history_tracking():
    """Test that NAV history is properly maintained."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    engine.tick()
    assert len(engine.nav_history) == 1
    assert engine.nav_history[0] == Decimal('100000.00')
    engine.tick()
    assert len(engine.nav_history) == 2

def test_risk_free_rate_adjustment():
    """Test that risk-free rate adjustment works correctly."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    engine.nav_history.append(Decimal('100000'))
    engine.ledger.cash = Decimal('101000') # Exactly matches risk-free rate
    
    # Expected return = 100000 * 0.01 = 1000
    # NAV change = 101000 - 100000 = 1000
    # Adjusted NAV change = 1000 - 1000 = 0
    reward = engine.calculate_reward()
    assert reward == pytest.approx(Decimal('0.00'))
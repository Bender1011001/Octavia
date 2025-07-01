from decimal import Decimal
import pytest
from engine import SimulationEngine
from models import Observation, CapitalAllocationAction, EquityAlloc
from router import AllocationManager
from ledger import Ledger

def test_engine_initialization():
    """Test engine starts with correct state."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    assert engine.current_tick == 0
    assert engine.ledger.cash == Decimal('100000.00')
    assert engine.previous_nav == Decimal('100000.00')

def test_tick_advances_time():
    """Test that tick() advances the current_tick."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    engine.tick()
    assert engine.current_tick == 1

def test_reset_functionality():
    """Test that reset() returns engine to initial state."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    engine.tick()
    engine.ledger.add_asset('EQUITY', 'AAPL', Decimal('10'), Decimal('1000'))
    
    initial_cash = Decimal('50000.00')
    observation = engine.reset(initial_cash=initial_cash)
    
    assert engine.current_tick == 0
    assert engine.ledger.cash == initial_cash
    assert len(engine.ledger.assets) == 0
    assert engine.previous_nav == initial_cash
    assert isinstance(observation, Observation)
    assert observation.tick == 0
    assert observation.cash == initial_cash

def test_observation_structure():
    """Test that observations have correct structure."""
    ledger = Ledger(initial_cash=Decimal('100000.00'))
    engine = SimulationEngine(ledger)
    obs, _, _, _, _ = engine.tick()
    
    assert isinstance(obs, Observation)
    assert hasattr(obs, 'tick')
    assert hasattr(obs, 'cash')
    assert hasattr(obs, 'nav')
    assert hasattr(obs, 'portfolio')
    assert hasattr(obs, 'projects_available')
    assert hasattr(obs, 'news')
    assert obs.tick == 1

from backends import TradeBackend


def test_engine_with_allocation_manager():
    """Test engine integration with allocation manager."""
    ledger = Ledger(initial_cash=Decimal('100000'))
    trade_backend = TradeBackend()
    allocation_manager = AllocationManager(ledger, trade_backend)
    engine = SimulationEngine(ledger, allocation_manager=allocation_manager)
    assert engine.allocation_manager is not None
    assert engine.ledger is ledger

def test_tick_with_action():
    """Test tick() method with CapitalAllocationAction."""
    ledger = Ledger(initial_cash=Decimal('10000'))
    trade_backend = TradeBackend()
    allocation_manager = AllocationManager(ledger, trade_backend)
    engine = SimulationEngine(ledger, allocation_manager=allocation_manager)

    action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test buy",
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('1000'))],
        cognition_cost=Decimal('1')
    )
    obs, reward, _, _, info = engine.tick(action)

    assert obs.tick == 1
    assert ledger.cash == Decimal('9000')
    assert len(info.failed_allocations) == 0
    # On the first tick, delta_nav_adj is 0, so reward calculation is:
    # reward = delta_nav_adj - (lambda_vol * excess_vol_penalty) - cognition_cost - memory_cost
    # reward = 0 - (1.0 * 0) - (0.01 * 1) - 0 = -0.01
    expected_reward = Decimal('0.00') - (engine.lambda_vol * Decimal('0.00')) - (engine.kappa_cost * action.cognition_cost) - Decimal('0.00')
    assert reward == expected_reward

def test_reward_consistency():
    """Test that reward calculations are consistent."""
    ledger1 = Ledger(initial_cash=Decimal('100000.00'))
    engine1 = SimulationEngine(ledger1)
    engine1.nav_history.append(Decimal('100000'))
    engine1.ledger.cash = Decimal('101000')
    reward1 = engine1.calculate_reward()

    ledger2 = Ledger(initial_cash=Decimal('100000.00'))
    engine2 = SimulationEngine(ledger2)
    engine2.nav_history.append(Decimal('100000'))
    engine2.ledger.cash = Decimal('101000')
    reward2 = engine2.calculate_reward()
    
    assert reward1 == reward2
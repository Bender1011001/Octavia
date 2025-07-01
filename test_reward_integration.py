import pytest
from decimal import Decimal

from engine import SimulationEngine
from backends import TradeBackend
from router import AllocationManager
from ledger import Ledger
from models import CapitalAllocationAction, EquityAlloc

def test_full_reward_workflow():
    """Test complete reward calculation in realistic scenario."""
    trade_backend = TradeBackend()
    ledger = Ledger(initial_cash=Decimal('100000'), price_provider=trade_backend)
    allocation_manager = AllocationManager(ledger, trade_backend)
    engine = SimulationEngine(ledger, allocation_manager)

    # Tick 1: Buy AAPL
    action1 = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="Buy AAPL",
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('10000'))],
        cognition_cost=Decimal('10')
    )
    obs1, reward1, _, _, _ = engine.tick(action1)
    
    # First reward is just cognition cost
    assert reward1 == Decimal('-0.10') # kappa_cost * cognition_cost = 0.01 * 10
    assert obs1.nav == Decimal('100000')
    assert len(engine.nav_history) == 1

    # Tick 2: AAPL price increases
    trade_backend.update_prices({'AAPL': Decimal('155')}) # Price went up
    obs2, reward2, _, _, _ = engine.tick()

    # NAV should increase
    # Initial investment was $10,000 in AAPL at $150/share = 66.66 shares.
    # After price rises to $155/share: 66.66 * 155 = 10,333.33
    # New NAV = $90,000 (cash) + $10,333.33 (assets) = $100,333.33
    # Previous NAV = $100,000
    # NAV Change = $333.33
    # Expected Return = $100,000 * 0.01 = $1,000
    # Adjusted NAV change = $333.33 - $1,000 = -$666.67
    assert obs2.nav == pytest.approx(Decimal('100333.33'))
    assert reward2 == pytest.approx(Decimal('-666.67'))

def test_reward_with_failed_allocations():
    """Test reward calculation when some allocations fail."""
    trade_backend = TradeBackend()
    ledger = Ledger(initial_cash=Decimal('1000'), price_provider=trade_backend)
    allocation_manager = AllocationManager(ledger, trade_backend)
    engine = SimulationEngine(ledger, allocation_manager)

    # Action with insufficient funds
    action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="Over-invest",
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('2000'))],
        cognition_cost=Decimal('5')
    )
    
    obs, reward, _, _, info = engine.tick(action)
    
    assert len(info.failed_allocations) == 1
    # Reward is only cognition cost
    assert reward == Decimal('-0.05')
    assert obs.nav == Decimal('1000')

def test_reward_progression_over_time():
    """Test reward calculation over multiple ticks."""
    trade_backend = TradeBackend()
    ledger = Ledger(initial_cash=Decimal('100000'), price_provider=trade_backend)
    allocation_manager = AllocationManager(ledger, trade_backend)
    engine = SimulationEngine(ledger, allocation_manager)

    # Buy stock
    action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="Buy",
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('50000'))],
        cognition_cost=Decimal('0')
    )
    engine.tick(action) # reward1 = 0

    # Price goes up
    trade_backend.update_prices({'AAPL': Decimal('152')})
    _, reward2, _, _, _ = engine.tick()
    # 50000 / 150 = 333.33 shares. NAV change = 333.33 * 2 = 666.66
    # Expected = 100000 * 0.01 = 1000. Adj = 666.66 - 1000 = -333.34
    assert reward2 == pytest.approx(Decimal('-333.33'))

    # Price goes down
    trade_backend.update_prices({'AAPL': Decimal('148')})
    _, reward3, _, _, _ = engine.tick()
    # Prev NAV = 50000 cash + 333.33 * 152 = 100666.66
    # NAV change = 333.33 * -4 = -1333.32
    # Expected = 100666.66 * 0.01 = 1006.67. Adj = -1333.32 - 1006.67 = -2339.99
    assert reward3 < Decimal('-2300') # Volatility penalty will make it even lower
import pytest
from decimal import Decimal
from engine import SimulationEngine
from ledger import Ledger
from backends import TradeBackend
from router import AllocationManager
from models import CapitalAllocationAction, EquityAlloc

def test_full_trading_workflow():
    """Test complete workflow: Engine -> AllocationManager -> TradeBackend -> Ledger"""
    # 1. Setup
    initial_cash = Decimal('50000.00')
    
    # Create the core components
    ledger = Ledger(initial_cash=initial_cash)
    trade_backend = TradeBackend()
    allocation_manager = AllocationManager(ledger=ledger, trade_backend=trade_backend)
    
    # Create the simulation engine (though we'll call the manager directly for this test)
    # engine = SimulationEngine(agents=[]) # Not strictly needed as we drive the action

    # 2. Create a CapitalAllocationAction to BUY stock
    buy_amount = Decimal('15000.00')
    buy_action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        cognition_cost=Decimal("0.0"),
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="GOOGL", usd=buy_amount)]
    )
    
    # 3. Execute the action through the allocation manager
    failed_buy = allocation_manager.execute_action(buy_action)
    
    # 4. Verify ledger state changes correctly after BUY
    assert not failed_buy
    assert ledger.cash == initial_cash - buy_amount
    assert len(ledger.assets) == 1
    googl_asset = ledger.assets[0]
    assert googl_asset.identifier == "GOOGL"
    assert googl_asset.cost_basis == buy_amount
    # Price of GOOGL is 2500, so 15000 / 2500 = 6 shares
    assert googl_asset.quantity == 6 

    # 5. Create an action to SELL stock
    sell_amount = Decimal('-5000.00')
    sell_action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        cognition_cost=Decimal("0.0"),
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="GOOGL", usd=sell_amount)]
    )
    
    # 6. Execute the sell action
    failed_sell = allocation_manager.execute_action(sell_action)
    
    # 7. Verify ledger state changes correctly after SELL
    assert not failed_sell
    # Cash should increase by 5000
    assert ledger.cash == initial_cash - buy_amount + abs(sell_amount)
    assert len(ledger.assets) == 1
    # 5000 / 2500 = 2 shares sold
    # 6 - 2 = 4 shares remaining
    assert ledger.assets[0].quantity == 4
    # cost_basis should be reduced proportionally
    # (15000 / 6) * 4 = 10000
    assert ledger.assets[0].cost_basis == Decimal('10000.00')
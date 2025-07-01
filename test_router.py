import pytest
from decimal import Decimal
from unittest.mock import Mock
from router import AllocationManager
from backends import TradeBackend
from ledger import Ledger
from models import CapitalAllocationAction, EquityAlloc, FailedAllocation

@pytest.fixture
def mock_ledger():
    """Fixture for a mock Ledger."""
    ledger = Mock(spec=Ledger)
    ledger.cash = Decimal('10000.00')
    ledger.assets = []
    return ledger

@pytest.fixture
def mock_trade_backend():
    """Fixture for a mock TradeBackend."""
    return Mock(spec=TradeBackend)

def test_allocation_manager_initialization(mock_ledger, mock_trade_backend):
    """Test manager initializes correctly."""
    manager = AllocationManager(ledger=mock_ledger, trade_backend=mock_trade_backend)
    assert manager.ledger == mock_ledger
    assert manager.trade_backend == mock_trade_backend

def test_execute_equity_buy_success(mock_ledger, mock_trade_backend):
    """Test successful stock purchase."""
    manager = AllocationManager(ledger=mock_ledger, trade_backend=mock_trade_backend)
    
    # Mock trade_backend to return success
    mock_trade_backend.execute_allocation.return_value = True
    
    buy_action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        cognition_cost=Decimal("0.0"),
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal("1500.00"))]
    )
    
    failed = manager.execute_action(buy_action)
    
    assert not failed
    mock_trade_backend.execute_allocation.assert_called_once()

def test_execute_equity_buy_insufficient_funds(mock_ledger, mock_trade_backend):
    """Test buy fails with insufficient cash."""
    manager = AllocationManager(ledger=mock_ledger, trade_backend=mock_trade_backend)
    
    # Mock trade_backend to return failure
    mock_trade_backend.execute_allocation.return_value = False
    
    buy_action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        cognition_cost=Decimal("0.0"),
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal("15000.00"))] # More than available cash
    )
    
    failed = manager.execute_action(buy_action)
    
    assert len(failed) == 1
    assert failed[0].reason == "Trade execution failed"
    mock_trade_backend.execute_allocation.assert_called_once()

def test_execute_equity_sell_success(mock_ledger, mock_trade_backend):
    """Test successful stock sale."""
    manager = AllocationManager(ledger=mock_ledger, trade_backend=mock_trade_backend)
    
    # Mock trade_backend to return success
    mock_trade_backend.execute_allocation.return_value = True
    
    sell_action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        cognition_cost=Decimal("0.0"),
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal("-1000.00"))]
    )
    
    failed = manager.execute_action(sell_action)
    
    assert not failed
    mock_trade_backend.execute_allocation.assert_called_once()

def test_execute_equity_sell_insufficient_shares(mock_ledger, mock_trade_backend):
    """Test sell fails with insufficient shares."""
    manager = AllocationManager(ledger=mock_ledger, trade_backend=mock_trade_backend)
    
    # Mock trade_backend to return failure
    mock_trade_backend.execute_allocation.return_value = False
    
    sell_action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        cognition_cost=Decimal("0.0"),
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal("-1000.00"))]
    )
    
    failed = manager.execute_action(sell_action)
    
    assert len(failed) == 1
    assert failed[0].reason == "Trade execution failed"
    mock_trade_backend.execute_allocation.assert_called_once()

def test_multiple_allocations(mock_ledger, mock_trade_backend):
    """Test processing multiple allocations in one action."""
    manager = AllocationManager(ledger=mock_ledger, trade_backend=mock_trade_backend)
    
    # Mock trade_backend to succeed on first call, fail on second
    mock_trade_backend.execute_allocation.side_effect = [True, False]
    
    actions = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        cognition_cost=Decimal("0.0"),
        allocations=[
            EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal("1000.00")), # Success
            EquityAlloc(asset_type="EQUITY", ticker="GOOGL", usd=Decimal("3000.00")) # Fail
        ]
    )
    
    failed = manager.execute_action(actions)
    
    assert len(failed) == 1
    assert failed[0].allocation.ticker == "GOOGL"
    assert mock_trade_backend.execute_allocation.call_count == 2

def test_failed_allocation_tracking(mock_ledger, mock_trade_backend):
    """Test that failed allocations are properly tracked."""
    manager = AllocationManager(ledger=mock_ledger, trade_backend=mock_trade_backend)
    
    # Mock trade_backend to raise an exception
    mock_trade_backend.execute_allocation.side_effect = Exception("Market closed")
    
    buy_action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="test",
        cognition_cost=Decimal("0.0"),
        allocations=[EquityAlloc(asset_type="EQUITY", ticker="TSLA", usd=Decimal("800.00"))]
    )
    
    failed = manager.execute_action(buy_action)
    
    assert len(failed) == 1
    assert failed[0].allocation.ticker == "TSLA"
    assert "Trade error: Market closed" in failed[0].reason
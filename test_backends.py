import pytest
from decimal import Decimal
from backends import TradeBackend, Stock
from ledger import Ledger
from models import EquityAlloc

@pytest.fixture
def trade_backend():
    """Fixture for a TradeBackend instance."""
    return TradeBackend()

@pytest.fixture
def ledger():
    """Fixture for a Ledger instance."""
    return Ledger(initial_cash=Decimal('10000.00'))

def test_trade_backend_initialization(trade_backend):
    """Test backend starts with sample stocks."""
    assert 'AAPL' in trade_backend.stocks
    assert isinstance(trade_backend.stocks['AAPL'], Stock)
    assert trade_backend.stocks['AAPL'].price == Decimal('150.00')

def test_get_price_valid_ticker(trade_backend):
    """Test getting price for valid ticker."""
    price = trade_backend.get_price('AAPL')
    assert price == Decimal('150.00')

def test_get_price_invalid_ticker(trade_backend):
    """Test getting price for invalid ticker returns None."""
    price = trade_backend.get_price('INVALID')
    assert price is None

def test_buy_stock_success(trade_backend, ledger):
    """Test successful stock purchase."""
    allocation = EquityAlloc(asset_type='EQUITY', ticker='AAPL', usd=Decimal('1500.00'))
    success = trade_backend.execute_allocation(allocation, ledger)
    
    assert success
    assert ledger.cash == Decimal('8500.00')
    assert len(ledger.assets) == 1
    asset = ledger.assets[0]
    assert asset.asset_type == "EQUITY"
    assert asset.identifier == 'AAPL'
    assert asset.quantity == 10  # 1500 / 150
    assert asset.cost_basis == Decimal('1500.00')

def test_buy_stock_insufficient_funds(trade_backend, ledger):
    """Test buy fails with insufficient funds."""
    allocation = EquityAlloc(asset_type='EQUITY', ticker='GOOGL', usd=Decimal('15000.00')) # Not enough cash
    success = trade_backend.execute_allocation(allocation, ledger)
    
    assert not success
    assert ledger.cash == Decimal('10000.00') # Unchanged
    assert len(ledger.assets) == 0 # Unchanged

def test_sell_stock_success(trade_backend, ledger):
    """Test successful stock sale."""
    # First, buy some stock to sell
    ledger.add_asset("EQUITY", "MSFT", 10, Decimal('3000.00'))
    assert ledger.cash == Decimal('7000.00')
    
    # Now, sell it
    allocation = EquityAlloc(asset_type='EQUITY', ticker='MSFT', usd=Decimal('-1500.00'))
    success = trade_backend.execute_allocation(allocation, ledger)
    
    assert success
    # 1500 / 300 = 5 shares to sell
    # 10 - 5 = 5 shares remaining
    # 7000 + 1500 = 8500 cash
    assert ledger.cash == Decimal('8500.00')
    assert len(ledger.assets) == 1
    assert ledger.assets[0].quantity == 5

def test_sell_stock_insufficient_shares(trade_backend, ledger):
    """Test sell fails with insufficient shares."""
    # Agent has no MSFT stock
    allocation = EquityAlloc(asset_type='EQUITY', ticker='MSFT', usd=Decimal('-1500.00'))
    success = trade_backend.execute_allocation(allocation, ledger)
    
    assert not success
    assert ledger.cash == Decimal('10000.00') # Unchanged
    assert len(ledger.assets) == 0 # Unchanged

def test_price_updates(trade_backend):
    """Test updating stock prices."""
    trade_backend.update_prices({'TSLA': Decimal('950.50')})
    assert trade_backend.get_price('TSLA') == Decimal('950.50')
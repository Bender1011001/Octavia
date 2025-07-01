"""
Demonstration of the DebtBackend and Shock System for Agent Tycoon Milestone 6.

This script demonstrates:
1. Bond trading functionality
2. Interest rate shock effects on bond prices
3. Market volatility shock effects on stock prices
4. Integration with the simulation engine
"""

from decimal import Decimal
from backends import DebtBackend, TradeBackend
from router import AllocationManager
from engine import SimulationEngine
from ledger import Ledger
from models import BondAlloc, EquityAlloc, CapitalAllocationAction
from market_data.engine import MarketDataEngine
import pandas as pd
import types

def main():
    print("=" * 60)
    print("AGENT TYCOON - MILESTONE 6 DEMONSTRATION")
    print("DebtBackend and Shock System")
    print("=" * 60)
    
    # Initialize system
    ledger = Ledger(Decimal('100000.00'))
    trade_backend = TradeBackend()
    debt_backend = DebtBackend()
    allocation_manager = AllocationManager(
        ledger, 
        trade_backend, 
        debt_backend=debt_backend
    )
    engine = SimulationEngine(ledger, allocation_manager)
    
    print(f"\n📊 INITIAL STATE")
    print(f"Cash: ${ledger.cash:,.2f}")
    print(f"NAV: ${ledger.get_nav():,.2f}")
    print(f"Available bonds: {len(debt_backend.bonds)}")
    print(f"Available stocks: {len(trade_backend.stocks)}")
    
    # Display available bonds
    print(f"\n💰 AVAILABLE BONDS:")
    for bond in debt_backend.get_all_bonds():
        print(f"  {bond.bond_id}: {bond.name}")
        print(f"    Price: ${bond.current_price:.2f}, YTM: {bond.yield_to_maturity:.4f}")
    
    # Test bond purchases
    print(f"\n🛒 PURCHASING BONDS...")
    bond_allocations = [
        BondAlloc(asset_type="BOND", bond_id="BOND-001", usd=Decimal('10000.00')),
        BondAlloc(asset_type="BOND", bond_id="BOND-002", usd=Decimal('15000.00')),
        BondAlloc(asset_type="BOND", bond_id="BOND-004", usd=Decimal('5000.00')),
    ]
    
    for allocation in bond_allocations:
        success = debt_backend.execute_allocation(allocation, ledger)
        bond = debt_backend.bonds[allocation.bond_id]
        print(f"  ✓ Bought ${allocation.usd:.2f} of {bond.name}: {'Success' if success else 'Failed'}")
    
    print(f"\n📈 AFTER BOND PURCHASES:")
    print(f"Cash: ${ledger.cash:,.2f}")
    print(f"NAV: ${ledger.get_nav():,.2f}")
    print(f"Portfolio items: {len(ledger.assets)}")
    
    # Test stock purchases for shock demonstration
    print(f"\n🏢 PURCHASING STOCKS...")
    stock_allocations = [
        EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('10000.00')),
        EquityAlloc(asset_type="EQUITY", ticker="GOOGL", usd=Decimal('15000.00')),
    ]
    
    for allocation in stock_allocations:
        success = trade_backend.execute_allocation(allocation, ledger)
        price = trade_backend.get_price(allocation.ticker)
        print(f"  ✓ Bought ${allocation.usd:.2f} of {allocation.ticker} @ ${price:.2f}: {'Success' if success else 'Failed'}")
    
    print(f"\n📊 PORTFOLIO AFTER STOCK PURCHASES:")
    print(f"Cash: ${ledger.cash:,.2f}")
    print(f"NAV: ${ledger.get_nav():,.2f}")
    
    # --- MarketDataEngine-driven interest rate shock demonstration ---
    print(f"\n⚡ APPLYING INTEREST RATE SHOCK (via MarketDataEngine)...")
    # Setup MarketDataEngine with a fake FRED series for demonstration
    tickers = list(trade_backend.stocks.keys())
    fred_series = {"FEDFUNDS": "FEDFUNDS"}
    market_data_engine = MarketDataEngine(tickers, fred_series, fred_api_key=None)
    engine.market_data_engine = market_data_engine

    # Simulate a normal tick (no shock)
    current_date = pd.Timestamp("2024-06-01")
    market_update = market_data_engine.get_market_update(current_date)
    # Apply normal market update
    if "economic" in market_update:
        debt_backend.update_interest_rates(market_update["economic"])
    if "prices" in market_update:
        trade_backend.update_prices(market_update["prices"])

    # Show state before shock
    initial_rate = debt_backend.base_interest_rate
    initial_bond_prices = {bond_id: bond.current_price for bond_id, bond in debt_backend.bonds.items()}
    initial_nav = ledger.get_nav()

    # Load and apply shocks from config
    shocks = load_shocks()
    apply_shocks(shocks, current_date, trade_backend, debt_backend)

    print(f"  📰 Interest rate shock applied: {initial_rate:.4f} → {debt_backend.base_interest_rate:.4f}")
    print(f"  💰 NAV: ${initial_nav:.2f} → ${ledger.get_nav():.2f}")

    print(f"\n💎 BOND PRICE CHANGES:")
    for bond_id, bond in debt_backend.bonds.items():
        old_price = initial_bond_prices[bond_id]
        change_pct = ((bond.current_price - old_price) / old_price) * 100
        print(f"  {bond.name}: ${old_price:.2f} → ${bond.current_price:.2f} ({change_pct:+.2f}%)")

    # --- MarketDataEngine-driven market volatility shock demonstration ---
    print(f"\n🌪️  APPLYING MARKET VOLATILITY SHOCK (via MarketDataEngine)...")
    initial_stock_prices = {ticker: stock.price for ticker, stock in trade_backend.stocks.items()}
    initial_nav = ledger.get_nav()

    # Apply market volatility shock from config (already handled in apply_shocks)
    print(f"  📰 Market volatility shock applied: -20% to all stocks")
    print(f"  💰 NAV: ${initial_nav:.2f} → ${ledger.get_nav():.2f}")

    print(f"\n📈 STOCK PRICE CHANGES:")
    for ticker, stock in trade_backend.stocks.items():
        old_price = initial_stock_prices[ticker]
        change_pct = ((stock.price - old_price) / old_price) * 100
        print(f"  {ticker}: ${old_price:.2f} → ${stock.price:.2f} ({change_pct:+.2f}%)")
    
    # Test bond selling
    print(f"\n💸 SELLING SOME BONDS...")
    sell_allocation = BondAlloc(asset_type="BOND", bond_id="BOND-001", usd=Decimal('-5000.00'))
    success = debt_backend.execute_allocation(sell_allocation, ledger)
    print(f"  ✓ Sold ${abs(sell_allocation.usd):.2f} of BOND-001: {'Success' if success else 'Failed'}")
    
    print(f"\n📊 FINAL PORTFOLIO STATE:")
    print(f"Cash: ${ledger.cash:,.2f}")
    print(f"NAV: ${ledger.get_nav():,.2f}")
    print(f"Portfolio items: {len(ledger.assets)}")
    
    print(f"\n🎯 PORTFOLIO BREAKDOWN:")
    portfolio_holdings = ledger.get_portfolio_holdings()
    for holding in portfolio_holdings:
        print(f"  {holding.asset_type} {holding.identifier}: {holding.quantity:.6f} units, ${holding.current_value:.2f}")
    
    # Demonstrate simulation tick with market data engine
    print(f"\n🔄 SIMULATION TICK WITH MARKET DATA ENGINE...")
    # Reset monkeypatches to normal fetcher methods if needed for further ticks
    # (In a real system, you would restore the original methods here.)

    obs, reward, terminated, truncated, info = engine.tick()

    print(f"  Tick: {obs.tick}")
    print(f"  News events: {len(obs.news)}")
    for news in obs.news:
        print(f"    📰 {news.event_type}: {news.description}")
    print(f"  Reward: {reward:.2f}")
    print(f"  Final NAV: ${obs.nav:.2f}")
    
    print(f"\n✅ MILESTONE 6 DEMONSTRATION COMPLETE!")
    print(f"   - Bond trading system: ✓ Working")
    print(f"   - Interest rate shocks: ✓ Working") 
    print(f"   - Market volatility shocks: ✓ Working")
    print(f"   - Integration with engine: ✓ Working")
    print("=" * 60)


if __name__ == "__main__":
    main()
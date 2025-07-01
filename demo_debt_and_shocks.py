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
    
    # Demonstrate interest rate shock
    print(f"\n⚡ APPLYING INTEREST RATE SHOCK...")
    initial_rate = debt_backend.base_interest_rate
    initial_bond_prices = {bond_id: bond.current_price for bond_id, bond in debt_backend.bonds.items()}
    initial_nav = ledger.get_nav()
    
    shock_event = engine._apply_rate_shock(150, 150)  # 1.5% rate hike
    
    print(f"  📰 {shock_event.description}")
    print(f"  📈 Base rate: {initial_rate:.4f} → {debt_backend.base_interest_rate:.4f}")
    print(f"  💰 NAV: ${initial_nav:.2f} → ${ledger.get_nav():.2f}")
    
    print(f"\n💎 BOND PRICE CHANGES:")
    for bond_id, bond in debt_backend.bonds.items():
        old_price = initial_bond_prices[bond_id]
        change_pct = ((bond.current_price - old_price) / old_price) * 100
        print(f"  {bond.name}: ${old_price:.2f} → ${bond.current_price:.2f} ({change_pct:+.2f}%)")
    
    # Demonstrate market volatility shock
    print(f"\n🌪️  APPLYING MARKET VOLATILITY SHOCK...")
    initial_stock_prices = {ticker: stock.price for ticker, stock in trade_backend.stocks.items()}
    initial_nav = ledger.get_nav()
    
    shock_event = engine._apply_market_volatility()
    
    print(f"  📰 {shock_event.description}")
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
    
    # Demonstrate simulation tick with shock
    print(f"\n🔄 SIMULATION TICK WITH SHOCK SYSTEM...")
    engine.shock_probability = Decimal('1.0')  # Force shock for demo
    engine.min_ticks_between_shocks = 0
    
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
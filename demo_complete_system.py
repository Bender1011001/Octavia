"""
Complete Agent Tycoon System Demonstration
Shows all features working together including HODL bot comparison.
"""

from decimal import Decimal
import random

from engine import SimulationEngine
from ledger import Ledger
from router import AllocationManager
from backends import TradeBackend, ProjectBackend, DebtBackend
from models import CapitalAllocationAction, EquityAlloc, ProjectAlloc, BondAlloc


def demonstrate_complete_system():
    """Demonstrate the complete Agent Tycoon system."""
    print("=== Agent Tycoon Complete System Demonstration ===\n")
    
    # Initialize all backends
    trade_backend = TradeBackend()
    project_backend = ProjectBackend()
    debt_backend = DebtBackend()
    
    # Create price provider wrapper class
    class PriceProvider:
        def __init__(self, trade_backend, debt_backend):
            self.trade_backend = trade_backend
            self.debt_backend = debt_backend
            
        def get_price(self, identifier: str):
            return self.trade_backend.get_price(identifier)
            
        def get_bond_price(self, identifier: str):
            return self.debt_backend.get_bond_price(identifier)
    
    price_provider = PriceProvider(trade_backend, debt_backend)
    
    # Initialize ledger and allocation manager
    initial_cash = Decimal('200000.00')
    ledger = Ledger(initial_cash, price_provider=price_provider)
    allocation_manager = AllocationManager(ledger, trade_backend, project_backend, debt_backend)
    
    # Initialize engine with HODL comparison
    engine = SimulationEngine(ledger, allocation_manager, enable_hodl_comparison=True)
    
    print(f"Starting simulation with ${initial_cash:,.2f}")
    print(f"HODL comparison: {'Enabled' if engine.enable_hodl_comparison else 'Disabled'}")
    
    # Run simulation for 30 ticks
    for tick in range(30):
        # Create diverse actions
        action = None
        if tick % 3 == 0 and tick < 15:  # Invest in first half
            action = create_sample_action(tick, ledger.cash)
        
        # Execute tick
        obs, reward, terminated, truncated, info = engine.tick(action)
        
        # Print status every 5 ticks
        if tick % 5 == 0 or obs.news:
            print(f"\n--- Tick {obs.tick} ---")
            print(f"Cash: ${obs.cash:,.2f}")
            print(f"NAV: ${obs.nav:,.2f}")
            print(f"Reward: {reward:.2f}")
            print(f"Portfolio: {len(obs.portfolio)} assets")
            
            if obs.news:
                print("News Events:")
                for event in obs.news:
                    print(f"  - {event.event_type}: {event.description}")
            
            # Show HODL comparison if available
            if engine.enable_hodl_comparison and engine.hodl_engine:
                hodl_nav = engine.hodl_engine.ledger.get_nav()
                print(f"HODL Bot NAV: ${hodl_nav:,.2f}")
                print(f"Outperformance: ${obs.nav - hodl_nav:,.2f}")
        
        if terminated or truncated:
            break
    
    # Final adaptability report
    if engine.enable_hodl_comparison:
        print("\n=== Final Adaptability Report ===")
        report = engine.get_adaptability_report()
        for key, value in report.items():
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value}")
    
    print(f"\nSimulation completed after {obs.tick} ticks")
    print(f"Final NAV: ${obs.nav:,.2f}")
    print(f"Total Return: {((obs.nav / initial_cash) - 1) * 100:.2f}%")
    

def create_sample_action(tick: int, available_cash: Decimal) -> CapitalAllocationAction:
    """Create sample diversified action."""
    allocations = []
    
    # Diversify across asset types
    if tick % 9 == 0:  # Stocks
        allocations.append(EquityAlloc(
            asset_type="EQUITY",
            ticker=random.choice(["AAPL", "GOOGL", "MSFT"]),
            usd=min(available_cash * Decimal('0.15'), Decimal('20000.00'))
        ))
    elif tick % 9 == 3:  # Projects
        allocations.append(ProjectAlloc(
            asset_type="PROJECT",
            project_id=random.choice(["P-001", "P-002", "P-003"]),
            usd=min(available_cash * Decimal('0.20'), Decimal('30000.00'))
        ))
    elif tick % 9 == 6:  # Bonds
        allocations.append(BondAlloc(
            asset_type="BOND",
            bond_id=random.choice(["BOND-001", "BOND-002", "BOND-003"]),
            usd=min(available_cash * Decimal('0.10'), Decimal('15000.00'))
        ))
    
    if allocations:
        return CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment=f"Diversified investment at tick {tick}",
            allocations=allocations,
            cognition_cost=Decimal('2.50')
        )
    
    return None


def demonstrate_hodl_vs_active_comparison():
    """Demonstrate HODL bot vs active agent comparison."""
    print("\n=== HODL Bot vs Active Agent Comparison ===\n")
    
    # Initialize backends
    trade_backend = TradeBackend()
    project_backend = ProjectBackend()
    debt_backend = DebtBackend()
    
    class PriceProvider:
        def __init__(self, trade_backend, debt_backend):
            self.trade_backend = trade_backend
            self.debt_backend = debt_backend
            
        def get_price(self, identifier: str):
            return self.trade_backend.get_price(identifier)
            
        def get_bond_price(self, identifier: str):
            return self.debt_backend.get_bond_price(identifier)
    
    price_provider = PriceProvider(trade_backend, debt_backend)
    
    initial_cash = Decimal('100000.00')
    
    # Create active agent simulation
    active_ledger = Ledger(initial_cash, price_provider=price_provider)
    active_allocation_manager = AllocationManager(
        active_ledger, trade_backend, project_backend, debt_backend
    )
    active_engine = SimulationEngine(
        active_ledger, active_allocation_manager, enable_hodl_comparison=True
    )
    
    print("Running comparison simulation...")
    
    # Run simulation with active trading
    for tick in range(20):
        action = None
        
        # Active strategy: invest early, diversify, react to shocks
        if tick == 1:
            action = CapitalAllocationAction(
                action_type="ALLOCATE_CAPITAL",
                comment="Initial investment",
                allocations=[
                    EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('30000.00'))
                ],
                cognition_cost=Decimal('1.00')
            )
        elif tick == 5:
            action = CapitalAllocationAction(
                action_type="ALLOCATE_CAPITAL",
                comment="Diversification",
                allocations=[
                    EquityAlloc(asset_type="EQUITY", ticker="GOOGL", usd=Decimal('20000.00'))
                ],
                cognition_cost=Decimal('1.50')
            )
        elif tick == 10:
            action = CapitalAllocationAction(
                action_type="ALLOCATE_CAPITAL",
                comment="Bond allocation",
                allocations=[
                    BondAlloc(asset_type="BOND", bond_id="BOND-001", usd=Decimal('15000.00'))
                ],
                cognition_cost=Decimal('1.00')
            )
        
        obs, reward, terminated, truncated, info = active_engine.tick(action)
        
        if terminated or truncated:
            break
    
    # Get final comparison
    final_report = active_engine.get_adaptability_report()
    
    print(f"\nFinal Results:")
    print(f"Active Agent NAV: ${final_report.get('final_agent_nav', 0):,.2f}")
    print(f"HODL Bot NAV: ${final_report.get('final_hodl_nav', 0):,.2f}")
    print(f"Outperformance: ${final_report.get('total_outperformance', 0):,.2f}")
    print(f"Outperformance %: {final_report.get('total_outperformance_pct', 0)*100:.2f}%")
    
    if 'adaptability_score' in final_report:
        print(f"\nAdaptability Metrics:")
        print(f"Adaptability Score: {final_report['adaptability_score']:.4f}")
        print(f"Shocks Encountered: {final_report.get('shock_count', 0)}")
        print(f"Times Outperformed: {final_report.get('outperformed_count', 0)}")
        print(f"Consistency Ratio: {final_report.get('consistency_ratio', 0):.2f}")


def demonstrate_shock_response():
    """Demonstrate how the system responds to shock events."""
    print("\n=== Shock Response Demonstration ===\n")
    
    # Initialize system
    trade_backend = TradeBackend()
    project_backend = ProjectBackend()
    debt_backend = DebtBackend()
    
    class PriceProvider:
        def __init__(self, trade_backend, debt_backend):
            self.trade_backend = trade_backend
            self.debt_backend = debt_backend
            
        def get_price(self, identifier: str):
            return self.trade_backend.get_price(identifier)
            
        def get_bond_price(self, identifier: str):
            return self.debt_backend.get_bond_price(identifier)
    
    price_provider = PriceProvider(trade_backend, debt_backend)
    
    initial_cash = Decimal('100000.00')
    ledger = Ledger(initial_cash, price_provider=price_provider)
    allocation_manager = AllocationManager(ledger, trade_backend, project_backend, debt_backend)
    engine = SimulationEngine(ledger, allocation_manager, enable_hodl_comparison=True)
    
    print("Monitoring system response to shocks...")
    
    shock_count = 0
    for tick in range(25):
        # Make some investments
        action = None
        if tick == 1:
            action = CapitalAllocationAction(
                action_type="ALLOCATE_CAPITAL",
                comment="Pre-shock investment",
                allocations=[
                    EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('25000.00'))
                ],
                cognition_cost=Decimal('1.00')
            )
        
        obs, reward, terminated, truncated, info = engine.tick(action)
        
        # Check for shocks and system response
        if obs.news:
            for event in obs.news:
                if event.event_type in ["RATE_SHOCK", "MARKET_VOLATILITY"]:
                    shock_count += 1
                    print(f"\n🚨 SHOCK DETECTED at tick {obs.tick}:")
                    print(f"   Type: {event.event_type}")
                    print(f"   Description: {event.description}")
                    print(f"   Agent NAV: ${obs.nav:,.2f}")
                    
                    if engine.hodl_engine:
                        hodl_nav = engine.hodl_engine.ledger.get_nav()
                        print(f"   HODL NAV: ${hodl_nav:,.2f}")
                        print(f"   HODL Bot Status: {'HODLing' if engine.hodl_bot.is_hodling else 'Active'}")
        
        if terminated or truncated:
            break
    
    print(f"\nShock Response Summary:")
    print(f"Total shocks encountered: {shock_count}")
    
    if engine.adaptability_measurer:
        adaptability_data = engine.adaptability_measurer.calculate_adaptability_score()
        print(f"Measured shock events: {adaptability_data.get('shock_count', 0)}")
        print(f"Adaptability score: {adaptability_data.get('adaptability_score', 0):.4f}")


if __name__ == "__main__":
    # Run all demonstrations
    demonstrate_complete_system()
    demonstrate_hodl_vs_active_comparison()
    demonstrate_shock_response()
    
    print("\n=== Agent Tycoon System Demonstration Complete ===")
    print("The system successfully integrates:")
    print("✓ Multi-asset trading (stocks, bonds, projects)")
    print("✓ Shock event simulation and response")
    print("✓ HODL bot baseline comparison")
    print("✓ Adaptability measurement and scoring")
    print("✓ Comprehensive reward calculation")
    print("✓ Portfolio management and tracking")
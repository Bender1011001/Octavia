"""Demonstration of the Project Investment System."""

from decimal import Decimal
from backends import TradeBackend, ProjectBackend
from router import AllocationManager
from engine import SimulationEngine
from ledger import Ledger
from models import CapitalAllocationAction, ProjectAlloc, EquityAlloc


def main():
    """Demonstrate the project investment system."""
    print("=== Agent Tycoon Project Investment System Demo ===\n")
    
    # Create backends
    trade_backend = TradeBackend()
    project_backend = ProjectBackend()
    
    # Create ledger and allocation manager
    ledger = Ledger(Decimal('200000.00'), price_provider=trade_backend)
    allocation_manager = AllocationManager(ledger, trade_backend, project_backend)
    
    # Create simulation engine
    engine = SimulationEngine(ledger, allocation_manager)
    
    print(f"Starting simulation with ${ledger.cash:,.2f} cash\n")
    
    # Show available projects
    print("Available Projects:")
    print("-" * 80)
    available_projects = project_backend.get_available_projects()
    for project in available_projects:
        print(f"ID: {project.project_id} | {project.name}")
        print(f"  Investment: ${project.required_investment:,.2f}")
        print(f"  Expected Return: {project.expected_return_pct:.1%}")
        print(f"  Risk Level: {project.risk_level}")
        print(f"  Duration: {project.weeks_to_completion} weeks")
        print()
    
    # Make diverse investments
    print("Making investments...")
    action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="Diversified portfolio with projects and stocks",
        allocations=[
            # Project investments
            ProjectAlloc(asset_type="PROJECT", project_id="P-001", usd=Decimal('30000.00')),
            ProjectAlloc(asset_type="PROJECT", project_id="P-002", usd=Decimal('40000.00')),
            ProjectAlloc(asset_type="PROJECT", project_id="P-005", usd=Decimal('25000.00')),
            # Stock investments
            EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('20000.00')),
            EquityAlloc(asset_type="EQUITY", ticker="GOOGL", usd=Decimal('15000.00'))
        ],
        cognition_cost=Decimal('25.00')
    )
    
    # Execute first tick with investments
    obs, reward, terminated, truncated, info = engine.tick(action)
    
    print(f"Investments executed successfully!")
    print(f"Failed allocations: {len(info.failed_allocations)}")
    print(f"Remaining cash: ${obs.cash:,.2f}")
    print(f"Total NAV: ${obs.nav:,.2f}")
    print(f"Reward: ${reward:.2f}")
    print()
    
    # Show portfolio
    print("Current Portfolio:")
    print("-" * 50)
    for holding in obs.portfolio:
        print(f"{holding.asset_type}: {holding.identifier}")
        print(f"  Quantity: {holding.quantity}")
        print(f"  Value: ${holding.current_value:,.2f}")
        print()
    
    # Simulate time progression
    print("Simulating time progression...")
    print("=" * 60)
    
    week = 1
    while week <= 16:  # Run for 16 weeks to see all projects complete
        obs, reward, terminated, truncated, info = engine.tick()
        
        # Show news events
        if obs.news:
            print(f"\nWeek {week}:")
            for news in obs.news:
                print(f"  📰 {news.description}")
        
        # Show portfolio changes
        project_holdings = [h for h in obs.portfolio if h.asset_type == "PROJECT"]
        if week % 4 == 0 or obs.news:  # Show status every 4 weeks or when there's news
            print(f"\nWeek {week} Status:")
            print(f"  Cash: ${obs.cash:,.2f}")
            print(f"  NAV: ${obs.nav:,.2f}")
            print(f"  Active Projects: {len(project_holdings)}")
            print(f"  Reward: ${reward:.2f}")
        
        week += 1
    
    print("\n" + "=" * 60)
    print("Final Results:")
    print(f"Final Cash: ${obs.cash:,.2f}")
    print(f"Final NAV: ${obs.nav:,.2f}")
    print(f"Total Return: ${obs.nav - Decimal('200000.00'):,.2f}")
    print(f"Return Percentage: {((obs.nav / Decimal('200000.00')) - 1) * 100:.2f}%")
    
    # Show remaining portfolio
    print("\nFinal Portfolio:")
    for holding in obs.portfolio:
        print(f"  {holding.asset_type}: {holding.identifier} = ${holding.current_value:,.2f}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
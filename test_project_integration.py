"""Integration tests for project investment system."""

import pytest
from decimal import Decimal
from backends import TradeBackend, ProjectBackend
from router import AllocationManager
from engine import SimulationEngine
from ledger import Ledger
from models import CapitalAllocationAction, ProjectAlloc, EquityAlloc


class TestProjectIntegration:
    """Integration tests for the complete project investment workflow."""

    def test_full_project_workflow(self):
        """Test complete project investment workflow."""
        # Create backends
        trade_backend = TradeBackend()
        project_backend = ProjectBackend()
        
        # Create ledger and allocation manager
        ledger = Ledger(Decimal('100000.00'), price_provider=trade_backend)
        allocation_manager = AllocationManager(ledger, trade_backend, project_backend)
        
        # Create engine
        engine = SimulationEngine(ledger, allocation_manager)
        
        # Create investment action
        action = CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Investing in tech startup",
            allocations=[
                ProjectAlloc(
                    asset_type="PROJECT",
                    project_id="P-004",  # Biotech Research - 6 weeks
                    usd=Decimal('20000.00')
                )
            ],
            cognition_cost=Decimal('10.00')
        )
        
        # Execute first tick with investment
        obs, reward, terminated, truncated, info = engine.tick(action)
        
        # Verify investment was successful
        assert len(info.failed_allocations) == 0
        assert obs.cash == Decimal('80000.00')  # 100k - 20k
        
        # Verify project appears in portfolio
        project_holdings = [h for h in obs.portfolio if h.asset_type == "PROJECT"]
        assert len(project_holdings) == 1
        assert project_holdings[0].identifier == "P-004"
        assert project_holdings[0].current_value == Decimal('20000.00')
        
        # Verify project is no longer fully available
        biotech_projects = [p for p in obs.projects_available if p.project_id == "P-004"]
        assert len(biotech_projects) == 1
        assert biotech_projects[0].required_investment == Decimal('10000.00')  # 30k - 20k
        
        # Advance time until project completes (6 weeks)
        final_obs = None
        project_completion_news = []
        
        for week in range(6):
            obs, reward, terminated, truncated, info = engine.tick()
            final_obs = obs
            
            # Collect project completion news
            project_news = [n for n in obs.news if n.event_type == "PROJECT_COMPLETION"]
            project_completion_news.extend(project_news)
        
        # Verify project completed
        assert len(project_completion_news) == 1
        assert "Biotech Research" in project_completion_news[0].description
        
        # Verify project asset removed from portfolio
        final_project_holdings = [h for h in final_obs.portfolio if h.asset_type == "PROJECT"]
        assert len(final_project_holdings) == 0
        
        # Verify cash changed (payout received)
        assert final_obs.cash != Decimal('80000.00')
        
        # Verify NAV calculation includes payout
        assert final_obs.nav == final_obs.cash  # No other assets

    def test_multiple_project_investments(self):
        """Test investing in multiple projects simultaneously."""
        # Create backends
        trade_backend = TradeBackend()
        project_backend = ProjectBackend()
        
        # Create ledger and allocation manager
        ledger = Ledger(Decimal('200000.00'), price_provider=trade_backend)
        allocation_manager = AllocationManager(ledger, trade_backend, project_backend)
        
        # Create engine
        engine = SimulationEngine(ledger, allocation_manager)
        
        # Create action with multiple project investments
        action = CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Diversified project portfolio",
            allocations=[
                ProjectAlloc(asset_type="PROJECT", project_id="P-001", usd=Decimal('30000.00')),
                ProjectAlloc(asset_type="PROJECT", project_id="P-002", usd=Decimal('40000.00')),
                ProjectAlloc(asset_type="PROJECT", project_id="P-005", usd=Decimal('25000.00'))
            ],
            cognition_cost=Decimal('15.00')
        )
        
        # Execute investment
        obs, reward, terminated, truncated, info = engine.tick(action)
        
        # Verify all investments successful
        assert len(info.failed_allocations) == 0
        assert obs.cash == Decimal('105000.00')  # 200k - 95k
        
        # Verify all projects in portfolio
        project_holdings = [h for h in obs.portfolio if h.asset_type == "PROJECT"]
        assert len(project_holdings) == 3
        
        project_ids = {h.identifier for h in project_holdings}
        assert project_ids == {"P-001", "P-002", "P-005"}
        
        # Verify total project value
        total_project_value = sum(h.current_value for h in project_holdings)
        assert total_project_value == Decimal('95000.00')
        
        # Advance time and check for completions
        completed_projects = set()
        
        for week in range(16):  # Longest project is 16 weeks
            obs, reward, terminated, truncated, info = engine.tick()
            
            # Track completed projects
            for news in obs.news:
                if news.event_type == "PROJECT_COMPLETION":
                    if "Infrastructure Bond" in news.description:
                        completed_projects.add("P-005")
                    elif "Tech Startup Alpha" in news.description:
                        completed_projects.add("P-001")
                    elif "Green Energy Initiative" in news.description:
                        completed_projects.add("P-002")
        
        # All projects should have completed
        assert completed_projects == {"P-001", "P-002", "P-005"}
        
        # No project assets should remain
        final_project_holdings = [h for h in obs.portfolio if h.asset_type == "PROJECT"]
        assert len(final_project_holdings) == 0

    def test_project_with_trade_integration(self):
        """Test projects working alongside stock trading."""
        # Create backends
        trade_backend = TradeBackend()
        project_backend = ProjectBackend()
        
        # Create ledger and allocation manager
        ledger = Ledger(Decimal('150000.00'), price_provider=trade_backend)
        allocation_manager = AllocationManager(ledger, trade_backend, project_backend)
        
        # Create engine
        engine = SimulationEngine(ledger, allocation_manager)
        
        # Create mixed allocation action
        action = CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Mixed portfolio strategy",
            allocations=[
                # Stock investments
                EquityAlloc(asset_type="EQUITY", ticker="AAPL", usd=Decimal('30000.00')),
                EquityAlloc(asset_type="EQUITY", ticker="GOOGL", usd=Decimal('25000.00')),
                # Project investments
                ProjectAlloc(asset_type="PROJECT", project_id="P-003", usd=Decimal('50000.00')),
                ProjectAlloc(asset_type="PROJECT", project_id="P-005", usd=Decimal('20000.00'))
            ],
            cognition_cost=Decimal('20.00')
        )
        
        # Execute mixed allocation
        obs, reward, terminated, truncated, info = engine.tick(action)
        
        # Verify all allocations successful
        assert len(info.failed_allocations) == 0
        assert obs.cash == Decimal('25000.00')  # 150k - 125k
        
        # Verify portfolio composition
        equity_holdings = [h for h in obs.portfolio if h.asset_type == "EQUITY"]
        project_holdings = [h for h in obs.portfolio if h.asset_type == "PROJECT"]
        
        assert len(equity_holdings) == 2
        assert len(project_holdings) == 2
        
        # Verify equity holdings
        equity_tickers = {h.identifier for h in equity_holdings}
        assert equity_tickers == {"AAPL", "GOOGL"}
        
        # Verify project holdings
        project_ids = {h.identifier for h in project_holdings}
        assert project_ids == {"P-003", "P-005"}
        
        # Verify NAV calculation includes both asset types
        expected_nav = obs.cash
        for holding in obs.portfolio:
            expected_nav += holding.current_value
        assert obs.nav == expected_nav
        
        # Advance time to see project completions
        project_news_count = 0
        
        for week in range(16):
            obs, reward, terminated, truncated, info = engine.tick()
            
            # Count project completion news
            project_news = [n for n in obs.news if n.event_type == "PROJECT_COMPLETION"]
            project_news_count += len(project_news)
        
        # Should have 2 project completions
        assert project_news_count == 2
        
        # Equity holdings should remain, projects should be completed
        final_equity_holdings = [h for h in obs.portfolio if h.asset_type == "EQUITY"]
        final_project_holdings = [h for h in obs.portfolio if h.asset_type == "PROJECT"]
        
        assert len(final_equity_holdings) == 2  # Stocks remain
        assert len(final_project_holdings) == 0  # Projects completed

    def test_project_investment_failure_handling(self):
        """Test handling of failed project investments."""
        # Create backends
        trade_backend = TradeBackend()
        project_backend = ProjectBackend()
        
        # Create ledger with limited cash
        ledger = Ledger(Decimal('30000.00'), price_provider=trade_backend)
        allocation_manager = AllocationManager(ledger, trade_backend, project_backend)
        
        # Create engine
        engine = SimulationEngine(ledger, allocation_manager)
        
        # Create action with investments that should fail
        action = CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Testing failure scenarios",
            allocations=[
                # This should succeed
                ProjectAlloc(asset_type="PROJECT", project_id="P-005", usd=Decimal('25000.00')),
                # This should fail - insufficient funds
                ProjectAlloc(asset_type="PROJECT", project_id="P-001", usd=Decimal('50000.00')),
                # This should fail - non-existent project
                ProjectAlloc(asset_type="PROJECT", project_id="P-999", usd=Decimal('10000.00'))
            ],
            cognition_cost=Decimal('10.00')
        )
        
        # Execute action
        obs, reward, terminated, truncated, info = engine.tick(action)
        
        # Should have 2 failed allocations
        assert len(info.failed_allocations) == 2
        
        # Check failure reasons
        failed_project_ids = [fa.allocation.project_id for fa in info.failed_allocations]
        assert "P-001" in failed_project_ids
        assert "P-999" in failed_project_ids
        
        # Only one project should be in portfolio
        project_holdings = [h for h in obs.portfolio if h.asset_type == "PROJECT"]
        assert len(project_holdings) == 1
        assert project_holdings[0].identifier == "P-005"
        
        # Cash should reflect only the successful investment
        assert obs.cash == Decimal('5000.00')  # 30k - 25k

    def test_project_partial_funding_integration(self):
        """Test partial funding scenarios in full integration."""
        # Create backends
        trade_backend = TradeBackend()
        project_backend = ProjectBackend()
        
        # Create ledger and allocation manager
        ledger = Ledger(Decimal('100000.00'), price_provider=trade_backend)
        allocation_manager = AllocationManager(ledger, trade_backend, project_backend)
        
        # Create engine
        engine = SimulationEngine(ledger, allocation_manager)
        
        # First investor takes partial funding
        action1 = CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Partial investment",
            allocations=[
                ProjectAlloc(asset_type="PROJECT", project_id="P-001", usd=Decimal('30000.00'))
            ],
            cognition_cost=Decimal('5.00')
        )
        
        obs1, _, _, _, _ = engine.tick(action1)
        
        # Verify partial funding
        p001_available = next(p for p in obs1.projects_available if p.project_id == "P-001")
        assert p001_available.required_investment == Decimal('20000.00')  # 50k - 30k
        
        # Second investor completes funding
        action2 = CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Complete funding",
            allocations=[
                ProjectAlloc(asset_type="PROJECT", project_id="P-001", usd=Decimal('20000.00'))
            ],
            cognition_cost=Decimal('5.00')
        )
        
        obs2, _, _, _, _ = engine.tick(action2)
        
        # Project should no longer be available
        p001_projects = [p for p in obs2.projects_available if p.project_id == "P-001"]
        assert len(p001_projects) == 0
        
        # Should have 1 consolidated project holding for same project
        project_holdings = [h for h in obs2.portfolio if h.asset_type == "PROJECT" and h.identifier == "P-001"]
        assert len(project_holdings) == 1
        
        # Should have quantity 2.0 (two separate investments consolidated)
        assert project_holdings[0].quantity == Decimal('2.0')
        
        # Total investment should be 50k
        assert project_holdings[0].current_value == Decimal('50000.00')
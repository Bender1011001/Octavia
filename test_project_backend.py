"""Unit tests for ProjectBackend functionality."""

import pytest
from decimal import Decimal
from backends import ProjectBackend, Project, ProjectInvestment
from models import ProjectAlloc, ProjectInfo
from ledger import Ledger


class TestProjectBackend:
    """Test suite for ProjectBackend class."""

    def test_project_backend_initialization(self):
        """Test backend initializes with sample projects."""
        backend = ProjectBackend()
        
        # Should have 5 sample projects
        assert len(backend.available_projects) == 5
        
        # Check specific projects exist
        assert "P-001" in backend.available_projects
        assert "P-002" in backend.available_projects
        assert "P-003" in backend.available_projects
        assert "P-004" in backend.available_projects
        assert "P-005" in backend.available_projects
        
        # Check project properties
        tech_startup = backend.available_projects["P-001"]
        assert tech_startup.name == "Tech Startup Alpha"
        assert tech_startup.required_investment == Decimal('50000.00')
        assert tech_startup.expected_return_pct == Decimal('0.25')
        assert tech_startup.risk_level == "HIGH"
        assert tech_startup.weeks_to_completion == 8
        assert tech_startup.success_probability == Decimal('0.6')
        assert tech_startup.remaining_funding == Decimal('50000.00')

    def test_get_available_projects(self):
        """Test getting list of available projects."""
        backend = ProjectBackend()
        projects = backend.get_available_projects()
        
        # Should return all 5 projects initially
        assert len(projects) == 5
        
        # Check that all returned objects are ProjectInfo instances
        for project in projects:
            assert isinstance(project, ProjectInfo)
            
        # Check specific project info
        tech_project = next(p for p in projects if p.project_id == "P-001")
        assert tech_project.name == "Tech Startup Alpha"
        assert tech_project.required_investment == Decimal('50000.00')
        assert tech_project.expected_return_pct == Decimal('0.25')
        assert tech_project.risk_level == "HIGH"
        assert tech_project.weeks_to_completion == 8

    def test_project_investment_success(self):
        """Test successful project investment."""
        backend = ProjectBackend()
        ledger = Ledger(Decimal('100000.00'))
        
        # Create investment allocation
        allocation = ProjectAlloc(
            asset_type="PROJECT",
            project_id="P-001",
            usd=Decimal('25000.00')
        )
        
        # Execute investment
        result = backend.execute_allocation(allocation, ledger)
        
        # Should succeed
        assert result is True
        
        # Check ledger state
        assert ledger.cash == Decimal('75000.00')  # 100k - 25k
        
        # Check project asset was added
        project_assets = [a for a in ledger.assets if a.asset_type == "PROJECT"]
        assert len(project_assets) == 1
        assert project_assets[0].identifier == "P-001"
        assert project_assets[0].quantity == Decimal('1.0')
        assert project_assets[0].cost_basis == Decimal('25000.00')
        
        # Check project remaining funding
        project = backend.available_projects["P-001"]
        assert project.remaining_funding == Decimal('25000.00')  # 50k - 25k
        
        # Check investment tracking
        assert len(backend.agent_investments) == 1
        investment = backend.agent_investments[0]
        assert investment.project_id == "P-001"
        assert investment.amount_invested == Decimal('25000.00')
        assert investment.weeks_remaining == 8

    def test_project_investment_insufficient_funds(self):
        """Test investment fails with insufficient funds."""
        backend = ProjectBackend()
        ledger = Ledger(Decimal('10000.00'))  # Only 10k cash
        
        # Try to invest 25k
        allocation = ProjectAlloc(
            asset_type="PROJECT",
            project_id="P-001",
            usd=Decimal('25000.00')
        )
        
        # Should fail
        result = backend.execute_allocation(allocation, ledger)
        assert result is False
        
        # Ledger should be unchanged
        assert ledger.cash == Decimal('10000.00')
        assert len(ledger.assets) == 0
        
        # No investments should be tracked
        assert len(backend.agent_investments) == 0

    def test_project_investment_nonexistent_project(self):
        """Test investment fails for non-existent project."""
        backend = ProjectBackend()
        ledger = Ledger(Decimal('100000.00'))
        
        # Try to invest in non-existent project
        allocation = ProjectAlloc(
            asset_type="PROJECT",
            project_id="P-999",
            usd=Decimal('25000.00')
        )
        
        # Should fail
        result = backend.execute_allocation(allocation, ledger)
        assert result is False
        
        # Ledger should be unchanged
        assert ledger.cash == Decimal('100000.00')
        assert len(ledger.assets) == 0

    def test_project_lifecycle_completion(self):
        """Test project completion and payout."""
        backend = ProjectBackend()
        ledger = Ledger(Decimal('100000.00'))
        
        # Make investment
        allocation = ProjectAlloc(
            asset_type="PROJECT",
            project_id="P-005",  # Infrastructure Bond - 4 weeks, 95% success
            usd=Decimal('25000.00')
        )
        backend.execute_allocation(allocation, ledger)
        
        initial_cash = ledger.cash
        
        # Advance time until project completes
        news_events = []
        for week in range(4):
            weekly_news = backend.tick(ledger)
            news_events.extend(weekly_news)
        
        # Project should be completed
        assert len(backend.agent_investments) == 0
        
        # Should have news event
        assert len(news_events) == 1
        assert "Infrastructure Bond" in news_events[0]
        
        # Cash should have changed (payout received)
        assert ledger.cash != initial_cash
        
        # Project asset should be removed from ledger
        project_assets = [a for a in ledger.assets if a.asset_type == "PROJECT"]
        assert len(project_assets) == 0

    def test_project_payout_calculation(self):
        """Test payout calculation for success and failure."""
        backend = ProjectBackend()
        
        # Create a test investment
        investment = ProjectInvestment("P-001", Decimal('10000.00'), 0)
        
        # Test multiple payouts to check distribution
        payouts = []
        for _ in range(100):
            payout = backend._calculate_project_payout(investment)
            payouts.append(payout)
        
        # All payouts should be positive
        assert all(p > 0 for p in payouts)
        
        # Should have some variation in payouts
        assert len(set(payouts)) > 1
        
        # Payouts should be properly quantized to 2 decimal places
        for payout in payouts:
            assert payout == payout.quantize(Decimal('0.01'))

    def test_partial_project_funding(self):
        """Test investing less than full project requirement."""
        backend = ProjectBackend()
        ledger = Ledger(Decimal('100000.00'))
        
        # Invest more than project needs
        allocation = ProjectAlloc(
            asset_type="PROJECT",
            project_id="P-005",  # Infrastructure Bond needs 25k
            usd=Decimal('30000.00')  # Try to invest 30k
        )
        
        result = backend.execute_allocation(allocation, ledger)
        assert result is True
        
        # Should only invest what's needed
        assert ledger.cash == Decimal('75000.00')  # 100k - 25k (not 30k)
        
        # Project should be fully funded
        project = backend.available_projects["P-005"]
        assert project.remaining_funding == Decimal('0.00')
        
        # Investment should reflect actual amount
        investment = backend.agent_investments[0]
        assert investment.amount_invested == Decimal('25000.00')

    def test_project_no_longer_available_after_full_funding(self):
        """Test that fully funded projects don't appear in available list."""
        backend = ProjectBackend()
        ledger = Ledger(Decimal('100000.00'))
        
        # Fully fund a project
        allocation = ProjectAlloc(
            asset_type="PROJECT",
            project_id="P-005",
            usd=Decimal('25000.00')
        )
        backend.execute_allocation(allocation, ledger)
        
        # Get available projects
        available = backend.get_available_projects()
        
        # P-005 should not be in the list
        project_ids = [p.project_id for p in available]
        assert "P-005" not in project_ids
        assert len(available) == 4  # 4 remaining projects

    def test_multiple_investments_same_project(self):
        """Test multiple investments in the same project."""
        backend = ProjectBackend()
        ledger = Ledger(Decimal('100000.00'))
        
        # Make first investment
        allocation1 = ProjectAlloc(
            asset_type="PROJECT",
            project_id="P-001",
            usd=Decimal('20000.00')
        )
        backend.execute_allocation(allocation1, ledger)
        
        # Make second investment
        allocation2 = ProjectAlloc(
            asset_type="PROJECT",
            project_id="P-001",
            usd=Decimal('15000.00')
        )
        backend.execute_allocation(allocation2, ledger)
        
        # Should have two separate investment records
        assert len(backend.agent_investments) == 2
        
        # Both should be for the same project
        assert all(inv.project_id == "P-001" for inv in backend.agent_investments)
        
        # Total investment should be tracked correctly
        total_invested = sum(inv.amount_invested for inv in backend.agent_investments)
        assert total_invested == Decimal('35000.00')
        
        # Project remaining funding should be correct
        project = backend.available_projects["P-001"]
        assert project.remaining_funding == Decimal('15000.00')  # 50k - 35k

    def test_get_agent_investments(self):
        """Test getting agent's current investments."""
        backend = ProjectBackend()
        ledger = Ledger(Decimal('100000.00'))
        
        # Make some investments
        allocation1 = ProjectAlloc(asset_type="PROJECT", project_id="P-001", usd=Decimal('20000.00'))
        allocation2 = ProjectAlloc(asset_type="PROJECT", project_id="P-002", usd=Decimal('30000.00'))
        
        backend.execute_allocation(allocation1, ledger)
        backend.execute_allocation(allocation2, ledger)
        
        # Get investments
        investments = backend.get_agent_investments()
        
        # Should return a copy
        assert investments is not backend.agent_investments
        assert len(investments) == 2
        
        # Check investment details
        p001_investment = next(inv for inv in investments if inv.project_id == "P-001")
        assert p001_investment.amount_invested == Decimal('20000.00')
        assert p001_investment.weeks_remaining == 8
        
        p002_investment = next(inv for inv in investments if inv.project_id == "P-002")
        assert p002_investment.amount_invested == Decimal('30000.00')
        assert p002_investment.weeks_remaining == 12
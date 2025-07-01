"""Unit tests for the DebtBackend and Bond classes."""

from decimal import Decimal
from backends import DebtBackend, Bond
from models import BondAlloc
from ledger import Ledger


class TestBond:
    """Test cases for the Bond class."""
    
    def test_bond_initialization(self):
        """Test bond initializes with correct attributes."""
        bond = Bond(
            bond_id="TEST-001",
            name="Test Bond",
            face_value=Decimal('1000.00'),
            coupon_rate=Decimal('0.05'),
            maturity_years=10,
            current_price=Decimal('950.00')
        )
        
        assert bond.bond_id == "TEST-001"
        assert bond.name == "Test Bond"
        assert bond.face_value == Decimal('1000.00')
        assert bond.coupon_rate == Decimal('0.05')
        assert bond.maturity_years == 10
        assert bond.current_price == Decimal('950.00')
        assert bond.yield_to_maturity > 0
        
    def test_yield_to_maturity_calculation(self):
        """Test YTM calculation."""
        bond = Bond(
            bond_id="TEST-001",
            name="Test Bond",
            face_value=Decimal('1000.00'),
            coupon_rate=Decimal('0.05'),
            maturity_years=10,
            current_price=Decimal('950.00')
        )
        
        # YTM should be approximately (50 + (1000-950)/10) / 950 = 0.0579
        expected_ytm = (Decimal('50.00') + (Decimal('1000.00') - Decimal('950.00')) / 10) / Decimal('950.00')
        assert abs(bond.yield_to_maturity - expected_ytm) < Decimal('0.001')
        
    def test_yield_to_maturity_zero_price(self):
        """Test YTM calculation with zero price."""
        bond = Bond(
            bond_id="TEST-001",
            name="Test Bond",
            face_value=Decimal('1000.00'),
            coupon_rate=Decimal('0.05'),
            maturity_years=10,
            current_price=Decimal('0.00')
        )
        
        assert bond.yield_to_maturity == Decimal('0.00')


class TestDebtBackend:
    """Test cases for the DebtBackend class."""
    
    def test_debt_backend_initialization(self):
        """Test backend initializes with sample bonds."""
        backend = DebtBackend()
        
        assert len(backend.bonds) == 5
        assert "BOND-001" in backend.bonds
        assert "BOND-002" in backend.bonds
        assert "BOND-003" in backend.bonds
        assert "BOND-004" in backend.bonds
        assert "BOND-005" in backend.bonds
        assert backend.base_interest_rate == Decimal('0.03')
        
    def test_get_bond_price(self):
        """Test getting bond prices."""
        backend = DebtBackend()
        
        # Test existing bond
        price = backend.get_bond_price("BOND-001")
        assert price == Decimal('980.00')
        
        # Test non-existing bond
        price = backend.get_bond_price("NONEXISTENT")
        assert price is None
        
    def test_bond_buy_success(self):
        """Test successful bond purchase."""
        backend = DebtBackend()
        ledger = Ledger(Decimal('10000.00'))
        
        allocation = BondAlloc(
            asset_type="BOND",
            bond_id="BOND-001",
            usd=Decimal('1000.00')
        )
        
        initial_cash = ledger.cash
        success = backend.execute_allocation(allocation, ledger)
        
        assert success is True
        assert ledger.cash == initial_cash - Decimal('1000.00')
        
        # Check bond was added to portfolio
        bond_assets = [asset for asset in ledger.assets if asset.asset_type == "BOND"]
        assert len(bond_assets) == 1
        assert bond_assets[0].identifier == "BOND-001"
        
    def test_bond_buy_insufficient_funds(self):
        """Test bond purchase with insufficient funds."""
        backend = DebtBackend()
        ledger = Ledger(Decimal('500.00'))  # Less than bond price
        
        allocation = BondAlloc(
            asset_type="BOND",
            bond_id="BOND-001",
            usd=Decimal('1000.00')
        )
        
        success = backend.execute_allocation(allocation, ledger)
        
        assert success is False
        assert ledger.cash == Decimal('500.00')  # Cash unchanged
        assert len(ledger.assets) == 0  # No assets added
        
    def test_bond_sell_success(self):
        """Test successful bond sale."""
        backend = DebtBackend()
        ledger = Ledger(Decimal('10000.00'))
        
        # First buy some bonds
        buy_allocation = BondAlloc(
            asset_type="BOND",
            bond_id="BOND-001",
            usd=Decimal('2000.00')
        )
        backend.execute_allocation(buy_allocation, ledger)
        
        # Then sell some
        sell_allocation = BondAlloc(
            asset_type="BOND",
            bond_id="BOND-001",
            usd=Decimal('-1000.00')
        )
        
        initial_cash = ledger.cash
        success = backend.execute_allocation(sell_allocation, ledger)
        
        assert success is True
        assert ledger.cash > initial_cash  # Cash increased from sale
        
    def test_bond_sell_insufficient_holdings(self):
        """Test bond sale with insufficient holdings."""
        backend = DebtBackend()
        ledger = Ledger(Decimal('10000.00'))
        
        # Try to sell bonds we don't own
        allocation = BondAlloc(
            asset_type="BOND",
            bond_id="BOND-001",
            usd=Decimal('-1000.00')
        )
        
        success = backend.execute_allocation(allocation, ledger)
        
        assert success is False
        
    def test_bond_unknown_bond_id(self):
        """Test allocation with unknown bond ID."""
        backend = DebtBackend()
        ledger = Ledger(Decimal('10000.00'))
        
        allocation = BondAlloc(
            asset_type="BOND",
            bond_id="UNKNOWN-BOND",
            usd=Decimal('1000.00')
        )
        
        success = backend.execute_allocation(allocation, ledger)
        
        assert success is False
        
    def test_bond_zero_allocation(self):
        """Test zero amount allocation."""
        backend = DebtBackend()
        ledger = Ledger(Decimal('10000.00'))
        
        allocation = BondAlloc(
            asset_type="BOND",
            bond_id="BOND-001",
            usd=Decimal('0.00')
        )
        
        success = backend.execute_allocation(allocation, ledger)
        
        assert success is True  # Zero allocation should succeed
        
    def test_update_interest_rates(self):
        """Test update_interest_rates updates base rate and bond prices as expected."""
        backend = DebtBackend()
        initial_base_rate = backend.base_interest_rate
        initial_prices = {bond_id: bond.current_price for bond_id, bond in backend.bonds.items()}

        # Simulate a rate hike to 4.5%
        backend.update_interest_rates({'interest_rate': 4.5})
        assert backend.base_interest_rate == Decimal('0.045')

        # All bond prices should generally decrease with a rate hike
        for bond_id, bond in backend.bonds.items():
            assert bond.current_price < initial_prices[bond_id]
            assert bond.yield_to_maturity > 0

        # Simulate a rate cut to 2.0%
        prices_after_hike = {bond_id: bond.current_price for bond_id, bond in backend.bonds.items()}
        backend.update_interest_rates({'interest_rate': 2.0})
        assert backend.base_interest_rate == Decimal('0.02')

        # All bond prices should generally increase with a rate cut
        for bond_id, bond in backend.bonds.items():
            assert bond.current_price > prices_after_hike[bond_id]
            assert bond.yield_to_maturity > 0

        # Test with missing or None interest_rate (should not change anything)
        prev_base_rate = backend.base_interest_rate
        prev_prices = {bond_id: bond.current_price for bond_id, bond in backend.bonds.items()}
        backend.update_interest_rates({})
        backend.update_interest_rates({'interest_rate': None})
        assert backend.base_interest_rate == prev_base_rate
        for bond_id, bond in backend.bonds.items():
            assert bond.current_price == prev_prices[bond_id]
        
    def test_bond_price_bounds(self):
        """Test bond prices stay within reasonable bounds."""
        backend = DebtBackend()
        
        # Apply extreme rate shock
        backend.apply_interest_rate_shock(2000)  # 20% increase
        
        for bond in backend.bonds.values():
            # Price should not go below 10% of face value
            min_price = bond.face_value * Decimal('0.1')
            assert bond.current_price >= min_price
            
            # Price should not go above 200% of face value
            max_price = bond.face_value * Decimal('2.0')
            assert bond.current_price <= max_price
            
    def test_get_all_bonds(self):
        """Test getting all available bonds."""
        backend = DebtBackend()
        
        bonds = backend.get_all_bonds()
        
        assert len(bonds) == 5
        assert all(isinstance(bond, Bond) for bond in bonds)
        
        # Check specific bonds are present
        bond_ids = [bond.bond_id for bond in bonds]
        assert "BOND-001" in bond_ids
        assert "BOND-002" in bond_ids
        assert "BOND-003" in bond_ids
        assert "BOND-004" in bond_ids
        assert "BOND-005" in bond_ids


class TestDebtBackendIntegration:
    """Integration tests for DebtBackend with Ledger."""
    
    def test_multiple_bond_transactions(self):
        """Test multiple bond buy/sell transactions."""
        backend = DebtBackend()
        ledger = Ledger(Decimal('50000.00'), price_provider=backend)
        
        # Buy different bonds
        allocations = [
            BondAlloc(asset_type="BOND", bond_id="BOND-001", usd=Decimal('5000.00')),
            BondAlloc(asset_type="BOND", bond_id="BOND-002", usd=Decimal('3000.00')),
            BondAlloc(asset_type="BOND", bond_id="BOND-003", usd=Decimal('2000.00')),
        ]
        
        for allocation in allocations:
            success = backend.execute_allocation(allocation, ledger)
            assert success is True
            
        # Check portfolio
        assert len(ledger.assets) == 3
        assert ledger.cash == Decimal('40000.00')
        
        # Check NAV calculation includes bond values
        nav = ledger.get_nav()
        assert nav > ledger.cash  # Should include bond values
        
    def test_bond_portfolio_valuation(self):
        """Test bond portfolio valuation after price changes."""
        backend = DebtBackend()
        ledger = Ledger(Decimal('10000.00'), price_provider=backend)
        
        # Buy bonds
        allocation = BondAlloc(
            asset_type="BOND",
            bond_id="BOND-001",
            usd=Decimal('5000.00')
        )
        backend.execute_allocation(allocation, ledger)
        
        initial_nav = ledger.get_nav()
        
        # Apply rate shock
        backend.apply_interest_rate_shock(200)  # 2% increase
        
        # NAV should change due to bond price changes
        new_nav = ledger.get_nav()
        assert new_nav != initial_nav
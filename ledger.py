from decimal import Decimal
from typing import List, Optional, Tuple

from models import AssetHolding


class Asset:
    """Represents a single asset holding."""
    def __init__(self, asset_type: str, identifier: str, quantity: Decimal, cost_basis: Decimal):
        self.asset_type = asset_type
        self.identifier = identifier
        self.quantity = quantity
        self.cost_basis = cost_basis  # Total cost when acquired

class Ledger:
    """Manages the agent's financial state and portfolio."""

    def __init__(self, initial_cash: Decimal, price_provider: Optional[object] = None):
        self._cash = initial_cash
        self.assets: List[Asset] = []
        self.price_provider = price_provider
    
    @property
    def cash(self) -> Decimal:
        """Get cash with proper quantization to 2 decimal places."""
        return self._cash.quantize(Decimal('0.01'))
    
    @cash.setter
    def cash(self, value: Decimal) -> None:
        """Set cash with proper quantization to 2 decimal places."""
        self._cash = value.quantize(Decimal('0.01'))

    def add_asset(self, asset_type: str, identifier: str, quantity: Decimal, total_cost: Decimal) -> bool:
        """Add an asset to the portfolio. Returns True if successful."""
        if total_cost > self.cash:
            return False

        self._cash -= total_cost

        # Check if we already own this asset
        existing_asset = self._find_asset(asset_type, identifier)
        if existing_asset:
            # Update existing holding (consolidate investments in the same asset/project)
            total_quantity = existing_asset.quantity + quantity
            total_cost_basis = existing_asset.cost_basis + total_cost
            existing_asset.quantity = total_quantity
            existing_asset.cost_basis = total_cost_basis
        else:
            # Add new asset
            self.assets.append(Asset(asset_type, identifier, quantity, total_cost))

        return True

    def remove_asset(self, asset_type: str, identifier: str, quantity: Decimal) -> Tuple[bool, Decimal]:
        """
        Remove quantity of an asset. Returns (success, proceeds).
        Uses price_provider to get market value.
        """
        asset = self._find_asset(asset_type, identifier)
        if not asset or asset.quantity < quantity:
            return False, Decimal('0.00')

        # Get market price
        price_per_unit = asset.cost_basis / asset.quantity if asset.quantity > 0 else Decimal('0')
        if self.price_provider and asset_type == "EQUITY":
            market_price = self.price_provider.get_price(identifier)
            if market_price is not None:
                price_per_unit = market_price
        elif self.price_provider and asset_type == "BOND" and hasattr(self.price_provider, 'get_bond_price'):
            bond_price = self.price_provider.get_bond_price(identifier)
            if bond_price is not None:
                price_per_unit = bond_price
        
        proceeds = price_per_unit * quantity

        # Update asset quantity and cost basis proportionally
        cost_basis_per_unit = asset.cost_basis / asset.quantity
        asset.quantity -= quantity
        asset.cost_basis -= cost_basis_per_unit * quantity

        # Remove asset if quantity is zero
        if asset.quantity <= Decimal('0.000001'):
            self.assets.remove(asset)

        # Add proceeds to cash
        self._cash += proceeds

        return True, proceeds

    def get_nav(self) -> Decimal:
        """Calculate Net Asset Value (cash + market value of all assets). Skips assets with missing prices."""
        import warnings
        asset_value = Decimal('0.00')
        for asset in self.assets:
            if self.price_provider and asset.asset_type == "EQUITY":
                market_price = self.price_provider.get_price(asset.identifier)
                if market_price is not None:
                    asset_value += asset.quantity * market_price
                else:
                    warnings.warn(f"Missing market price for equity {asset.identifier}; excluded from NAV.", UserWarning)
            elif self.price_provider and asset.asset_type == "BOND" and hasattr(self.price_provider, 'get_bond_price'):
                bond_price = self.price_provider.get_bond_price(asset.identifier)
                if bond_price is not None:
                    asset_value += asset.quantity * bond_price
                else:
                    warnings.warn(f"Missing market price for bond {asset.identifier}; excluded from NAV.", UserWarning)
            else:
                warnings.warn(f"Unknown asset type or missing price provider for {asset.identifier}; excluded from NAV.", UserWarning)
        return (self.cash + asset_value).quantize(Decimal('0.01'))

    def get_portfolio_holdings(self) -> List[AssetHolding]:
        """Return current portfolio as list of AssetHolding objects."""
        holdings = []
        for asset in self.assets:
            current_value = asset.cost_basis
            if self.price_provider and asset.asset_type == "EQUITY":
                market_price = self.price_provider.get_price(asset.identifier)
                if market_price is not None:
                    current_value = (asset.quantity * market_price).quantize(Decimal('0.01'))
            elif self.price_provider and asset.asset_type == "BOND" and hasattr(self.price_provider, 'get_bond_price'):
                bond_price = self.price_provider.get_bond_price(asset.identifier)
                if bond_price is not None:
                    current_value = (asset.quantity * bond_price).quantize(Decimal('0.01'))
            
            holding = AssetHolding(
                asset_type=asset.asset_type,
                identifier=asset.identifier,
                quantity=asset.quantity.quantize(Decimal('0.000001')),
                current_value=current_value.quantize(Decimal('0.01'))
            )
            holdings.append(holding)
        return holdings

    def _find_asset(self, asset_type: str, identifier: str) -> Optional[Asset]:
        """Find an asset in the portfolio."""
        for asset in self.assets:
            if asset.asset_type == asset_type and asset.identifier == identifier:
                return asset
        return None
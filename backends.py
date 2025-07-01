import numpy as np
from decimal import Decimal
from typing import Optional, Dict, List
from models import EquityAlloc, ProjectAlloc, BondAlloc, ProjectInfo
from ledger import Ledger
import uuid
from config_loader import ConfigLoader

class Stock:
    """Represents a stock with price information."""
    def __init__(self, ticker: str, price: Decimal):
        self.ticker = ticker
        self.price = price


class Project:
    """Represents an investment project."""
    def __init__(self, project_id: str, name: str, required_investment: Decimal,
                 expected_return_pct: Decimal, risk_level: str, weeks_to_completion: int,
                 success_probability: Decimal = Decimal('0.7')):
        self.project_id = project_id
        self.name = name
        self.required_investment = required_investment
        self.expected_return_pct = expected_return_pct
        self.risk_level = risk_level
        self.weeks_to_completion = weeks_to_completion
        self.success_probability = success_probability
        self.remaining_funding = required_investment
        

class ProjectInvestment:
    """Represents an agent's investment in a project."""
    def __init__(self, project_id: str, amount_invested: Decimal, weeks_remaining: int):
        self.project_id = project_id
        self.amount_invested = amount_invested
        self.weeks_remaining = weeks_remaining

class TradeBackend:
    """Handles stock trading operations."""

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        # Initialize with stocks from configuration
        if config_loader is None:
            config_loader = ConfigLoader()
        
        stocks_config = config_loader.load_stocks_config()
        self.stocks = {}
        
        for ticker, stock_data in stocks_config.items():
            self.stocks[ticker] = Stock(
                ticker=stock_data['ticker'],
                price=Decimal(stock_data['price'])
            )

    def get_price(self, ticker: str) -> Optional[Decimal]:
        """Get current price of a stock."""
        stock = self.stocks.get(ticker)
        return stock.price if stock else None

    def execute_allocation(self, allocation: EquityAlloc, ledger: Ledger) -> bool:
        """
        Execute an equity allocation (buy or sell).
        Returns True if successful, False otherwise.
        """
        ticker = allocation.ticker
        usd_amount = allocation.usd

        # Get current stock price
        price = self.get_price(ticker)
        if price is None:
            return False  # Unknown ticker

        if usd_amount > 0:
            # BUY operation
            return self._execute_buy(ticker, usd_amount, price, ledger)
        elif usd_amount < 0:
            # SELL operation
            return self._execute_sell(ticker, abs(usd_amount), price, ledger)
        else:
            # Zero amount - no operation needed
            return True

    def _execute_buy(self, ticker: str, usd_amount: Decimal, price: Decimal, ledger: Ledger) -> bool:
        """Execute a buy order."""
        # Check if agent has enough cash
        if ledger.cash < usd_amount:
            return False

        # Calculate shares to buy
        shares = (usd_amount / price).quantize(Decimal('0.000001'))

        # Add to ledger
        return ledger.add_asset("EQUITY", ticker, shares, usd_amount)

    def _execute_sell(self, ticker: str, usd_amount: Decimal, price: Decimal, ledger: Ledger) -> bool:
        """Execute a sell order."""
        # Calculate shares to sell
        shares_to_sell = (usd_amount / price).quantize(Decimal('0.000001'))

        # Check if agent has enough shares
        existing_asset = None
        for asset in ledger.assets:
            if asset.asset_type == "EQUITY" and asset.identifier == ticker:
                existing_asset = asset
                break

        if not existing_asset or existing_asset.quantity < shares_to_sell:
            return False

        # Execute the sale
        success, proceeds = ledger.remove_asset("EQUITY", ticker, shares_to_sell)
        return success

    def update_prices(self, price_changes: Dict[str, Decimal]):
        """Update stock prices from market data engine."""
        for ticker, new_price in price_changes.items():
            if ticker in self.stocks and new_price is not None:
                self.stocks[ticker].price = Decimal(str(new_price))


class ProjectBackend:
    """Handles project investment operations."""
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        self.available_projects: Dict[str, Project] = {}
        self.agent_investments: List[ProjectInvestment] = []
        self._initialize_sample_projects(config_loader)
        
    def _initialize_sample_projects(self, config_loader: Optional[ConfigLoader] = None):
        """Initialize with projects from configuration."""
        if config_loader is None:
            config_loader = ConfigLoader()
            
        projects_config = config_loader.load_projects_config()
        
        for project_data in projects_config:
            project = Project(
                project_id=project_data['project_id'],
                name=project_data['name'],
                required_investment=Decimal(project_data['required_investment']),
                expected_return_pct=Decimal(project_data['expected_return_pct']),
                risk_level=project_data['risk_level'],
                weeks_to_completion=project_data['weeks_to_completion'],
                success_probability=Decimal(project_data['success_probability'])
            )
            self.available_projects[project.project_id] = project
            
    def get_available_projects(self) -> List[ProjectInfo]:
        """Get list of projects available for investment."""
        project_infos = []
        for project in self.available_projects.values():
            if project.remaining_funding > 0:
                info = ProjectInfo(
                    project_id=project.project_id,
                    name=project.name,
                    required_investment=project.remaining_funding,
                    expected_return_pct=project.expected_return_pct,
                    risk_level=project.risk_level,
                    weeks_to_completion=project.weeks_to_completion
                )
                project_infos.append(info)
        return project_infos
        
    def execute_allocation(self, allocation: ProjectAlloc, ledger: Ledger) -> bool:
        """Execute a project investment allocation."""
        project_id = allocation.project_id
        investment_amount = allocation.usd
        
        # Check if project exists and is available
        if project_id not in self.available_projects:
            return False
            
        project = self.available_projects[project_id]
        
        # Check if project still needs funding
        if project.remaining_funding <= 0:
            return False
            
        # Check if agent has enough cash
        if ledger.cash < investment_amount:
            return False
            
        # Limit investment to remaining funding needed
        actual_investment = min(investment_amount, project.remaining_funding)
        
        # Execute the investment
        success = ledger.add_asset("PROJECT", project_id, Decimal('1.0'), actual_investment)
        if not success:
            return False
            
        # Update project funding
        project.remaining_funding -= actual_investment
        
        # Track the investment
        investment = ProjectInvestment(
            project_id=project_id,
            amount_invested=actual_investment,
            weeks_remaining=project.weeks_to_completion
        )
        self.agent_investments.append(investment)
        
        return True
        
    def tick(self, ledger: Ledger) -> List[str]:
        """
        Process one time step for all investments.
        Returns list of news events for completed projects.
        """
        news_events = []
        completed_investments = []
        
        for investment in self.agent_investments:
            investment.weeks_remaining -= 1
            
            if investment.weeks_remaining <= 0:
                # Project completed - calculate payout
                payout = self._calculate_project_payout(investment)
                
                # Remove the project asset from ledger
                ledger.remove_asset("PROJECT", investment.project_id, Decimal('1.0'))
                
                # Add cash payout
                ledger.cash += payout
                
                # Create news event
                project = self.available_projects.get(investment.project_id)
                if project:
                    if payout > investment.amount_invested:
                        news_events.append(f"Project {project.name} succeeded! Payout: ${payout}")
                    else:
                        news_events.append(f"Project {project.name} failed. Salvage: ${payout}")
                
                completed_investments.append(investment)
        
        # Remove completed investments
        for investment in completed_investments:
            self.agent_investments.remove(investment)
            
        return news_events
        
    def _calculate_project_payout(self, investment: ProjectInvestment) -> Decimal:
        """Calculate the payout for a completed project."""
        project = self.available_projects.get(investment.project_id)
        if not project:
            return Decimal('0.00')
            
        # Determine if project succeeded
        success_roll = np.random.random()
        
        if success_roll < float(project.success_probability):
            # Success - use lognormal distribution
            mean_return = float(project.expected_return_pct)
            # Use lognormal with mean and some variance
            multiplier = np.random.lognormal(mean=np.log(1 + mean_return), sigma=0.2)
            payout = investment.amount_invested * Decimal(str(multiplier))
        else:
            # Failure - use uniform distribution for salvage value (10-30% of investment)
            salvage_pct = np.random.uniform(0.1, 0.3)
            payout = investment.amount_invested * Decimal(str(salvage_pct))
            
        return payout.quantize(Decimal('0.01'))
        
    def get_agent_investments(self) -> List[ProjectInvestment]:
        """Get list of agent's current investments."""
        return self.agent_investments.copy()


class Bond:
    """Represents a bond with pricing information."""
    def __init__(self, bond_id: str, name: str, face_value: Decimal, coupon_rate: Decimal,
                 maturity_years: int, current_price: Decimal):
        self.bond_id = bond_id
        self.name = name
        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.maturity_years = maturity_years
        self.current_price = current_price
        self.yield_to_maturity = self._calculate_ytm()
        
    def _calculate_ytm(self) -> Decimal:
        """Calculate approximate yield to maturity."""
        if self.current_price == 0:
            return Decimal('0.00')
        annual_coupon = self.face_value * self.coupon_rate
        ytm = (annual_coupon + (self.face_value - self.current_price) / self.maturity_years) / self.current_price
        return ytm.quantize(Decimal('0.0001'))


class DebtBackend:
    """Handles bond trading operations."""
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        self.bonds: Dict[str, Bond] = {}
        if config_loader is None:
            config_loader = ConfigLoader()
        
        # Load market configuration for base interest rate
        market_config = config_loader.load_market_config()
        self.base_interest_rate = Decimal(market_config['base_interest_rate'])
        
        self._initialize_sample_bonds(config_loader)
        
    def _initialize_sample_bonds(self, config_loader: ConfigLoader):
        """Initialize with bonds from configuration."""
        bonds_config = config_loader.load_bonds_config()
        
        for bond_data in bonds_config:
            bond = Bond(
                bond_id=bond_data['bond_id'],
                name=bond_data['name'],
                face_value=Decimal(bond_data['face_value']),
                coupon_rate=Decimal(bond_data['coupon_rate']),
                maturity_years=bond_data['maturity_years'],
                current_price=Decimal(bond_data['current_price'])
            )
            self.bonds[bond.bond_id] = bond
            
    def get_bond_price(self, bond_id: str) -> Optional[Decimal]:
        """Get current price of a bond."""
        bond = self.bonds.get(bond_id)
        return bond.current_price if bond else None
        
    def execute_allocation(self, allocation: BondAlloc, ledger: Ledger) -> bool:
        """Execute a bond allocation (buy or sell)."""
        bond_id = allocation.bond_id
        usd_amount = allocation.usd
        
        # Get current bond price
        price = self.get_bond_price(bond_id)
        if price is None:
            return False  # Unknown bond
            
        if usd_amount > 0:
            # BUY operation
            return self._execute_buy(bond_id, usd_amount, price, ledger)
        elif usd_amount < 0:
            # SELL operation
            return self._execute_sell(bond_id, abs(usd_amount), price, ledger)
        else:
            # Zero amount - no operation needed
            return True
            
    def _execute_buy(self, bond_id: str, usd_amount: Decimal, price: Decimal, ledger: Ledger) -> bool:
        """Execute a bond buy order."""
        # Check if agent has enough cash
        if ledger.cash < usd_amount:
            return False
            
        # Calculate bond units to buy (bonds are typically sold in units)
        bond_units = usd_amount / price
        
        # Add to ledger
        return ledger.add_asset("BOND", bond_id, bond_units, usd_amount)
        
    def _execute_sell(self, bond_id: str, usd_amount: Decimal, price: Decimal, ledger: Ledger) -> bool:
        """Execute a bond sell order."""
        # Calculate bond units to sell
        bond_units_to_sell = usd_amount / price
        
        # Check if agent has enough bonds
        existing_asset = None
        for asset in ledger.assets:
            if asset.asset_type == "BOND" and asset.identifier == bond_id:
                existing_asset = asset
                break
                
        if not existing_asset or existing_asset.quantity < bond_units_to_sell:
            return False
            
        # Execute the sale
        success, proceeds = ledger.remove_asset("BOND", bond_id, bond_units_to_sell)
        return success
        
    def update_interest_rates(self, economic_data: Dict[str, float]):
        """Update bond prices based on new interest rate data."""
        if 'interest_rate' not in economic_data or economic_data['interest_rate'] is None:
            return

        new_base_rate = Decimal(str(economic_data['interest_rate'])) / Decimal('100') # Assuming rate is in percent
        rate_change = new_base_rate - self.base_interest_rate
        self.base_interest_rate = new_base_rate

        # Recalculate bond prices based on new interest rate environment
        for bond in self.bonds.values():
            # Simplified bond pricing: inverse relationship with interest rates
            # Price change = -duration * rate_change
            # Using approximate duration = maturity_years
            duration = Decimal(str(bond.maturity_years))
            price_change_pct = -duration * rate_change
            new_price = bond.current_price * (Decimal('1.0') + price_change_pct)

            # Ensure price doesn't go below 10% of face value or above 200% of face value
            min_price = bond.face_value * Decimal('0.1')
            max_price = bond.face_value * Decimal('2.0')
            bond.current_price = max(min_price, min(max_price, new_price)).quantize(Decimal('0.01'))

            # Recalculate yield to maturity
            bond.yield_to_maturity = bond._calculate_ytm()
            
    def get_all_bonds(self) -> List[Bond]:
        """Get list of all available bonds."""
        return list(self.bonds.values())
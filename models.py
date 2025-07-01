"""Core Pydantic models for Agent Tycoon simulation."""

from decimal import Decimal
from typing import Any, Dict, List, Literal, Union

from pydantic import BaseModel, Field, ValidationError, condecimal
from typing_extensions import Annotated


class EquityAlloc(BaseModel):
    model_config = {"extra": "forbid"}
    """Allocation for buying or selling equities."""
    asset_type: Literal["EQUITY"]
    ticker: str
    usd: condecimal(decimal_places=2)  # positive=buy, negative=sell


class ProjectAlloc(BaseModel):
    model_config = {"extra": "forbid"}
    """Allocation for investing in a project."""
    asset_type: Literal["PROJECT"]
    project_id: str
    usd: condecimal(decimal_places=2, ge=Decimal('0'))  # only positive


class BondAlloc(BaseModel):
    model_config = {"extra": "forbid"}
    """Allocation for buying or selling bonds."""
    asset_type: Literal["BOND"]
    bond_id: str
    usd: condecimal(decimal_places=2)  # positive=buy, negative=sell


class CashAlloc(BaseModel):
    model_config = {"extra": "forbid"}
    """Allocation for holding cash."""
    asset_type: Literal["CASH"]
    usd: condecimal(decimal_places=2)


# Discriminated Union for all allocation types
Allocation = Annotated[
    Union[EquityAlloc, ProjectAlloc, BondAlloc, CashAlloc],
    Field(discriminator='asset_type')
]


class CapitalAllocationAction(BaseModel):
    model_config = {"extra": "forbid"}
    """Action model for an agent to allocate capital."""
    action_type: Literal["ALLOCATE_CAPITAL"]
    comment: str
    allocations: List[Allocation]
    cognition_cost: condecimal(decimal_places=2, ge=Decimal('0'))


class AssetHolding(BaseModel):
    model_config = {"extra": "forbid"}
    """Represents a holding of a specific asset in the portfolio."""
    asset_type: str
    identifier: str  # ticker, project_id, bond_id, etc.
    quantity: condecimal(decimal_places=6)
    current_value: condecimal(decimal_places=2)


class ProjectInfo(BaseModel):
    model_config = {"extra": "forbid"}
    """Information about an available project for investment."""
    project_id: str
    name: str
    required_investment: condecimal(decimal_places=2)
    expected_return_pct: condecimal(decimal_places=4)
    risk_level: str
    weeks_to_completion: int


class NewsEvent(BaseModel):
    model_config = {"extra": "forbid"}
    """Represents a news event that can affect the simulation."""
    event_type: str
    description: str
    impact_data: Dict[str, Any]


class Observation(BaseModel):
    model_config = {"extra": "forbid"}
    """Observation model provided to the agent at each step."""
    tick: int
    cash: condecimal(decimal_places=2)
    nav: condecimal(decimal_places=2)
    portfolio: List[AssetHolding]
    projects_available: List[ProjectInfo]
    news: List[NewsEvent]


class FailedAllocation(BaseModel):
    model_config = {"extra": "forbid"}
    """Represents a failed allocation attempt and the reason."""
    allocation: Allocation
    reason: str


class InfoDict(BaseModel):
    model_config = {"extra": "forbid"}
    """Dictionary for additional information returned after an action."""
    failed_allocations: List[FailedAllocation]
    # Add other info fields as needed
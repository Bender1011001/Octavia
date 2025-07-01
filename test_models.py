"""Unit tests for the Pydantic models in models.py."""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from models import (
    CapitalAllocationAction,
    EquityAlloc,
    ProjectAlloc,
    CashAlloc,
    BondAlloc,
    Allocation
)

def test_valid_equity_allocation():
    """Tests that a valid EquityAlloc model can be created."""
    data = {
        "asset_type": "EQUITY",
        "ticker": "AAPL",
        "usd": Decimal("1000.50")
    }
    model = EquityAlloc(**data)
    assert model.asset_type == "EQUITY"
    assert model.ticker == "AAPL"
    assert model.usd == Decimal("1000.50")

def test_invalid_equity_allocation_with_project_field():
    """Tests that creating an EquityAlloc with a 'project_id' fails."""
    data = {
        "asset_type": "EQUITY",
        "ticker": "AAPL",
        "usd": Decimal("1000.00"),
        "project_id": "should_fail"
    }
    with pytest.raises(ValidationError):
        EquityAlloc(**data)

def test_capital_allocation_action_validation():
    """Tests the validation of a complete CapitalAllocationAction."""
    action_data = {
        "action_type": "ALLOCATE_CAPITAL",
        "comment": "Quarterly rebalance",
        "allocations": [
            {"asset_type": "EQUITY", "ticker": "GOOG", "usd": Decimal("5000.00")},
            {"asset_type": "PROJECT", "project_id": "proj_123", "usd": Decimal("10000.00")},
            {"asset_type": "BOND", "bond_id": "bond_abc", "usd": Decimal("-2000.00")},
            {"asset_type": "CASH", "usd": Decimal("-13000.00")}
        ],
        "cognition_cost": Decimal("1.25")
    }
    action = CapitalAllocationAction(**action_data)
    assert action.action_type == "ALLOCATE_CAPITAL"
    assert len(action.allocations) == 4
    assert isinstance(action.allocations[0], EquityAlloc)
    assert isinstance(action.allocations[1], ProjectAlloc)
    assert isinstance(action.allocations[2], BondAlloc)
    assert isinstance(action.allocations[3], CashAlloc)
    assert action.allocations[0].ticker == "GOOG"
    assert action.allocations[1].project_id == "proj_123"

def test_negative_usd_validation_for_project_alloc():
    """Tests that ProjectAlloc raises a ValidationError for negative usd."""
    data = {
        "asset_type": "PROJECT",
        "project_id": "proj_456",
        "usd": Decimal("-5000.00")
    }
    with pytest.raises(ValidationError) as excinfo:
        ProjectAlloc(**data)
    assert "Input should be greater than or equal to 0" in str(excinfo.value)

def test_decimal_precision_enforced():
    """Tests that decimal precision is enforced correctly."""
    with pytest.raises(ValidationError):
        # Too many decimal places for usd
        EquityAlloc(asset_type="EQUITY", ticker="MSFT", usd=Decimal("100.123"))

    with pytest.raises(ValidationError):
        # Too many decimal places for cognition_cost
        CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="test",
            allocations=[],
            cognition_cost=Decimal("0.123")
        )

def test_discriminated_union_works_correctly():
    """Tests that the discriminated union correctly parses different allocation types."""
    allocations_data = [
        {"asset_type": "EQUITY", "ticker": "TSLA", "usd": Decimal("250.75")},
        {"asset_type": "PROJECT", "project_id": "proj_789", "usd": Decimal("50000.00")},
    ]
    # Pydantic can parse this list into the correct model types within another model
    action = CapitalAllocationAction(
        action_type="ALLOCATE_CAPITAL",
        comment="Testing union",
        allocations=allocations_data,
        cognition_cost=Decimal("0.50")
    )
    assert isinstance(action.allocations[0], EquityAlloc)
    assert action.allocations[0].ticker == "TSLA"
    assert isinstance(action.allocations[1], ProjectAlloc)
    assert action.allocations[1].project_id == "proj_789"

def test_invalid_asset_type_in_union():
    """Tests that an invalid asset_type in the discriminated union fails validation."""
    allocations_data = [
        {"asset_type": "DERIVATIVE", "ticker": "SPY_CALL", "usd": Decimal("100.00")}
    ]
    with pytest.raises(ValidationError):
        CapitalAllocationAction(
            action_type="ALLOCATE_CAPITAL",
            comment="Invalid type",
            allocations=allocations_data,
            cognition_cost=Decimal("0.10")
        )
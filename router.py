from typing import List
from models import CapitalAllocationAction, FailedAllocation
from ledger import Ledger

# Forward declaration for type hinting to avoid circular dependency
if False:
    from backends import TradeBackend, ProjectBackend, DebtBackend

class AllocationManager:
    """
    Safely processes agent's CapitalAllocationAction by routing to appropriate backends.
    Follows the Atomic-on-Cash principle and proper sequencing.
    """

    def __init__(self, ledger: Ledger, trade_backend: 'TradeBackend',
                 project_backend: 'ProjectBackend' = None, debt_backend: 'DebtBackend' = None):
        self.ledger = ledger
        self.trade_backend = trade_backend
        self.project_backend = project_backend
        self.debt_backend = debt_backend

    def execute_action(self, action: CapitalAllocationAction) -> List[FailedAllocation]:
        """
        Execute a CapitalAllocationAction safely.
        Returns list of failed allocations with reasons.

        Processing order: Trade -> Project -> Debt (as per spec)
        """
        failed_allocations = []

        # Separate allocations by type for proper sequencing
        equity_allocs = []
        project_allocs = []
        bond_allocs = []
        cash_allocs = []

        for allocation in action.allocations:
            if allocation.asset_type == "EQUITY":
                equity_allocs.append(allocation)
            elif allocation.asset_type == "PROJECT":
                project_allocs.append(allocation)
            elif allocation.asset_type == "BOND":
                bond_allocs.append(allocation)
            elif allocation.asset_type == "CASH":
                cash_allocs.append(allocation)

        # Process in order: Trade -> Project -> Debt
        # For now, only implement Trade (EQUITY)

        # Process equity allocations
        for allocation in equity_allocs:
            try:
                success = self.trade_backend.execute_allocation(allocation, self.ledger)
                if not success:
                    failed_allocations.append(FailedAllocation(
                        allocation=allocation,
                        reason="Trade execution failed"
                    ))
            except Exception as e:
                failed_allocations.append(FailedAllocation(
                    allocation=allocation,
                    reason=f"Trade error: {str(e)}"
                ))

        # Process project allocations
        if self.project_backend:
            for allocation in project_allocs:
                try:
                    success = self.project_backend.execute_allocation(allocation, self.ledger)
                    if not success:
                        failed_allocations.append(FailedAllocation(
                            allocation=allocation,
                            reason="Project investment failed"
                        ))
                except Exception as e:
                    failed_allocations.append(FailedAllocation(
                        allocation=allocation,
                        reason=f"Project error: {str(e)}"
                    ))

        # Process bond allocations
        if self.debt_backend:
            for allocation in bond_allocs:
                try:
                    success = self.debt_backend.execute_allocation(allocation, self.ledger)
                    if not success:
                        failed_allocations.append(FailedAllocation(
                            allocation=allocation,
                            reason="Bond transaction failed"
                        ))
                except Exception as e:
                    failed_allocations.append(FailedAllocation(
                        allocation=allocation,
                        reason=f"Bond error: {str(e)}"
                    ))

        # TODO: Process cash_allocs when needed

        return failed_allocations
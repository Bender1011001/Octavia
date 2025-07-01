"""
Event system for Agent Tycoon visualization.
Captures all simulation events for real-time streaming and historical analysis.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
import asyncio
import json


class EventType(Enum):
    """Types of events that can occur in the simulation."""
    SIMULATION_START = "simulation_start"
    SIMULATION_TICK = "simulation_tick"
    AGENT_DECISION = "agent_decision"
    TRADE_EXECUTED = "trade_executed"
    PROJECT_INVESTMENT = "project_investment"
    PROJECT_COMPLETED = "project_completed"
    BOND_TRANSACTION = "bond_transaction"
    MARKET_SHOCK = "market_shock"
    PRICE_UPDATE = "price_update"
    PORTFOLIO_UPDATE = "portfolio_update"
    REWARD_CALCULATED = "reward_calculated"
    HODL_COMPARISON = "hodl_comparison"


class SimulationEvent(BaseModel):
    """Base class for all simulation events."""
    event_type: EventType
    timestamp: datetime
    tick: int
    data: Dict[str, Any]
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class EventCollector:
    """Collects and manages simulation events for visualization."""
    
    def __init__(self):
        self.events: List[SimulationEvent] = []
        self.subscribers: List[callable] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
    def emit(self, event_type: EventType, tick: int, data: Dict[str, Any]):
        """Emit a new event to all subscribers."""
        event = SimulationEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            tick=tick,
            data=self._serialize_data(data)
        )
        
        self.events.append(event)
        
        # Notify all subscribers
        for subscriber in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    if self.loop:
                        # Schedule the coroutine on the event loop from a different thread
                        asyncio.run_coroutine_threadsafe(subscriber(event), self.loop)
                    else:
                        print("Warning: asyncio event loop not set for async subscriber.")
                else:
                    # Call synchronous subscribers directly
                    subscriber(event)
            except Exception as e:
                print(f"Error notifying subscriber: {e}")
    
    def subscribe(self, callback: callable):
        """Subscribe to events."""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: callable):
        """Unsubscribe from events."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the asyncio event loop for thread-safe coroutine execution."""
        self.loop = loop
    
    def get_events(self, event_type: Optional[EventType] = None,
                   start_tick: Optional[int] = None,
                   end_tick: Optional[int] = None) -> List[SimulationEvent]:
        """Get filtered events."""
        filtered_events = self.events
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if start_tick is not None:
            filtered_events = [e for e in filtered_events if e.tick >= start_tick]
            
        if end_tick is not None:
            filtered_events = [e for e in filtered_events if e.tick <= end_tick]
            
        return filtered_events
    
    def clear_events(self):
        """Clear all stored events."""
        self.events.clear()
    
    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize data to JSON-compatible format."""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, Decimal):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif hasattr(value, 'dict'):  # Pydantic models
                serialized[key] = value.dict()
            elif hasattr(value, '__dict__'):  # Other objects
                serialized[key] = {k: str(v) for k, v in value.__dict__.items()}
            else:
                serialized[key] = value
        return serialized


# Global event collector instance
event_collector = EventCollector()
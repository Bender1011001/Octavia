"""
FastAPI web server for Agent Tycoon visualization.
Provides REST API and WebSocket endpoints for real-time data streaming.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Optional, Dict, Any
import json
import asyncio
from datetime import datetime

from .events import EventCollector, EventType, SimulationEvent


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection is broken, remove it
                self.disconnect(connection)


class VisualizationServer:
    """Main visualization server class."""
    
    def __init__(self, event_collector: EventCollector):
        self.app = FastAPI(title="Agent Tycoon Visualization", version="1.0.0")
        self.event_collector = event_collector
        self.connection_manager = ConnectionManager()
        
        # Subscribe to events for real-time broadcasting
        self.event_collector.subscribe(self._broadcast_event)
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all API routes."""
        
        @self.app.get("/")
        async def get_dashboard():
            """Serve the main dashboard."""
            return HTMLResponse(self._get_dashboard_html())
        
        @self.app.get("/api/events")
        async def get_events(
            event_type: Optional[str] = None,
            start_tick: Optional[int] = None,
            end_tick: Optional[int] = None,
            limit: Optional[int] = 1000
        ):
            """Get filtered events."""
            try:
                event_type_enum = EventType(event_type) if event_type else None
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid event type")
            
            events = self.event_collector.get_events(
                event_type=event_type_enum,
                start_tick=start_tick,
                end_tick=end_tick
            )
            
            # Limit results
            if limit:
                events = events[-limit:]
            
            return [event.dict() for event in events]
        
        @self.app.get("/api/portfolio/current")
        async def get_current_portfolio():
            """Get current portfolio state."""
            portfolio_events = self.event_collector.get_events(
                event_type=EventType.PORTFOLIO_UPDATE
            )
            
            if portfolio_events:
                return portfolio_events[-1].data
            else:
                return {"message": "No portfolio data available"}
        
        @self.app.get("/api/performance/summary")
        async def get_performance_summary():
            """Get performance summary metrics."""
            portfolio_events = self.event_collector.get_events(
                event_type=EventType.PORTFOLIO_UPDATE
            )
            
            if not portfolio_events:
                return {"message": "No performance data available"}
            
            # Calculate basic metrics
            nav_values = [float(event.data.get('nav', 0)) for event in portfolio_events]
            
            if len(nav_values) < 2:
                return {"nav_current": nav_values[0] if nav_values else 0}
            
            initial_nav = nav_values[0]
            current_nav = nav_values[-1]
            total_return = (current_nav - initial_nav) / initial_nav if initial_nav > 0 else 0
            
            return {
                "nav_current": current_nav,
                "nav_initial": initial_nav,
                "total_return": total_return,
                "total_return_pct": total_return * 100,
                "num_ticks": len(nav_values)
            }
        
        @self.app.get("/api/decisions/recent")
        async def get_recent_decisions(limit: int = 10):
            """Get recent AI decisions."""
            decision_events = self.event_collector.get_events(
                event_type=EventType.AGENT_DECISION
            )
            
            return [event.dict() for event in decision_events[-limit:]]
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await self.connection_manager.connect(websocket)
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.connection_manager.disconnect(websocket)
    
    async def _broadcast_event(self, event: SimulationEvent):
        """Broadcast event to all connected WebSocket clients."""
        message = json.dumps({
            "type": "event",
            "data": event.dict()
        })
        await self.connection_manager.broadcast(message)
    
    def _get_dashboard_html(self) -> str:
        """Generate the dashboard HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Tycoon Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .panel {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .panel h2 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .metric {
            display: inline-block;
            margin: 10px 20px 10px 0;
        }
        .metric-label {
            font-size: 14px;
            color: #666;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .status {
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .status.connected {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.disconnected {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        #nav-chart, #allocation-chart {
            height: 400px;
        }
        .full-width {
            grid-column: 1 / -1;
        }
    </style>
</head>
<body>
    <h1>Agent Tycoon Dashboard</h1>
    
    <div id="connection-status" class="status disconnected">
        Connecting to simulation...
    </div>
    
    <div class="dashboard">
        <div class="panel">
            <h2>Portfolio Performance</h2>
            <div id="performance-metrics">
                <div class="metric">
                    <div class="metric-label">Current NAV</div>
                    <div class="metric-value" id="current-nav">$0.00</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Return</div>
                    <div class="metric-value" id="total-return">0.00%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Simulation Tick</div>
                    <div class="metric-value" id="current-tick">0</div>
                </div>
            </div>
            <div id="nav-chart"></div>
        </div>
        
        <div class="panel">
            <h2>Asset Allocation</h2>
            <div id="allocation-chart"></div>
        </div>
        
        <div class="panel full-width">
            <h2>Recent Decisions</h2>
            <div id="recent-decisions">
                <p>No decisions yet...</p>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection
        let ws = null;
        let navData = [];
        let allocationData = {};
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = function() {
                document.getElementById('connection-status').className = 'status connected';
                document.getElementById('connection-status').textContent = 'Connected to simulation';
                loadInitialData();
            };
            
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                if (message.type === 'event') {
                    handleEvent(message.data);
                }
            };
            
            ws.onclose = function() {
                document.getElementById('connection-status').className = 'status disconnected';
                document.getElementById('connection-status').textContent = 'Disconnected from simulation';
                // Attempt to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function handleEvent(event) {
            if (event.event_type === 'portfolio_update') {
                updatePortfolioMetrics(event.data);
                updateNAVChart(event.tick, event.data.nav);
                updateAllocationChart(event.data.portfolio);
            } else if (event.event_type === 'agent_decision') {
                updateRecentDecisions(event);
            }
        }
        
        function updatePortfolioMetrics(data) {
            document.getElementById('current-nav').textContent = `$${parseFloat(data.nav).toLocaleString()}`;
            document.getElementById('current-tick').textContent = data.tick || 0;
            
            if (data.total_return_pct !== undefined) {
                const returnPct = parseFloat(data.total_return_pct).toFixed(2);
                document.getElementById('total-return').textContent = `${returnPct}%`;
            }
        }
        
        function updateNAVChart(tick, nav) {
            navData.push({x: tick, y: parseFloat(nav)});
            
            const trace = {
                x: navData.map(d => d.x),
                y: navData.map(d => d.y),
                type: 'scatter',
                mode: 'lines',
                name: 'Portfolio NAV',
                line: {color: '#007bff'}
            };
            
            const layout = {
                title: 'Portfolio Value Over Time',
                xaxis: {title: 'Simulation Tick'},
                yaxis: {title: 'Net Asset Value ($)'},
                margin: {t: 40, r: 20, b: 40, l: 60}
            };
            
            Plotly.newPlot('nav-chart', [trace], layout);
        }
        
        function updateAllocationChart(portfolio) {
            if (!portfolio || portfolio.length === 0) return;
            
            const allocation = {};
            portfolio.forEach(holding => {
                const type = holding.asset_type;
                if (!allocation[type]) allocation[type] = 0;
                allocation[type] += parseFloat(holding.current_value || 0);
            });
            
            const trace = {
                labels: Object.keys(allocation),
                values: Object.values(allocation),
                type: 'pie',
                hole: 0.4
            };
            
            const layout = {
                title: 'Asset Allocation',
                margin: {t: 40, r: 20, b: 20, l: 20}
            };
            
            Plotly.newPlot('allocation-chart', [trace], layout);
        }
        
        function updateRecentDecisions(event) {
            const decisionsDiv = document.getElementById('recent-decisions');
            const decision = document.createElement('div');
            decision.style.cssText = 'border-bottom: 1px solid #eee; padding: 10px 0;';
            
            const time = new Date(event.timestamp).toLocaleTimeString();
            decision.innerHTML = `
                <strong>Tick ${event.tick}</strong> (${time})<br>
                <small>${JSON.stringify(event.data, null, 2)}</small>
            `;
            
            decisionsDiv.insertBefore(decision, decisionsDiv.firstChild);
            
            // Keep only last 10 decisions
            while (decisionsDiv.children.length > 10) {
                decisionsDiv.removeChild(decisionsDiv.lastChild);
            }
        }
        
        async function loadInitialData() {
            try {
                // Load performance summary
                const perfResponse = await fetch('/api/performance/summary');
                const perfData = await perfResponse.json();
                if (perfData.nav_current) {
                    updatePortfolioMetrics(perfData);
                }
                
                // Load recent portfolio events for chart
                const eventsResponse = await fetch('/api/events?event_type=portfolio_update&limit=100');
                const events = await eventsResponse.json();
                
                navData = events.map(event => ({
                    x: event.tick,
                    y: parseFloat(event.data.nav)
                }));
                
                if (navData.length > 0) {
                    updateNAVChart(navData[navData.length - 1].x, navData[navData.length - 1].y);
                }
                
                // Load current portfolio
                const portfolioResponse = await fetch('/api/portfolio/current');
                const portfolioData = await portfolioResponse.json();
                if (portfolioData.portfolio) {
                    updateAllocationChart(portfolioData.portfolio);
                }
                
            } catch (error) {
                console.error('Error loading initial data:', error);
            }
        }
        
        // Initialize
        connectWebSocket();
    </script>
</body>
</html>
        """


def create_visualization_server(event_collector: EventCollector) -> FastAPI:
    """Create and configure the visualization server."""
    server = VisualizationServer(event_collector)
    return server.app
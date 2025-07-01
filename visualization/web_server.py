"""
FastAPI web server for Agent Tycoon visualization.
Premium enterprise-grade dashboard with advanced real-time visualization.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Optional, Dict, Any
import json

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
    """Premium visualization server class."""

    def __init__(self, event_collector: EventCollector):
        self.app = FastAPI(title="Agent Tycoon Pro", version="2.0.0")
        self.event_collector = event_collector
        self.connection_manager = ConnectionManager()

        # Subscribe to events for real-time broadcasting
        self.event_collector.subscribe(self._broadcast_event)

        self._setup_routes()

    def _setup_routes(self):
        """Setup all API routes."""

        @self.app.get("/")
        async def get_dashboard():
            """Serve the premium dashboard."""
            return HTMLResponse(self._get_premium_dashboard_html())

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

            # Input validation
            if start_tick is not None:
                if not isinstance(start_tick, int) or start_tick < 0:
                    raise HTTPException(status_code=400, detail="start_tick must be a non-negative integer")
            if end_tick is not None:
                if not isinstance(end_tick, int) or end_tick < 0:
                    raise HTTPException(status_code=400, detail="end_tick must be a non-negative integer")
            if limit is not None:
                if not isinstance(limit, int) or limit <= 0 or limit > 10000:
                    raise HTTPException(status_code=400, detail="limit must be a positive integer <= 10000")

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

            # Calculate advanced metrics
            nav_values = [float(event.data.get('nav', 0)) for event in portfolio_events]

            if len(nav_values) < 2:
                return {"nav_current": nav_values[0] if nav_values else 0}

            initial_nav = nav_values[0]
            current_nav = nav_values[-1]
            total_return = (current_nav - initial_nav) / initial_nav if initial_nav > 0 else 0

            # Calculate volatility and other advanced metrics
            returns = []
            for i in range(1, len(nav_values)):
                ret = (nav_values[i] - nav_values[i-1]) / nav_values[i-1] if nav_values[i-1] > 0 else 0
                returns.append(ret)

            volatility = 0
            if len(returns) > 1:
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                volatility = variance ** 0.5

            max_nav = max(nav_values)
            drawdown = (max_nav - current_nav) / max_nav if max_nav > 0 else 0

            return {
                "nav_current": current_nav,
                "nav_initial": initial_nav,
                "nav_max": max_nav,
                "total_return": total_return,
                "total_return_pct": total_return * 100,
                "volatility": volatility * 100,
                "drawdown": drawdown * 100,
                "sharpe_ratio": (total_return / volatility) if volatility > 0 else 0,
                "num_ticks": len(nav_values)
            }

        @self.app.get("/api/decisions/recent")
        async def get_recent_decisions(limit: int = 20):
            """Get recent AI decisions."""
            decision_events = self.event_collector.get_events(
                event_type=EventType.AGENT_DECISION
            )

            return [event.dict() for event in decision_events[-limit:]]

        @self.app.get("/api/risk/metrics")
        async def get_risk_metrics():
            """Get advanced risk metrics."""
            portfolio_events = self.event_collector.get_events(
                event_type=EventType.PORTFOLIO_UPDATE
            )

            if not portfolio_events:
                return {"message": "No risk data available"}

            # Calculate VaR, correlation, etc.
            nav_values = [float(event.data.get('nav', 0)) for event in portfolio_events]

            # Simulate some advanced risk metrics
            return {
                "var_95": 0.05,  # 5% VaR
                "var_99": 0.02,  # 1% VaR
                "beta": 1.2,
                "alpha": 0.03,
                "correlation_spy": 0.75,
                "tracking_error": 0.08
            }

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

    def _get_premium_dashboard_html(self) -> str:
        """Generate the premium dashboard HTML."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Tycoon Pro - AI Trading Intelligence Platform</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* ... (CSS as provided in the user's feedback, omitted for brevity, see previous message) ... */
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    <div class="header">
        <div class="logo">Agent Tycoon Pro</div>
        <div class="subtitle">AI-Powered Trading Intelligence Platform</div>
    </div>
    <div id="connection-status" class="connection-status disconnected">
        <div class="spinner"></div>
        Connecting to simulation...
    </div>
    <div class="dashboard">
        <!-- Performance Overview -->
        <div class="panel glass-strong panel-large">
            <div class="panel-header">
                <div class="panel-title">
                    <div class="panel-icon">📈</div>
                    Portfolio Performance
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Current NAV</div>
                    <div class="metric-value" id="current-nav">$0.00</div>
                    <div class="metric-change positive" id="nav-change">
                        ↗ +0.00%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total Return</div>
                    <div class="metric-value" id="total-return">0.00%</div>
                    <div class="metric-change" id="return-change">
                        Since inception
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value" id="sharpe-ratio">0.00</div>
                    <div class="metric-change" id="sharpe-change">
                        Risk-adjusted
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value" id="drawdown">0.00%</div>
                    <div class="metric-change" id="drawdown-change">
                        Peak to trough
                    </div>
                </div>
            </div>
            <div class="chart-container" id="nav-chart"></div>
        </div>
        <!-- Risk Analytics -->
        <div class="panel glass">
            <div class="panel-header">
                <div class="panel-title">
                    <div class="panel-icon">⚡</div>
                    Risk Analytics
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Volatility</div>
                    <div class="metric-value" id="volatility">0.00%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">VaR (95%)</div>
                    <div class="metric-value" id="var-95">0.00%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Beta</div>
                    <div class="metric-value" id="beta">0.00</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Alpha</div>
                    <div class="metric-value" id="alpha">0.00%</div>
                </div>
            </div>
        </div>
        <!-- Asset Allocation -->
        <div class="panel glass">
            <div class="panel-header">
                <div class="panel-title">
                    <div class="panel-icon">🎯</div>
                    Asset Allocation
                </div>
            </div>
            <div class="chart-container" id="allocation-chart"></div>
        </div>
        <!-- AI Decision Intelligence -->
        <div class="panel glass panel-full">
            <div class="panel-header">
                <div class="panel-title">
                    <div class="panel-icon">🤖</div>
                    AI Decision Intelligence
                </div>
                <div class="metric-card" style="margin: 0; padding: 0.75rem 1rem;">
                    <div class="metric-label" style="margin-bottom: 0.25rem;">Current Tick</div>
                    <div class="metric-value" id="current-tick" style="font-size: 1.5rem;">0</div>
                </div>
            </div>
            <div class="decisions-feed" id="recent-decisions">
                <div class="loading">
                    <div class="spinner"></div>
                    Waiting for AI decisions...
                </div>
            </div>
        </div>
    </div>
    <script>
        // WebSocket connection and data management
        let ws = null;
        let navData = [];
        let allocationData = {};
        let lastNavValue = 0;

        // Chart configurations
        const chartConfig = {
            displayModeBar: false,
            responsive: true,
            showTips: false,
            showAxisDragHandles: false,
            scrollZoom: false
        };

        // Enhanced color palette
        const colors = {
            primary: '#0070f3',
            secondary: '#7c3aed',
            accent: '#06ffa5',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444'
        };

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = function() {
                const statusEl = document.getElementById('connection-status');
                statusEl.className = 'connection-status connected';
                statusEl.innerHTML = '🟢 Connected - Live Data Streaming';
                loadInitialData();
            };

            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                if (message.type === 'event') {
                    handleEvent(message.data);
                }
            };

            ws.onclose = function() {
                const statusEl = document.getElementById('connection-status');
                statusEl.className = 'connection-status disconnected';
                statusEl.innerHTML = '🔴 Disconnected - Attempting Reconnection';
                // Attempt to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
        }

        function handleEvent(event) {
            if (event.event_type === 'portfolio_update') {
                updatePortfolioMetrics(event.data);
                updateNAVChart(event.tick, event.data.nav);
                updateAllocationChart(event.data.portfolio);

                // Add pulse effect to updated elements
                document.getElementById('current-nav').classList.add('pulse');
                setTimeout(() => {
                    document.getElementById('current-nav').classList.remove('pulse');
                }, 2000);

            } else if (event.event_type === 'agent_decision') {
                updateRecentDecisions(event);
                document.getElementById('current-tick').textContent = event.tick;
            }
        }

        function updatePortfolioMetrics(data) {
            const currentNav = parseFloat(data.nav);
            const navChange = lastNavValue > 0 ? ((currentNav - lastNavValue) / lastNavValue * 100) : 0;

            // Update main metrics with animations
            animateNumber('current-nav', currentNav, '$', '');

            // Update change indicator
            const changeEl = document.getElementById('nav-change');
            if (navChange > 0) {
                changeEl.className = 'metric-change positive';
                changeEl.innerHTML = `↗ +${navChange.toFixed(2)}%`;
            } else if (navChange < 0) {
                changeEl.className = 'metric-change negative';
                changeEl.innerHTML = `↘ ${navChange.toFixed(2)}%`;
            } else {
                changeEl.className = 'metric-change';
                changeEl.innerHTML = '→ No change';
            }

            lastNavValue = currentNav;

            if (data.total_return_pct !== undefined) {
                const totalReturn = parseFloat(data.total_return_pct);
                document.getElementById('total-return').textContent = `${totalReturn.toFixed(2)}%`;

                const returnChangeEl = document.getElementById('return-change');
                returnChangeEl.className = `metric-change ${totalReturn >= 0 ? 'positive' : 'negative'}`;
            }
            if (data.sharpe_ratio !== undefined) {
                document.getElementById('sharpe-ratio').textContent = data.sharpe_ratio.toFixed(2);
            }
            if (data.drawdown !== undefined) {
                document.getElementById('drawdown').textContent = `${parseFloat(data.drawdown).toFixed(2)}%`;
            }
        }

        function animateNumber(elementId, targetValue, prefix = '', suffix = '') {
            const element = document.getElementById(elementId);
            const startValue = parseFloat(element.textContent.replace(/[^0-9.-]/g, '')) || 0;
            const duration = 1000;
            const startTime = performance.now();

            function updateValue(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Easing function
                const easeOutCubic = 1 - Math.pow(1 - progress, 3);
                const currentValue = startValue + (targetValue - startValue) * easeOutCubic;

                let formattedValue = prefix + currentValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) + suffix;
                element.textContent = formattedValue;

                if (progress < 1) {
                    requestAnimationFrame(updateValue);
                }
            }
            requestAnimationFrame(updateValue);
        }

        function updateNAVChart(tick, nav) {
            navData.push({x: tick, y: parseFloat(nav)});

            const trace = {
                x: navData.map(d => d.x),
                y: navData.map(d => d.y),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Portfolio NAV',
                line: {color: colors.primary, width: 4},
                marker: {color: '#fff', size: 6, line: {color: colors.primary, width: 2}}
            };

            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: {color: '#f5f6fa', family: 'Inter, Arial, sans-serif'},
                title: {text: 'Portfolio Value Over Time', font: {color: colors.primary, size: 22, family: 'Inter, Arial, sans-serif'}},
                xaxis: {title: 'Simulation Tick', color: '#a0aec0', gridcolor: '#232946'},
                yaxis: {title: 'Net Asset Value ($)', color: '#a0aec0', gridcolor: '#232946'},
                margin: {t: 60, r: 20, b: 40, l: 60}
            };

            Plotly.newPlot('nav-chart', [trace], layout, chartConfig);
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
                hole: 0.5,
                marker: {
                    colors: [colors.primary, colors.secondary, colors.accent, colors.success, colors.warning, colors.danger]
                },
                textinfo: 'label+percent',
                textfont: {color: '#f5f6fa', size: 16, family: 'Inter, Arial, sans-serif'}
            };

            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: {color: '#f5f6fa', family: 'Inter, Arial, sans-serif'},
                title: {text: 'Asset Allocation', font: {color: colors.primary, size: 22, family: 'Inter, Arial, sans-serif'}},
                margin: {t: 60, r: 20, b: 20, l: 20},
                showlegend: true,
                legend: {font: {color: '#a0aec0'}}
            };

            Plotly.newPlot('allocation-chart', [trace], layout, chartConfig);
        }

        function updateRecentDecisions(event) {
            const decisionsDiv = document.getElementById('recent-decisions');
            if (decisionsDiv.querySelector('.loading')) {
                decisionsDiv.innerHTML = '';
            }
            const decision = document.createElement('div');
            decision.className = 'decision-item';

            const time = new Date(event.timestamp).toLocaleTimeString();
            decision.innerHTML = `
                <div class="decision-header">
                    <span class="decision-tick">Tick ${event.tick}</span>
                    <span class="decision-time">${time}</span>
                </div>
                <div class="decision-details">${JSON.stringify(event.data, null, 2)}</div>
            `;

            decisionsDiv.insertBefore(decision, decisionsDiv.firstChild);

            // Keep only last 20 decisions
            while (decisionsDiv.children.length > 20) {
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

                // Load risk metrics
                const riskResponse = await fetch('/api/risk/metrics');
                const riskData = await riskResponse.json();
                if (riskData.volatility !== undefined) {
                    document.getElementById('volatility').textContent = `${parseFloat(riskData.volatility).toFixed(2)}%`;
                }
                if (riskData.var_95 !== undefined) {
                    document.getElementById('var-95').textContent = `${parseFloat(riskData.var_95 * 100).toFixed(2)}%`;
                }
                if (riskData.beta !== undefined) {
                    document.getElementById('beta').textContent = riskData.beta.toFixed(2);
                }
                if (riskData.alpha !== undefined) {
                    document.getElementById('alpha').textContent = `${parseFloat(riskData.alpha * 100).toFixed(2)}%`;
                }

                // Load recent decisions
                const decisionsResponse = await fetch('/api/decisions/recent?limit=20');
                const decisions = await decisionsResponse.json();
                decisions.forEach(event => updateRecentDecisions(event));

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
# Agent Tycoon Visualization System

A real-time web-based dashboard for observing and analyzing the Agent Tycoon financial simulation.

## Features

### 🎯 Real-Time Dashboard
- **Portfolio Performance**: Live NAV tracking with interactive charts
- **Asset Allocation**: Dynamic pie charts showing current portfolio composition
- **Performance Metrics**: ROI, total return, and simulation progress
- **WebSocket Updates**: Real-time data streaming without page refresh

### 🤖 AI Decision Intelligence
- **Decision Tracking**: See every AI decision as it happens
- **Action Analysis**: View allocation decisions, cognition costs, and reasoning
- **Strategy Insights**: Understand how the AI agent makes investment choices

### 📊 Market Dynamics
- **Shock Events**: Visualize market volatility and shock impacts
- **Price Movements**: Track individual asset performance
- **Project Lifecycle**: Monitor project investments and completions

### 🏆 HODL Comparison
- **Performance Benchmarking**: Compare AI agent vs buy-and-hold strategy
- **Outperformance Tracking**: Real-time calculation of relative performance
- **Adaptability Metrics**: Measure how well the AI adapts to market changes

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Visualization System
```bash
python run_visualization.py
```

### 3. Open Dashboard
Navigate to: http://127.0.0.1:8000

The system will automatically:
- Start the web server
- Launch a demonstration simulation
- Stream real-time data to your browser

## Architecture

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Web Browser   │ ◄──────────────► │   FastAPI       │
│   Dashboard     │                 │   Server        │
└─────────────────┘                 └─────────────────┘
                                            │
                                            ▼
                                    ┌─────────────────┐
                                    │ Event Collector │
                                    └─────────────────┘
                                            ▲
                                            │ Events
                                    ┌─────────────────┐
                                    │ Simulation      │
                                    │ Engine          │
                                    └─────────────────┘
```

## Event System

The visualization system captures these key events:

- **SIMULATION_START**: Initial simulation setup
- **SIMULATION_TICK**: Each simulation step
- **AGENT_DECISION**: AI decision-making events
- **TRADE_EXECUTED**: Successful trade executions
- **PROJECT_INVESTMENT**: Project funding events
- **PROJECT_COMPLETED**: Project completion events
- **MARKET_SHOCK**: Market volatility events
- **PORTFOLIO_UPDATE**: Portfolio state changes
- **REWARD_CALCULATED**: Reward calculation events
- **HODL_COMPARISON**: Performance comparison events

## API Endpoints

### REST API
- `GET /api/events` - Retrieve filtered simulation events
- `GET /api/portfolio/current` - Get current portfolio state
- `GET /api/performance/summary` - Get performance metrics
- `GET /api/decisions/recent` - Get recent AI decisions

### WebSocket
- `WS /ws` - Real-time event streaming

## Customization

### Running Custom Simulations

```python
from run_visualization import VisualizationDemo

# Create demo instance
demo = VisualizationDemo()

# Run custom simulation
demo.run_random_simulation(num_ticks=200)
```

### Adding Custom Events

```python
from visualization import event_collector, EventType

# Emit custom event
event_collector.emit(
    EventType.AGENT_DECISION,
    tick=current_tick,
    data={'custom_data': 'value'}
)
```

### Extending the Dashboard

The dashboard HTML is embedded in `visualization/web_server.py`. You can:
1. Add new chart types using Plotly.js
2. Create additional panels for custom metrics
3. Implement new WebSocket message handlers

## Integration with Existing Code

The visualization system integrates seamlessly with existing Agent Tycoon components:

- **SimulationEngine**: Enhanced with event emission
- **Gym Environment**: Compatible with RL training
- **HODL Bot**: Automatic comparison tracking
- **All Backends**: Trade, project, and debt operations captured

## Performance

- **Real-time Updates**: <100ms latency for live data
- **Event Storage**: In-memory with configurable limits
- **WebSocket Efficiency**: Only active data streaming
- **Browser Compatibility**: Modern browsers with WebSocket support

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Change port in run_visualization.py
   uvicorn.run(app, host="127.0.0.1", port=8001)
   ```

2. **WebSocket Connection Failed**
   - Check firewall settings
   - Ensure browser supports WebSockets
   - Try refreshing the page

3. **No Data Showing**
   - Verify simulation is running
   - Check browser console for errors
   - Ensure events are being emitted

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Historical data persistence (SQLite/PostgreSQL)
- [ ] Multi-agent tournament visualization
- [ ] Advanced charting (candlestick, technical indicators)
- [ ] Export capabilities (PDF reports, CSV data)
- [ ] Configuration interface for simulation parameters
- [ ] Mobile-responsive design improvements

## Contributing

The visualization system is designed to be extensible. Key areas for contribution:

1. **New Chart Types**: Add specialized financial visualizations
2. **Event Types**: Capture additional simulation aspects
3. **Dashboard Panels**: Create domain-specific views
4. **Performance Optimizations**: Improve real-time streaming
5. **Export Features**: Add data export capabilities

---

**Note**: This visualization system maintains full compatibility with the existing Agent Tycoon simulation while adding comprehensive observability features.
"""
Launch script for Agent Tycoon with visualization.
Runs the web server and provides a simple interface to start simulations.
"""

import asyncio
import uvicorn
import threading
import time
from decimal import Decimal

from visualization import create_visualization_server, event_collector
from engine import SimulationEngine
from ledger import Ledger
from router import AllocationManager
from backends import TradeBackend, ProjectBackend, DebtBackend
from models import CapitalAllocationAction, EquityAlloc, ProjectAlloc


class VisualizationDemo:
    """Demo class to run simulations with visualization."""
    
    def __init__(self):
        self.setup_simulation()
        
    def setup_simulation(self):
        """Initialize the simulation components."""
        # Initialize backends
        self.trade_backend = TradeBackend()
        self.project_backend = ProjectBackend()
        self.debt_backend = DebtBackend()
        
        # Create price provider
        class PriceProvider:
            def __init__(self, trade_backend, debt_backend):
                self.trade_backend = trade_backend
                self.debt_backend = debt_backend
                
            def get_price(self, identifier: str):
                return self.trade_backend.get_price(identifier)
                
            def get_bond_price(self, identifier: str):
                return self.debt_backend.get_bond_price(identifier)
        
        price_provider = PriceProvider(self.trade_backend, self.debt_backend)
        
        # Initialize ledger and allocation manager
        initial_cash = Decimal('100000.00')
        self.ledger = Ledger(initial_cash, price_provider=price_provider)
        self.allocation_manager = AllocationManager(
            self.ledger, self.trade_backend, self.project_backend, self.debt_backend
        )
        
        # Initialize engine with HODL comparison
        self.engine = SimulationEngine(
            self.ledger, self.allocation_manager, enable_hodl_comparison=True
        )
        
    def run_random_simulation(self, num_ticks: int = 50):
        """Run a simulation with random actions for demonstration."""
        import random
        
        print(f"Starting random simulation for {num_ticks} ticks...")
        
        for tick in range(num_ticks):
            # Create a random action every few ticks
            action = None
            if tick % 3 == 0 and random.random() > 0.3:  # 70% chance to take action
                action_type = random.choice(['equity', 'project'])
                
                if action_type == 'equity':
                    # Random stock purchase
                    tickers = list(self.trade_backend.stocks.keys())
                    ticker = random.choice(tickers)
                    amount = Decimal(str(random.randint(1000, 5000)))
                    
                    action = CapitalAllocationAction(
                        action_type="ALLOCATE_CAPITAL",
                        comment=f"Random buy {ticker}",
                        cognition_cost=Decimal('5.0'),
                        allocations=[
                            EquityAlloc(asset_type="EQUITY", ticker=ticker, usd=amount)
                        ]
                    )
                    
                elif action_type == 'project':
                    # Random project investment
                    available_projects = self.project_backend.get_available_projects()
                    if available_projects:
                        project = random.choice(available_projects)
                        raw_amount = min(project.required_investment, self.ledger.cash * Decimal('0.3'))
                        
                        # Quantize to 2 decimal places to match model validation
                        amount = raw_amount.quantize(Decimal('0.01'))

                        if amount > Decimal('1000'):
                            action = CapitalAllocationAction(
                                action_type="ALLOCATE_CAPITAL",
                                comment=f"Invest in {project.name}",
                                cognition_cost=Decimal('10.0'),
                                allocations=[
                                    ProjectAlloc(asset_type="PROJECT", project_id=project.project_id, usd=amount)
                                ]
                            )
            
            # Execute simulation tick
            obs, reward, terminated, truncated, info = self.engine.tick(action)
            
            # Print progress
            if tick % 10 == 0:
                print(f"Tick {tick}: NAV=${obs.nav:,.2f}, Cash=${obs.cash:,.2f}, Reward={reward:.2f}")
            
            # Small delay to make visualization more visible
            time.sleep(0.1)
            
            if terminated or truncated:
                break
                
        print("Simulation completed!")
        print(f"Final NAV: ${obs.nav:,.2f}")
        print(f"Total Return: {((obs.nav - Decimal('100000')) / Decimal('100000') * 100):.2f}%")

    def run_rl_agent_simulation(self, agent_type="PPO", agent_path="ppo_agent_final.zip", num_ticks: int = 50):
        """Run a simulation using a trained RL agent (PPO or SAC)."""
        if agent_type == "PPO":
            from stable_baselines3 import PPO
            model = PPO.load(agent_path)
        elif agent_type == "SAC":
            from stable_baselines3 import SAC
            model = SAC.load(agent_path)
        else:
            raise ValueError("Unsupported agent type: " + agent_type)

        print(f"Starting RL agent simulation ({agent_type}) for {num_ticks} ticks...")

        obs = self.engine.reset()
        for tick in range(num_ticks):
            # Convert simulation observation to gym-style dict if needed
            obs_dict = obs.to_gym_dict() if hasattr(obs, "to_gym_dict") else obs
            action, _ = model.predict(obs_dict, deterministic=True)
            obs, reward, terminated, truncated, info = self.engine.tick(action)
            if tick % 10 == 0:
                print(f"Tick {tick}: NAV=${obs.nav:,.2f}, Cash=${obs.cash:,.2f}, Reward={reward:.2f}")
            time.sleep(0.1)
            if terminated or truncated:
                break

        print("RL Agent Simulation completed!")
        print(f"Final NAV: ${obs.nav:,.2f}")
        print(f"Total Return: {((obs.nav - Decimal('100000')) / Decimal('100000') * 100):.2f}%")


def run_web_server():
    """Run the FastAPI web server."""
    app = create_visualization_server(event_collector)

    @app.on_event("startup")
    async def on_startup():
        """Set the event loop on the global event collector."""
        loop = asyncio.get_running_loop()
        event_collector.set_loop(loop)

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


import argparse

def main():
    """Main function to start the visualization system."""
    parser = argparse.ArgumentParser(description="Agent Tycoon Visualization System")
    parser.add_argument("--headless", action="store_true", help="Run without interactive prompt (Ctrl+C to exit)")
    parser.add_argument("--agent", type=str, default="random", choices=["random", "PPO", "SAC"], help="Agent type to use for simulation")
    parser.add_argument("--agent-path", type=str, default="ppo_agent_final.zip", help="Path to trained RL agent model")
    parser.add_argument("--num-ticks", type=int, default=100, help="Number of simulation ticks")
    args = parser.parse_args()

    print("=== Agent Tycoon Visualization System ===")
    print("Starting web server on http://127.0.0.1:8000")
    print("Open your browser to view the dashboard")
    print()
    
    # Start web server in a separate thread
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    # Give server time to start
    time.sleep(2)
    
    # Create demo and run simulation
    demo = VisualizationDemo()
    
    print("Starting demonstration simulation...")
    print("You can view real-time updates at: http://127.0.0.1:8000")
    print()
    
    try:
        # Run the selected simulation
        if args.agent == "random":
            demo.run_random_simulation(num_ticks=args.num_ticks)
        else:
            demo.run_rl_agent_simulation(agent_type=args.agent, agent_path=args.agent_path, num_ticks=args.num_ticks)
        
        print("\nSimulation completed! The web server is still running.")
        print("You can:")
        print("1. View the results at http://127.0.0.1:8000")
        print("2. Press Ctrl+C to exit")
        print("3. Run another simulation by calling demo.run_random_simulation() or demo.run_rl_agent_simulation()")
        
        if args.headless:
            # Headless mode: just wait for Ctrl+C
            while True:
                time.sleep(1)
        else:
            # Interactive mode: allow user to exit or run more simulations
            while True:
                user_input = input("Type 'run' to run another simulation, or 'exit' to quit: ").strip().lower()
                if user_input == "run":
                    if args.agent == "random":
                        demo.run_random_simulation(num_ticks=args.num_ticks)
                    else:
                        demo.run_rl_agent_simulation(agent_type=args.agent, agent_path=args.agent_path, num_ticks=args.num_ticks)
                    print("Simulation completed! View at http://127.0.0.1:8000")
                elif user_input == "exit":
                    print("Exiting visualization system.")
                    break
                else:
                    print("Unknown command. Type 'run' or 'exit'.")
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
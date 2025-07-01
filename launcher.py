import subprocess
import sys
import time
import webbrowser
import os

def main():
    # Start the visualization system
    print("Starting Agent Tycoon Visualization System...")
    proc = subprocess.Popen([sys.executable, "run_visualization.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for the server to start
    time.sleep(3)

    url = "http://127.0.0.1:8000"
    print(f"Opening browser to {url}")
    webbrowser.open(url)

    try:
        # Wait for the visualization process to finish
        proc.wait()
    except KeyboardInterrupt:
        print("Shutting down launcher and visualization system...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    main()
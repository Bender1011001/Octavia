import csv
import os
from datetime import datetime

LEADERBOARD_FILE = "agent_leaderboard.csv"

def log_result(agent_name, mean_reward, std_reward, notes=""):
    file_exists = os.path.isfile(LEADERBOARD_FILE)
    with open(LEADERBOARD_FILE, mode="a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "agent_name", "mean_reward", "std_reward", "notes"])
        writer.writerow([
            datetime.now().isoformat(),
            agent_name,
            f"{mean_reward:.2f}",
            f"{std_reward:.2f}",
            notes
        ])

def print_leaderboard():
    if not os.path.isfile(LEADERBOARD_FILE):
        print("No leaderboard data found.")
        return
    with open(LEADERBOARD_FILE, mode="r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            print(", ".join(row))

if __name__ == "__main__":
    print("Current Agent Leaderboard:")
    print_leaderboard()
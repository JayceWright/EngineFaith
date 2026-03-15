import httpx
import sys
import json

BASE_URL = "http://127.0.0.1:8000"

def add_agent(name, prompt, faith=0.0, stress=0.0):
    data = {
        "name": name,
        "prompt": prompt,
        "faith_level": faith,
        "stress_level": stress
    }
    try:
        response = httpx.post(f"{BASE_URL}/agents", json=data)
        response.raise_for_status()
        print(f"Success: {response.json()['message']}")
    except Exception as e:
        print(f"Error: {e}")

def list_world():
    try:
        response = httpx.get(f"{BASE_URL}/world")
        response.raise_for_status()
        data = response.json()
        print("\n--- AGENTS ---")
        for agent in data['agents']:
            print(f"ID {agent['id']}: {agent['name']} (Faith: {agent['faith_level']}, Stress: {agent['stress_level']})")
        print("\n--- RECENT SCRIPTURES ---")
        for s in data['recent_scriptures']:
            name = s['agent_name'] if s['agent_name'] else "World"
            print(f"[{s['timestamp']}] {name}: {s['message']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_agents.py list")
        print("  python manage_agents.py add <name> <prompt> [faith] [stress]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        list_world()
    elif cmd == "add":
        if len(sys.argv) < 4:
            print("Usage: python manage_agents.py add <name> <prompt> [faith] [stress]")
        else:
            name = sys.argv[2]
            prompt = sys.argv[3]
            faith = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
            stress = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
            add_agent(name, prompt, faith, stress)
    else:
        print("Unknown command")

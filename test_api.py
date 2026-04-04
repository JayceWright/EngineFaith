import httpx

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("Testing /agents endpoint...")
    agent_data = {
        "name": "Test Agent",
        "prompt": "You are a test agent. Always mention 'test' in your messages.",
        "faith_level": 1.0,
        "stress_level": 0.0
    }

    # Create agent
    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/agents", json=agent_data)
        print(f"Response from /agents: {response.text}")
        assert response.status_code == 200
        assert "Agent Test Agent created." in response.json()["message"]

        print("Testing /world endpoint...")
        response = client.get(f"{BASE_URL}/world")
        print(f"Response from /world: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert len(data['agents']) > 0
        assert any(a['name'] == 'Test Agent' for a in data['agents'])

    print("API tests passed!")

if __name__ == "__main__":
    test_api()

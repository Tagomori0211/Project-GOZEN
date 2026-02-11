import requests
import time
import json
import sys

BASE_URL = "http://localhost:9000/api/v1"

def test_health():
    print("Testing /health...")
    try:
        r = requests.get(f"{BASE_URL}/health")
        r.raise_for_status()
        print(f"OK: {r.json()}")
    except Exception as e:
        print(f"FAIL: {e}")
        # sys.exit(1) # Continue to try flow even if health fails? No, fail.
        sys.exit(1)

def test_full_flow():
    print("\nTesting Full Council Flow...")
    
    # 1. Start Session
    mission = "Test Mission: Verify Full API Flow"
    print(f"[1] Starting session with mission: {mission}")
    r = requests.post(f"{BASE_URL}/council/start", json={
        "mission": mission,
        "plan": "pro",
        "security_level": "mock" 
    })
    r.raise_for_status()
    data = r.json()
    session_id = data["session_id"]
    print(f" -> Session Started: {session_id}")
    
    # 2. Wait for Proposals (awaiting_arbitration)
    print("[2] Waiting for proposals...")
    for _ in range(30): # Wait up to 30s
        time.sleep(1)
        r = requests.get(f"{BASE_URL}/council/{session_id}/status")
        r.raise_for_status()
        state = r.json()
        status = state['status']
        print(f"    Status: {status}")
        
        if status == "awaiting_arbitration":
            print(" -> Proposals Ready!")
            print(f"    Kaigun: {state.get('kaigun_proposal', {}).get('header', 'N/A')}")
            print(f"    Rikugun: {state.get('rikugun_proposal', {}).get('header', 'N/A')}")
            break
        elif status == "error":
            print(f" -> Error: {state.get('error')}")
            sys.exit(1)
    else:
        print(" -> Timeout waiting for proposals")
        sys.exit(1)

    # 3. Arbitrate (Adopt Kaigun)
    print(f"[3] Arbitrating (Adopt Kaigun)...")
    r = requests.post(f"{BASE_URL}/council/{session_id}/arbitrate", json={
        "decision": "kaigun",
        "reason": "By test script fiat."
    })
    r.raise_for_status()
    print(f" -> Arbitrated: {r.json()}")

    # 4. Wait for Completion
    print("[4] Waiting for completion (notification & document)...")
    for _ in range(30):
        time.sleep(1)
        r = requests.get(f"{BASE_URL}/council/{session_id}/status")
        r.raise_for_status()
        state = r.json()
        status = state['status']
        print(f"    Status: {status}")
        
        if status == "completed":
            print(" -> Flow Completed!")
            doc = state.get("official_document", {})
            print(f"    Official Document: {doc}")
            break
        elif status == "error":
             print(f" -> Error: {state.get('error')}")
             sys.exit(1)
    else:
        print(" -> Timeout waiting for completion")
        sys.exit(1)

    print("\nSUCCESS: Full flow verified.")

if __name__ == "__main__":
    test_health()
    test_full_flow()

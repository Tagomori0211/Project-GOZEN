import asyncio
import httpx
import json
import sys
import time
import websockets

BASE_URL = "http://127.0.0.1:9000/api"
WS_URL = "ws://127.0.0.1:9000/ws/council"

async def test_health():
    print("Testing Health Check...")
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{BASE_URL}/v1/health")
            r.raise_for_status()
            print(f"[PASS] Health OK: {r.json()}")
        except Exception as e:
            print(f"[FAIL] Health Failed: {e}")
            sys.exit(1)

async def test_full_flow(scenario="integrate_adopt"):
    print(f"\nStarting Full Scenario Test: {scenario}")
    
    async with httpx.AsyncClient() as client:
        # 1. Create Session
        print("[1] Creating session...")
        try:
            r = await client.post(f"{BASE_URL}/sessions", json={
                "security_level": "mock"
            })
            r.raise_for_status()
            session_id = r.json()["session_id"]
            print(f" -> Session Created: {session_id}")
        except Exception as e:
            print(f"[FAIL] Session creation failed: {e}")
            sys.exit(1)

        # 2. Start WebSocket and Trigger FLOW
        print(f"[2] Connecting to WS: {WS_URL}/{session_id}")
        try:
            async with websockets.connect(f"{WS_URL}/{session_id}") as ws:
                # Trigger START
                await ws.send(json.dumps({
                    "type": "START",
                    "mission": f"Verification: {scenario}"
                }))
                print(" -> START signal sent via WS")

                # Listen for events
                phases_seen = []
                rounds_seen = 0
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        event = json.loads(msg)
                        etype = event.get("type")
                        print(f"    Event: {etype}")

                        if etype == "PHASE":
                            phase = event.get("phase")
                            phases_seen.append(phase)
                            print(f"    -> Phase: {phase}")
                            if phase == "proposal":
                                rounds_seen += 1
                                print(f"    -> Round: {rounds_seen}")

                        if etype == "AWAITING_DECISION":
                            choice = 3 # Default: Integrate
                            if scenario == "adopt_kaigun": choice = 1
                            elif scenario == "adopt_rikugun": choice = 2
                            elif scenario == "reject_all": choice = 4
                            
                            print(f"    -> Decision required. Sending Choice ({choice})")
                            await client.post(f"{BASE_URL}/sessions/{session_id}/decision", json={"choice": choice})
                        
                        if etype == "AWAITING_MERGE_DECISION":
                            choice = 1 # Default: Adopt
                            if scenario == "integrate_reject" and rounds_seen == 1:
                                choice = 2 # Reject in Round 1
                            
                            print(f"    -> Merge Decision required. Sending Choice ({choice})")
                            await client.post(f"{BASE_URL}/sessions/{session_id}/decision", json={"choice": choice})

                        if etype == "COMPLETE" or (etype == "PHASE" and event.get("phase") == "complete"):
                            print("\n[3] Flow completion detected!")
                            if scenario == "integrate_reject" and rounds_seen < 2:
                                print("[FAIL] Expected at least 2 rounds for integrate_reject scenario")
                                sys.exit(1)
                            break
                        
                        if etype == "ERROR":
                            print(f"[FAIL] Workflow Error: {event.get('message')}")
                            sys.exit(1)

                    except asyncio.TimeoutError:
                        print("[FAIL] Timeout waiting for WS events")
                        sys.exit(1)

        except Exception as e:
            print(f"[FAIL] WebSocket/Workflow failed: {e}")
            sys.exit(1)

    print(f"\n[PASS] Scenario {scenario} verified Successfully.")

if __name__ == "__main__":
    scenario = "integrate_adopt"
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    
    asyncio.run(test_health())
    asyncio.run(test_full_flow(scenario))

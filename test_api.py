import requests
import json
import sys

BASE_URL = "http://localhost:5000"
if len(sys.argv) > 1:
    BASE_URL = sys.argv[1]

# Remove trailing slash
if BASE_URL.endswith("/"):
    BASE_URL = BASE_URL[:-1]

def run_tests():
    print(f"=== Testing API against {BASE_URL} ===\n")
    
    # Test GET /
    print("Test: GET / (Root Endpoint)")
    try:
        res = requests.get(f"{BASE_URL}/")
        if res.status_code == 200 and "Multi Agent Writer API is running!" in res.text:
            print("  PASS - Root endpoint returned success")
        else:
            print(f"  FAIL - Expected status 200 and specific text, got {res.status_code}: {res.text}")
    except Exception as e:
        print(f"  FAIL - Request error: {e}")
        
    print("\n--------------------------")
    
    # Test GET /api/health
    print("Test: GET /api/health (Health Check)")
    try:
        res = requests.get(f"{BASE_URL}/api/health")
        if res.status_code == 200 and res.json().get("status") == "ok":
            print(f"  PASS - Health check OK. Response: {res.json()}")
        else:
            print(f"  FAIL - Health check failed. Status: {res.status_code}, Response: {res.text}")
    except Exception as e:
        print(f"  FAIL - Request error: {e}")
        
    print("\n--------------------------")
    
    # Test POST /api/run
    print('Test: POST /api/run with topic "Future of AI"')
    try:
        url = f"{BASE_URL}/api/run"
        payload = {"topic": "Future of AI"}
        
        print(f"  Connecting to SSE stream at {url}...")
        
        # We need stream=True to process Server-Sent Events
        session = requests.Session()
        with session.post(url, json=payload, stream=True, headers={'Cache-Control': 'no-cache'}) as response:
            if response.status_code != 200:
                print(f"  FAIL - SSE connection failed with status code {response.status_code}: {response.text}")
                return
                
            print("  PASS - Connected to SSE stream. Waiting for events...")
            print("  --- Stream Output ---")
            
            event_count = 0
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        event_data = json.loads(decoded_line[6:])
                        event_count += 1
                        print(f"  -> [{event_data.get('type')}] {event_data.get('message')}")
                        
                        if event_data.get('type') in ['complete', 'error']:
                            break
                            
            if event_count > 0:
                print(f"  --- End of stream ({event_count} events received) ---")
                print("  PASS - SSE streaming works as expected")
            else:
                print("  FAIL - Did not receive any SSE events")
                
    except Exception as e:
        print(f"  FAIL - Request error: {e}")

if __name__ == "__main__":
    run_tests()

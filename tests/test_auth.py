import requests
import time
import sys

BASE_URL = "http://127.0.0.1:5000"

def wait_for_server():
    for _ in range(10):
        try:
            requests.get(BASE_URL + "/apidocs/")
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    return False

def test_auth():
    if not wait_for_server():
        print("Server failed to start")
        sys.exit(1)

    # Register
    reg_payload = {"username": "testuser", "password": "password123"}
    resp = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    print(f"Register status: {resp.status_code}")
    print(f"Register response: {resp.text}")
    
    if resp.status_code != 201:
        # It might be 400 if user exists from previous run (if db persisted)
        if resp.status_code == 400 and "User already exists" in resp.text:
            pass
        else:
            sys.exit(1)

    # Login
    login_payload = {"username": "testuser", "password": "password123"}
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    print(f"Login status: {resp.status_code}")
    if resp.status_code == 200 and 'token' in resp.json():
        print("Login successful, token received")
    else:
        print(f"Login failed: {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    test_auth()

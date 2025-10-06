#!/usr/bin/env python3
"""
Test script for 3D-Speaker Inference Server API
"""

import requests
import time
import os

def test_server(base_url="http://localhost:8000"):
    """Test the speaker verification server"""

    print(f"Testing server at: {base_url}")

    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
        return False

    # Test 2: Home endpoint
    print("\n2. Testing home endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: List models
    print("\n3. Testing models endpoint...")
    try:
        response = requests.get(f"{base_url}/models")
        print(f"   Status: {response.status_code}")
        print(f"   Available models: {len(response.json()['available_models'])}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n✅ Server test completed!")
    return True

if __name__ == "__main__":
    test_server()
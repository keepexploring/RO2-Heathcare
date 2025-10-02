#!/usr/bin/env python3
"""
Authentication Security Test Suite
Tests the FastAPI authentication implementation
"""

import requests
import json
import sys
from typing import Dict, Optional


class AuthTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None

    def test_login(self, username: str, password: str) -> bool:
        """Test login functionality"""
        print(f"\n🔐 Testing Login: {username}")
        try:
            response = requests.post(
                f"{self.base_url}/login",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                print(f"   ✅ Login successful - Token: {self.token[:20]}...")
                return True
            else:
                print(f"   ❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Login error: {e}")
            return False

    def test_protected_endpoints_without_auth(self) -> Dict[str, bool]:
        """Test protected endpoints without authentication"""
        print(f"\n🚫 Testing Protected Endpoints WITHOUT Authentication:")
        print("-" * 60)

        endpoints = [
            "/data",
            "/stats",
            "/latest",
            "/timeline",
            "/concentrators",
            "/analytics",
            "/raw-accelerometer",
            "/vibration/frequency"
        ]

        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                if response.status_code in [401, 403]:  # Both are valid for "not authenticated"
                    print(f"   ✅ {endpoint:<20} - Protected ({response.status_code})")
                    results[endpoint] = True
                else:
                    print(f"   ❌ {endpoint:<20} - NOT Protected ({response.status_code})")
                    results[endpoint] = False
            except Exception as e:
                print(f"   ⚠️  {endpoint:<20} - Error: {e}")
                results[endpoint] = False

        return results

    def test_protected_endpoints_with_auth(self) -> Dict[str, bool]:
        """Test protected endpoints with valid authentication"""
        if not self.token:
            print("❌ No token available for testing")
            return {}

        print(f"\n✅ Testing Protected Endpoints WITH Authentication:")
        print("-" * 60)

        endpoints = [
            "/data?limit=1",
            "/stats",
            "/latest",
            "/timeline?hours=1",
            "/concentrators",
            "/analytics?limit=1",
            "/raw-accelerometer?limit=1",
            "/vibration/frequency?hours=1"
        ]

        headers = {"Authorization": f"Bearer {self.token}"}
        results = {}

        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
                if response.status_code == 200:
                    print(f"   ✅ {endpoint:<25} - Access granted (200)")
                    results[endpoint] = True
                elif response.status_code == 401:
                    print(f"   ❌ {endpoint:<25} - Auth failed (401)")
                    results[endpoint] = False
                else:
                    print(f"   ⚠️  {endpoint:<25} - Unexpected ({response.status_code})")
                    results[endpoint] = False
            except Exception as e:
                print(f"   ❌ {endpoint:<25} - Error: {e}")
                results[endpoint] = False

        return results

    def test_public_endpoints(self) -> Dict[str, bool]:
        """Test public endpoints (should work without auth)"""
        print(f"\n🌐 Testing Public Endpoints (No Auth Required):")
        print("-" * 60)

        endpoints = ["/ping", "/health"]
        results = {}

        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    print(f"   ✅ {endpoint:<20} - Public access (200)")
                    results[endpoint] = True
                else:
                    print(f"   ❌ {endpoint:<20} - Failed ({response.status_code})")
                    results[endpoint] = False
            except Exception as e:
                print(f"   ❌ {endpoint:<20} - Error: {e}")
                results[endpoint] = False

        return results

    def test_invalid_credentials(self):
        """Test login with invalid credentials"""
        print(f"\n🚫 Testing Invalid Credentials:")
        print("-" * 40)

        test_cases = [
            ("admin", "wrongpassword"),
            ("wronguser", "admin123"),
            ("", ""),
            ("admin", "")
        ]

        for username, password in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/login",
                    json={"username": username, "password": password}
                )

                if response.status_code == 401:
                    print(f"   ✅ Invalid login rejected: '{username}'/'{password}'")
                else:
                    print(f"   ❌ Invalid login accepted: '{username}'/'{password}' ({response.status_code})")
            except Exception as e:
                print(f"   ❌ Error testing '{username}'/'{password}': {e}")

    def run_full_test_suite(self):
        """Run complete authentication test suite"""
        print("🔒 FastAPI Authentication Security Test Suite")
        print("=" * 60)

        # Test 1: Public endpoints
        public_results = self.test_public_endpoints()

        # Test 2: Invalid credentials
        self.test_invalid_credentials()

        # Test 3: Valid login
        login_success = self.test_login("admin", "admin123")

        if not login_success:
            print("\n❌ Cannot continue tests - login failed")
            return False

        # Test 4: Protected endpoints without auth
        unauth_results = self.test_protected_endpoints_without_auth()

        # Test 5: Protected endpoints with auth
        auth_results = self.test_protected_endpoints_with_auth()

        # Summary
        print(f"\n📊 Test Summary:")
        print("=" * 30)

        total_protected = len(unauth_results)
        protected_count = sum(unauth_results.values())
        accessible_count = sum(auth_results.values())

        print(f"Public endpoints working: {sum(public_results.values())}/{len(public_results)}")
        print(f"Endpoints properly protected: {protected_count}/{total_protected}")
        print(f"Endpoints accessible with auth: {accessible_count}/{len(auth_results)}")

        if protected_count == total_protected and accessible_count == len(auth_results):
            print("\n🎉 All security tests PASSED!")
            return True
        else:
            print(f"\n⚠️  Security issues detected!")
            return False


if __name__ == "__main__":
    # Check if server is running
    tester = AuthTester()
    try:
        response = requests.get(f"{tester.base_url}/health", timeout=5)
        print(f"Server is running at {tester.base_url}")
    except:
        print(f"❌ Server not running at {tester.base_url}")
        print("Please start the server with: docker-compose up")
        sys.exit(1)

    # Run tests
    success = tester.run_full_test_suite()
    sys.exit(0 if success else 1)
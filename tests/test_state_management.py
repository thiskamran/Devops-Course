# tests/test_state_management.py
import unittest
import requests

class TestStateManagement(unittest.TestCase):
    BASE_URL = "http://localhost:8197"
    auth = ("user", "test@123")

    def test_state_management_feature(self):
        """Test the basic state management feature - GET/PUT /state"""
        # Test changing state to RUNNING
        response = requests.put(
            f"{self.BASE_URL}/state",
            data="RUNNING",
            headers={'Content-Type': 'text/plain'},
            auth=self.auth
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify state changed
        response = requests.get(f"{self.BASE_URL}/state", auth=self.auth)
        self.assertEqual(response.text, "RUNNING")

if __name__ == '__main__':
    unittest.main()
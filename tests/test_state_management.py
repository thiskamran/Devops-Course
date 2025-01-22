# tests/test_state_management.py
import unittest
import requests
import time
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestStateManagement(unittest.TestCase):
    BASE_URL = "http://localhost:8197/"
    auth = ("user", "test@123")

    
    def test_state_management_feature(self):
        """Test the basic state management feature - GET/PUT /state"""
        try:
            # Test initial state
            logger.info("Getting initial state...")
            response = requests.get(f"{self.BASE_URL}/state", auth=self.auth)  
            logger.info(f"Initial state: {response.text}")
            self.assertEqual(response.status_code, 200)
            
            # Test changing state to RUNNING
            logger.info("Attempting to change state to RUNNING...")
            response = requests.put(
                f"{self.BASE_URL}/state",
                data="RUNNING",
                headers={'Content-Type': 'text/plain'},
                auth=self.auth
            )
            logger.info(f"PUT response status: {response.status_code}")
            logger.info(f"PUT response content: {response.text}")
            self.assertEqual(response.status_code, 200)
            
            time.sleep(5)  # Allow state to propagate
            
            # Verify state changed
            response = requests.get(f"{self.BASE_URL}/state", auth=self.auth)
            logger.info(f"Final state: {response.text}")
            print(f"Final state: {response.text}")
            self.assertEqual(response.text.strip(), "RUNNING")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise

if __name__ == '__main__':
    unittest.main()
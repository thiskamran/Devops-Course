# tests/test_state_management.py
import unittest
import requests
import time
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestStateManagement(unittest.TestCase):
    BASE_URL = "http://nginx:8197/"
    auth = ("user", "test@123")

    def put_state(self, state):
        return requests.put(
            f"{self.BASE_URL}/state",
            data=state,
            headers={'Content-Type': 'text/plain'},
            auth=self.auth
        )

    def get_state(self):
        return requests.get(f"{self.BASE_URL}/state", auth=self.auth)

    def make_request(self):
        return requests.get(f"{self.BASE_URL}/request", auth=self.auth)
    
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

   
    def test_request_handling_in_paused_state(self):
        """Test that requests are blocked in PAUSED state"""
        # Set RUNNING first
        self.put_state("RUNNING")
        response = self.make_request()
        self.assertEqual(response.status_code, 200)
        
        # Change to PAUSED
        self.put_state("PAUSED")
        response = self.make_request()
        self.assertEqual(response.status_code, 503)

    
        """Test behavior when state changes while processing requests"""
        self.put_state("RUNNING")
        time.sleep(1)
        
        # Start a long-running request
        def long_request():
            return requests.get(f"{self.BASE_URL}/request?delay=5", auth=self.auth)
            
        import threading
        request_thread = threading.Thread(target=long_request)
        request_thread.start()
        
        # Change state while request is processing
        time.sleep(1)
        self.put_state("PAUSED")
        
        request_thread.join()
        
        # Verify system is in PAUSED state
        response = self.get_state()
        self.assertEqual(response.text.strip(), "PAUSED")
if __name__ == '__main__':
    unittest.main()